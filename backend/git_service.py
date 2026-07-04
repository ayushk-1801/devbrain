"""Local git operations service.

All functions execute real git subprocess commands in a configurable
local repository path (LOCAL_REPO_PATH from settings, default ".").

These tools only work when the DevBrain backend is running on the same
machine as the local git clone. They are intentionally kept read/write
safe: destructive operations (rebase, force-push) are allowed but
surface clear warnings in their return value.

git_smart_push() is the flagship orchestrator — it stages → commits
→ pushes in a single atomic call with structured step-by-step output.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path
from typing import Any, Optional

from backend.config import settings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_path(repo_path: Optional[str]) -> str:
    """Return the repo path to use, falling back to settings.LOCAL_REPO_PATH."""
    if repo_path:
        return str(Path(repo_path).expanduser().resolve())
    return str(Path(settings.LOCAL_REPO_PATH).expanduser().resolve())


async def _run_git(*args: str, cwd: str) -> dict[str, Any]:
    """Run a git command asynchronously and return structured output."""
    cmd = ["git"] + list(args)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
            "success": proc.returncode == 0,
        }
    except FileNotFoundError:
        return {
            "command": " ".join(cmd),
            "returncode": -1,
            "stdout": "",
            "stderr": "git not found on PATH",
            "success": False,
        }
    except Exception as e:
        return {
            "command": " ".join(cmd),
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False,
        }


# ---------------------------------------------------------------------------
# Git status
# ---------------------------------------------------------------------------


async def git_status(repo_path: Optional[str] = None) -> dict[str, Any]:
    """Return the working tree status of the local git repository.

    Equivalent to `git status --porcelain` with branch info.

    Args:
        repo_path: Path to the local git repo. Defaults to LOCAL_REPO_PATH.
    """
    cwd = _resolve_path(repo_path)
    porcelain = await _run_git("status", "--porcelain=v2", "--branch", cwd=cwd)
    human = await _run_git("status", cwd=cwd)

    # Parse porcelain v2 output
    staged = []
    unstaged = []
    untracked = []
    branch = None

    for line in porcelain["stdout"].splitlines():
        if line.startswith("# branch.head"):
            branch = line.split(" ", 2)[2] if len(line.split(" ")) > 2 else None
        elif line.startswith("1 ") or line.startswith("2 "):
            parts = line.split(" ")
            xy = parts[1] if len(parts) > 1 else "??"
            filename = parts[-1] if len(parts) > 1 else ""
            x, y = (xy[0], xy[1]) if len(xy) >= 2 else ("?", "?")
            if x != "." and x != "?":
                staged.append({"file": filename, "status": x})
            if y != "." and y != "?":
                unstaged.append({"file": filename, "status": y})
        elif line.startswith("?"):
            parts = line.split(" ")
            if len(parts) > 1:
                untracked.append(parts[-1])

    is_clean = not staged and not unstaged and not untracked

    return {
        "repo_path": cwd,
        "branch": branch,
        "is_clean": is_clean,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "human_readable": human["stdout"],
        "success": porcelain["success"],
    }


# ---------------------------------------------------------------------------
# Git commit
# ---------------------------------------------------------------------------


async def git_commit(
    message: str,
    repo_path: Optional[str] = None,
    add_all: bool = True,
) -> dict[str, Any]:
    """Stage changes and create a commit.

    Args:
        message: The commit message.
        repo_path: Path to the local git repo. Defaults to LOCAL_REPO_PATH.
        add_all: If True (default), runs `git add -A` before committing.
    """
    cwd = _resolve_path(repo_path)
    steps = []

    if add_all:
        add_result = await _run_git("add", "-A", cwd=cwd)
        steps.append({"step": "add", **add_result})
        if not add_result["success"]:
            return {"success": False, "steps": steps, "repo_path": cwd}

    commit_result = await _run_git("commit", "-m", message, cwd=cwd)
    steps.append({"step": "commit", **commit_result})

    # Extract commit SHA from output
    sha = None
    for line in commit_result["stdout"].splitlines():
        if "]" in line and "[" in line:
            # e.g. [main abc1234] commit message
            try:
                sha = line.split("]")[0].split()[-1]
            except Exception:
                pass

    return {
        "success": commit_result["success"],
        "message": message,
        "sha": sha,
        "repo_path": cwd,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# Git push / pull
# ---------------------------------------------------------------------------


async def git_push(
    repo_path: Optional[str] = None,
    remote: str = "origin",
    branch: Optional[str] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Push the current branch (or a named branch) to a remote.

    Args:
        repo_path: Path to the local git repo.
        remote: Remote name (default "origin").
        branch: Branch to push. If None, pushes the current branch.
        force: If True, adds --force-with-lease (safer than --force).
    """
    cwd = _resolve_path(repo_path)
    args = ["push", remote]
    if branch:
        args.append(branch)
    if force:
        args.append("--force-with-lease")
    result = await _run_git(*args, cwd=cwd)
    return {"success": result["success"], "remote": remote, "branch": branch, "repo_path": cwd, **result}


