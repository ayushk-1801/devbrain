"""FastAPI router for auth and instance management endpoints."""
from __future__ import annotations

import logging
import secrets
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.platform import auth as auth_mod
from backend.platform import provisioner
from backend.platform.crypto import decrypt_secrets, encrypt_secrets
from backend.platform.db import get_session
from backend.platform.models import Instance, User

logger = logging.getLogger("devbrain.platform")

router = APIRouter()

# ---------------------------------------------------------------------------
# Auth dependency helpers
# ---------------------------------------------------------------------------


def require_user(session: Session, token: str) -> User:
    """Verify token and return the User, or raise 401."""
    payload = auth_mod.verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = int(payload["sub"])
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@router.get("/auth/github/login")
async def github_login(response: Response) -> RedirectResponse:
    """Redirect the browser to GitHub OAuth authorization page."""
    state = secrets.token_urlsafe(32)
    # State is short-lived; we embed it in the redirect URL the frontend
    # will pass back. For production, store in a signed cookie.
    url = auth_mod.github_authorization_url(state)
    redirect = RedirectResponse(url=url)
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
    )
    return redirect


@router.get("/auth/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    oauth_state: Optional[str] = Cookie(default=None),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Handle the GitHub OAuth callback, issue a JWT, redirect to frontend."""
    frontend_url = auth_mod.FRONTEND_URL

    if oauth_state and state != oauth_state:
        return RedirectResponse(f"{frontend_url}/login?error=state_mismatch")

    access_token = await auth_mod.exchange_code_for_token(code)
    if not access_token:
        return RedirectResponse(f"{frontend_url}/login?error=token_exchange_failed")

    github_user = await auth_mod.fetch_github_user(access_token)
    if not github_user:
        return RedirectResponse(f"{frontend_url}/login?error=user_fetch_failed")

    # Upsert user
    stmt = select(User).where(User.github_id == github_user["id"])
    user = session.exec(stmt).first()
    if user:
        user.github_login = github_user.get("login", user.github_login)
        user.github_name  = github_user.get("name")
        user.avatar_url   = github_user.get("avatar_url", user.avatar_url)
        user.email        = github_user.get("email")
    else:
        user = User(
            github_id    = github_user["id"],
            github_login = github_user.get("login", ""),
            github_name  = github_user.get("name"),
            avatar_url   = github_user.get("avatar_url", ""),
            email        = github_user.get("email"),
        )
        session.add(user)
    session.commit()
    session.refresh(user)

    jwt_token = auth_mod.create_access_token(
        user.id, user.github_login, user.avatar_url
    )

    redirect = RedirectResponse(f"{frontend_url}/dashboard?token={jwt_token}")
    redirect.delete_cookie("oauth_state")
    return redirect


@router.get("/auth/me")
async def get_me(
    authorization: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """Return the current user's profile. Pass ?authorization=Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    user = require_user(session, token)
    return {
        "id": user.id,
        "github_login": user.github_login,
        "github_name": user.github_name,
        "avatar_url": user.avatar_url,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Instance routes
# ---------------------------------------------------------------------------


class CreateInstanceRequest(BaseModel):
    repo: str
    github_token: str
    cognee_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    webhook_secret: Optional[str] = None


@router.post("/instances")
async def create_instance(
    req: CreateInstanceRequest,
    authorization: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """Provision a new DevBrain backend instance for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    user = require_user(session, token)

    # Validate that at least one LLM key is provided
    if not req.cognee_api_key and not req.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Either cognee_api_key or gemini_api_key is required",
        )

    # Validate repo format
    if "/" not in req.repo:
        raise HTTPException(status_code=400, detail="repo must be in 'owner/repo' format")

    # Validate GitHub token by fetching the repo briefly
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/repos/{req.repo}",
                headers={
                    "Authorization": f"Bearer {req.github_token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=10,
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=400, detail="Invalid GitHub token")
        if resp.status_code == 404:
            raise HTTPException(
                status_code=400,
                detail=f"Repository '{req.repo}' not found or not accessible",
            )
    except httpx.TimeoutException:
        pass  # Don't block creation on network timeout

    # Allocate port
    used_ports_result = session.exec(select(Instance.port)).all()
    used_ports = list(used_ports_result)
    try:
        port = provisioner.allocate_port(used_ports)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Encrypt secrets
    secrets_dict = {
        "github_token":   req.github_token,
        "cognee_api_key": req.cognee_api_key or "",
        "gemini_api_key": req.gemini_api_key or "",
        "webhook_secret": req.webhook_secret or secrets.token_hex(16),
    }
    secrets_enc = encrypt_secrets(secrets_dict)

    # Create instance record
    instance = Instance(
        user_id=user.id,
        repo=req.repo,
        port=port,
        status="pending",
        secrets_enc=secrets_enc,
    )
    session.add(instance)
    session.commit()
    session.refresh(instance)

    # Provision containers
    try:
        result = await provisioner.provision_instance(
            instance.id, req.repo, port, secrets_dict
        )
        instance.status                = result["status"]
        instance.container_api_name    = result["container_api_name"]
        instance.container_worker_name = result["container_worker_name"]
        instance.container_redis_name  = result["container_redis_name"]
    except Exception as exc:
        logger.exception("Failed to provision instance %s", instance.id)
        instance.status = "error"
    finally:
        session.add(instance)
        session.commit()
        session.refresh(instance)

    mcp_command = (
        f'claude mcp add devbrain -s project '
        f'-e DEVBRAIN_API_URL="{instance.api_url}" '
        f'-- python -m backend.mcp_server'
    )

    return {
        "id": instance.id,
        "repo": instance.repo,
        "api_url": instance.api_url,
        "status": instance.status,
        "created_at": instance.created_at.isoformat(),
        "mcp_command": mcp_command,
    }


@router.get("/instances")
async def list_instances(
    authorization: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """List all instances for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    user = require_user(session, token)

    stmt = select(Instance).where(Instance.user_id == user.id)
    instances = session.exec(stmt).all()

    return {
        "instances": [
            {
                "id": inst.id,
                "repo": inst.repo,
                "api_url": inst.api_url,
                "status": inst.status,
                "created_at": inst.created_at.isoformat(),
                "mcp_command": (
                    f'claude mcp add devbrain -s project '
                    f'-e DEVBRAIN_API_URL="{inst.api_url}" '
                    f'-- python -m backend.mcp_server'
                ),
            }
            for inst in instances
        ]
    }


@router.get("/instances/{instance_id}")
async def get_instance(
    instance_id: str,
    authorization: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """Get a single instance by ID (owner only)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    user = require_user(session, token)

    instance = session.get(Instance, instance_id)
    if not instance or instance.user_id != user.id:
        raise HTTPException(status_code=404, detail="Instance not found")

    # Refresh live status from Docker
    live_status = provisioner.get_instance_status(instance_id)
    if live_status != instance.status and live_status in ("running", "stopped"):
        instance.status = live_status
        session.add(instance)
        session.commit()

    return {
        "id": instance.id,
        "repo": instance.repo,
        "api_url": instance.api_url,
        "status": instance.status,
        "created_at": instance.created_at.isoformat(),
        "container_api_name": instance.container_api_name,
    }


@router.delete("/instances/{instance_id}")
async def delete_instance(
    instance_id: str,
    authorization: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """Stop + remove all containers and delete the instance record."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    user = require_user(session, token)

    instance = session.get(Instance, instance_id)
    if not instance or instance.user_id != user.id:
        raise HTTPException(status_code=404, detail="Instance not found")

    try:
        await provisioner.stop_instance(instance_id)
    except Exception as exc:
        logger.warning("Error stopping containers for %s: %s", instance_id, exc)

    session.delete(instance)
    session.commit()
    return {"status": "deleted", "id": instance_id}


@router.get("/instances/{instance_id}/health")
async def instance_health(
    instance_id: str,
    authorization: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> dict:
    """Proxy a health check to the tenant's API container."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ")
    user = require_user(session, token)

    instance = session.get(Instance, instance_id)
    if not instance or instance.user_id != user.id:
        raise HTTPException(status_code=404, detail="Instance not found")

    urls = [
        f"http://devbrain-{instance_id}-api:8000/health",
        f"{instance.api_url}/health"
    ]
    last_exc = None
    for url in urls:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=3)
            if resp.status_code == 200:
                return {"id": instance_id, "healthy": True, "detail": resp.json()}
        except Exception as exc:
            last_exc = exc
    return {"id": instance_id, "healthy": False, "detail": str(last_exc)}
