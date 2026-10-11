"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from git_autocommit import __version__, git
from git_autocommit.config import Config, ConfigError, default_config_path, load_config
from git_autocommit.prompt import build_prompt
from git_autocommit.providers import ProviderError, generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="git-autocommit",
        description=(
            "Generate a Conventional Commits message from the staged diff (git diff --cached) "
            "with a fast, low-cost model and commit it. Does not run git add."
        ),
        epilog=f"Config: {default_config_path()}",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--confirm", action="store_true", help="ask y/N on the terminal before committing")
    mode.add_argument("--dry-run", action="store_true", help="print the generated message without committing")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.confirm and not sys.stdin.isatty():
        _log("No TTY available for confirmation. Aborting without committing.")
        return 1
    try:
        config = load_config(default_config_path())
    except ConfigError as exc:
        _log(f"Invalid config: {exc}")
        return 2

    try:
        if not git.is_inside_work_tree():
            _log("Not inside a Git repository.")
            return 1
        if not git.has_staged_changes():
            _log("No staged changes found. Stage first (e.g., git add <paths>) and rerun.")
            return 1
        if not _identity_ok(config):
            return 1
        prompt = build_prompt(config.language, config.max_diff_bytes)
    except git.GitError as exc:
        _log(str(exc))
        return 1

    message = _generate_with_fallback(config, prompt)
    if message is None:
        return 1

    print(message, flush=True)
    if args.dry_run:
        return 0
    if args.confirm:
        print("Commit with the above message? [y/N]: ", end="", file=sys.stderr, flush=True)
        if sys.stdin.readline().strip().lower() not in ("y", "yes"):
            _log("Aborted. No commit created.")
            return 0
    try:
        if not _identity_ok(config):
            return 1
    except git.GitError as exc:
        _log(str(exc))
        return 1
    return git.commit(message + "\n")


def _identity_ok(config: Config) -> bool:
    if config.identity is None:
        return True
    mismatches = git.identity_mismatches(config.identity.name, config.identity.email)
    if mismatches:
        _log(
            f"Git {' and '.join(mismatches)} identity is not {config.identity.name} <{config.identity.email}>. "
            "Refusing to commit."
        )
        return False
    return True


def _generate_with_fallback(config: Config, prompt: str) -> str | None:
    for label, spec in (("primary", config.primary), ("secondary", config.secondary)):
        _log(f"Generating a commit message with {label}: {spec.provider} / {spec.model} ({spec.reasoning_effort})...")
        try:
            return generate(spec, prompt)
        except ProviderError as exc:
            _log(f"{label} failed: {exc}")
    _log("No commit message produced. No commit created.")
    return None


def _log(message: str) -> None:
    print(message, file=sys.stderr)
