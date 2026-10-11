"""Thin wrappers around the git CLI."""

from __future__ import annotations

import subprocess


class GitError(Exception):
    pass


def run_git(*args: str, input_text: str | None = None) -> str:
    try:
        result = subprocess.run(["git", *args], input=input_text, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise GitError("git is not installed") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def is_inside_work_tree() -> bool:
    try:
        return run_git("rev-parse", "--is-inside-work-tree").strip() == "true"
    except GitError:
        return False


def has_staged_changes() -> bool:
    result = subprocess.run(["git", "diff", "--cached", "--quiet", "--exit-code"], capture_output=True)
    if result.returncode not in (0, 1):
        raise GitError(f"git diff --cached failed: {result.stderr.decode(errors='replace').strip()}")
    return result.returncode == 1


def staged_diff(*extra: str) -> str:
    return run_git("diff", "--cached", "--no-color", *extra)


def commit(message: str) -> int:
    """Run `git commit` with hooks enabled, streaming its output to the terminal."""
    return subprocess.run(["git", "commit", "-F", "-"], input=message, text=True).returncode


def identity_mismatches(name: str, email: str) -> list[str]:
    """Return the roles (author/committer) whose resolved identity differs from `name <email>`."""
    expected = f"{name} <{email}> "
    mismatches = []
    for role in ("author", "committer"):
        ident = run_git("var", f"GIT_{role.upper()}_IDENT")
        if not ident.startswith(expected):
            mismatches.append(role)
    return mismatches


def staged_numstat() -> list[tuple[int, str]]:
    """Return (changed lines, path) for each staged file; binary files count as 0 lines."""
    fields = staged_diff("--numstat", "-z", "-M").split("\0")
    entries = []
    index = 0
    while index < len(fields) and fields[index]:
        added, deleted, path = fields[index].split("\t", 2)
        index += 1
        if not path:  # rename/copy: the old and new paths follow as separate fields
            path = fields[index + 1]
            index += 2
        changed = int(added) + int(deleted) if added.isdigit() and deleted.isdigit() else 0
        entries.append((changed, path))
    return entries