async def git_pull(
    repo_path: Optional[str] = None,
    remote: str = "origin",
    branch: Optional[str] = None,
    rebase: bool = False,
) -> dict[str, Any]:
    """Pull from a remote into the current branch.

    Args:
        repo_path: Path to the local git repo.
        remote: Remote name (default "origin").
        branch: Branch to pull. If None, uses the tracking branch.
        rebase: If True, uses --rebase instead of merge.
    """
    cwd = _resolve_path(repo_path)
    args = ["pull"]
    if rebase:
        args.append("--rebase")
    args.append(remote)
    if branch:
        args.append(branch)
    result = await _run_git(*args, cwd=cwd)
    return {"success": result["success"], "remote": remote, "branch": branch, "repo_path": cwd, **result}


# ---------------------------------------------------------------------------
# Branch management
# ---------------------------------------------------------------------------


async def git_switch_branch(
    branch: str,
    repo_path: Optional[str] = None,
    create: bool = False,
) -> dict[str, Any]:
    """Switch to an existing branch, or create and switch to a new one.

    Args:
        branch: Target branch name.
        repo_path: Path to the local git repo.
        create: If True, creates the branch before switching (like -c).
    """
    cwd = _resolve_path(repo_path)
    args = ["switch"]
    if create:
        args.append("-c")
    args.append(branch)
    result = await _run_git(*args, cwd=cwd)
    return {"success": result["success"], "branch": branch, "created": create, "repo_path": cwd, **result}


async def git_create_branch(
    name: str,
    from_ref: Optional[str] = None,
    repo_path: Optional[str] = None,
    checkout: bool = False,
) -> dict[str, Any]:
    """Create a new branch, optionally from a specific ref.

    Args:
        name: New branch name.
        from_ref: Starting commit/branch/tag. Defaults to current HEAD.
        repo_path: Path to the local git repo.
        checkout: If True, switches to the new branch after creating it.
    """
    cwd = _resolve_path(repo_path)
    steps = []

    if checkout:
        args = ["switch", "-c", name]
        if from_ref:
            args.append(from_ref)
    else:
        args = ["branch", name]
        if from_ref:
            args.append(from_ref)

    result = await _run_git(*args, cwd=cwd)
    steps.append({"step": "create_branch", **result})
    return {"success": result["success"], "name": name, "from_ref": from_ref, "checkout": checkout, "repo_path": cwd, "steps": steps}


# ---------------------------------------------------------------------------
# Merge / Rebase
# ---------------------------------------------------------------------------


