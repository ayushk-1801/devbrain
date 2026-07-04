"""GitHub OAuth flow and JWT token helpers for the DevBrain platform."""
from __future__ import annotations
import os
import secrets
import time
from typing import Optional
import httpx
from jose import JWTError, jwt

GITHUB_OAUTH_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
GITHUB_OAUTH_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")
GITHUB_OAUTH_REDIRECT_URI = os.getenv(
    "GITHUB_OAUTH_REDIRECT_URI", "http://localhost:9000/auth/callback"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 60 * 60 * 24  # 24 hours


def _jwt_secret() -> str:
    secret = os.getenv("PLATFORM_SECRET_KEY", "")
    if not secret:
        raise RuntimeError("PLATFORM_SECRET_KEY env var is required")
    return secret


def create_access_token(user_id: int, github_login: str, avatar_url: str) -> str:
    """Issue a signed JWT for the given user."""
    payload = {
        "sub": str(user_id),
        "login": github_login,
        "avatar": avatar_url,
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """Verify a JWT and return its payload, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def github_authorization_url(state: str) -> str:
    """Build the GitHub OAuth authorization URL."""
    return (
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_OAUTH_CLIENT_ID}"
        "&scope=read:user,user:email"
        f"&redirect_uri={GITHUB_OAUTH_REDIRECT_URI}"
        f"&state={state}"
    )


async def exchange_code_for_token(code: str) -> Optional[str]:
    """Exchange a GitHub OAuth code for an access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_OAUTH_CLIENT_ID,
                "client_secret": GITHUB_OAUTH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_OAUTH_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("access_token")


async def fetch_github_user(access_token: str) -> Optional[dict]:
    """Fetch the authenticated user's GitHub profile."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
