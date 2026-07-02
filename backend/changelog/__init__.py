"""Changelog & update-tracking subsystem for DevBrain.

Two-layer design
----------------
1. **Global changelog** — every event (commit, PR, issue, release, ADR) that
   landed in a repo between the previous generation run and *now*.  Written to
   ``GLOBAL_CHANGELOG_{safe_repo}.md`` inside ``.devbrain/changelogs/``.

2. **User updates** — the subset of the global changelog that is relevant to a
   specific GitHub username (their commits, their PRs, issues assigned to them,
   files they touched that were changed by others).  Written to
   ``USER_UPDATES_{username}_{safe_repo}.md`` in the same directory.

Public surface
--------------
``generate_global_changelog(owner, repo)``   → GlobalChangelog dataclass + md path
``generate_user_updates(owner, repo, user)`` → UserUpdates dataclass + md path
"""