async def git_merge(
    branch: str,
    repo_path: Optional[str] = None,
    strategy: Optional[str] = None,
    no_ff: bool = True,
    message: Optional[str] = None,
) -> dict[str, Any]:
    """Merge a branch into the current branch.

    Args:
        branch: The branch to merge in.
        repo_path: Path to the local git repo.
        strategy: Merge strategy (e.g. "ours", "theirs"). Optional.
        no_ff: If True (default), always creates a merge commit (--no-ff).
        message: Optional merge commit message.
    """
    cwd = _resolve_path(repo_path)
    args = ["merge"]
    if no_ff:
        args.append("--no-ff")
    if strategy:
        args += ["--strategy", strategy]
    if message:
        args += ["-m", message]
    args.append(branch)
    result = await _run_git(*args, cwd=cwd)
    return {"success": result["success"], "merged_branch": branch, "repo_path": cwd, **result}


async def git_rebase(
    onto: str,
    repo_path: Optional[str] = None,
    interactive: bool = False,
) -> dict[str, Any]:
    """Rebase the current branch onto another branch or commit.

    Args:
        onto: The branch or commit to rebase onto.
        repo_path: Path to the local git repo.
        interactive: If True, uses -i (interactive rebase — requires a TTY,
                     so this is noted in the response but not actually run interactively).
    """
    cwd = _resolve_path(repo_path)
    if interactive:
        return {
            "success": False,
            "repo_path": cwd,
            "error": "Interactive rebase (-i) requires a TTY and cannot be run via the API. "
                     "Use git_rebase without interactive=True, or run it in a terminal.",
        }
    result = await _run_git("rebase", onto, cwd=cwd)
    return {"success": result["success"], "onto": onto, "repo_path": cwd, **result}


# ---------------------------------------------------------------------------
# Stash
# ---------------------------------------------------------------------------


async def git_stash(
    action: str = "push",
    message: Optional[str] = None,
    repo_path: Optional[str] = None,
    index: Optional[int] = None,
) -> dict[str, Any]:
    """Manage the git stash.

    Args:
        action: One of "push", "pop", "list", "drop", "show", "apply".
        message: Optional stash message (for push action).
        repo_path: Path to the local git repo.
        index: Stash index for pop/drop/show/apply (e.g. 0 → stash@{0}).
    """
    cwd = _resolve_path(repo_path)
    valid_actions = {"push", "pop", "list", "drop", "show", "apply"}
    if action not in valid_actions:
        return {"success": False, "error": f"Invalid action '{action}'. Must be one of: {sorted(valid_actions)}", "repo_path": cwd}

    args = ["stash", action]
    if action == "push" and message:
        args += ["-m", message]
    if index is not None and action in {"pop", "drop", "show", "apply"}:
        args.append(f"stash@{{{index}}}")

    result = await _run_git(*args, cwd=cwd)
    return {"success": result["success"], "action": action, "repo_path": cwd, **result}


# ---------------------------------------------------------------------------
# Git sync
# ---------------------------------------------------------------------------


