"""Command-line entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from git_autocommit import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="git-autocommit",
        description="Generate a Conventional Commits message from the staged diff and commit it.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print("git-autocommit: not implemented yet")
    return 1