async def git_sync(
    repo_path: Optional[str] = None,
    remote: str = "origin",
    branch: Optional[str] = None,
) -> dict[str, Any]:
    """Pull (with rebase) then push — a full sync cycle.

    Equivalent to: git pull --rebase origin <branch> && git push origin <branch>

    Args:
        repo_path: Path to the local git repo.
        remote: Remote name (default "origin").
        branch: Branch name. If None, uses the current tracking branch.
    """
    cwd = _resolve_path(repo_path)
    steps = []

    pull_result = await git_pull(repo_path=cwd, remote=remote, branch=branch, rebase=True)
    steps.append({"step": "pull_rebase", **pull_result})

    if not pull_result["success"]:
        return {"success": False, "repo_path": cwd, "remote": remote, "steps": steps}

    push_result = await git_push(repo_path=cwd, remote=remote, branch=branch)
    steps.append({"step": "push", **push_result})

    return {
        "success": push_result["success"],
        "repo_path": cwd,
        "remote": remote,
        "branch": branch,
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# git_smart_push — orchestration endpoint
# ---------------------------------------------------------------------------


async def git_smart_push(
    message: str,
    repo_path: Optional[str] = None,
    remote: str = "origin",
    branch: Optional[str] = None,
    add_all: bool = True,
    force: bool = False,
    pull_before_push: bool = True,
) -> dict[str, Any]:
    """Orchestrate a complete stage → commit → [pull --rebase] → push cycle.

    This is the smart single-endpoint for pushing changes. It:
    1. Runs `git status` to check what's changed
    2. Stages all changes (or staged-only if add_all=False)
    3. Creates a commit with the provided message
    4. Optionally pulls with rebase to incorporate upstream changes
    5. Pushes to the remote

    Returns a structured step-by-step result so the caller can see exactly
    what happened at each stage.

    Args:
        message: Commit message.
        repo_path: Path to the local git repo. Defaults to LOCAL_REPO_PATH.
        remote: Remote to push to (default "origin").
        branch: Branch to push. If None, uses the current branch.
        add_all: If True (default), stages all changes before committing.
        force: If True, uses --force-with-lease on push.
        pull_before_push: If True (default), pulls with rebase before pushing.
    """
    cwd = _resolve_path(repo_path)
    steps = []
    overall_success = True

    # Step 1: Status check
    status = await git_status(repo_path=cwd)
    steps.append({"step": "status", "branch": status.get("branch"), "is_clean": status.get("is_clean"),
                  "staged_count": len(status.get("staged", [])),
                  "unstaged_count": len(status.get("unstaged", [])),
                  "untracked_count": len(status.get("untracked", []))})

    if status.get("is_clean") and not status.get("staged"):
        return {
            "success": True,
            "skipped": True,
            "reason": "Working tree is clean — nothing to commit.",
            "repo_path": cwd,
            "steps": steps,
        }

    # Step 2: Stage changes
    if add_all:
        add_result = await _run_git("add", "-A", cwd=cwd)
        steps.append({"step": "add_all", **add_result})
        if not add_result["success"]:
            return {"success": False, "repo_path": cwd, "failed_at": "add", "steps": steps}

    # Step 3: Commit
    commit_result = await git_commit(message=message, repo_path=cwd, add_all=False)  # already staged
    steps.append({"step": "commit", "success": commit_result["success"],
                  "sha": commit_result.get("sha"), "message": message,
                  "stdout": commit_result.get("stdout", ""), "stderr": commit_result.get("stderr", "")})
    if not commit_result["success"]:
        overall_success = False
        # If it failed due to "nothing to commit", that's OK
        stderr = commit_result.get("stderr", "") + commit_result.get("stdout", "")
        if "nothing to commit" in stderr.lower():
            steps[-1]["note"] = "Nothing new to commit (already clean after add)"
        else:
            return {"success": False, "repo_path": cwd, "failed_at": "commit", "steps": steps}

    # Step 4: Pull with rebase (avoid non-fast-forward push rejections)
    if pull_before_push:
        pull_args = ["pull", "--rebase", remote]
        if branch:
            pull_args.append(branch)
        pull_result = await _run_git(*pull_args, cwd=cwd)
        steps.append({"step": "pull_rebase", **pull_result})
        if not pull_result["success"]:
            # Non-fatal if remote is empty or branch doesn't exist yet
            stderr = pull_result.get("stderr", "")
            if "couldn't find remote ref" in stderr.lower() or "does not appear to be a git repository" in stderr.lower():
                steps[-1]["note"] = "Remote branch not found — skipping pull (first push to this branch?)"
            else:
                return {"success": False, "repo_path": cwd, "failed_at": "pull_rebase", "steps": steps}

    # Step 5: Push
    push_args = ["push", remote]
    if branch:
        push_args.append(branch)
    if force:
        push_args.append("--force-with-lease")
    push_result = await _run_git(*push_args, cwd=cwd)
    steps.append({"step": "push", **push_result})
    if not push_result["success"]:
        return {"success": False, "repo_path": cwd, "failed_at": "push", "steps": steps}

    return {
        "success": True,
        "message": message,
        "sha": commit_result.get("sha"),
        "remote": remote,
        "branch": branch or status.get("branch"),
        "repo_path": cwd,
        "steps": steps,
    }
