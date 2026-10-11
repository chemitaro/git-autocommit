"""Invoke the codex / claude CLIs to generate a commit message."""

from __future__ import annotations

import os
import subprocess
import tempfile

from git_autocommit.config import ModelSpec

TIMEOUT_SECONDS = 180
# Strip API keys so both CLIs authenticate with the logged-in subscription instead of metered API billing.
STRIPPED_ENV_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")


class ProviderError(Exception):
    pass


def build_command(spec: ModelSpec) -> list[str]:
    if spec.provider == "codex":
        return [
            "codex",
            "exec",
            "--model",
            spec.model,
            "--config",
            f'model_reasoning_effort="{spec.reasoning_effort}"',
            "--config",
            "notify=[]",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--ephemeral",
            "--color",
            "never",
            "-",
        ]
    if spec.provider == "claude":
        return [
            "claude",
            "-p",
            "--model",
            spec.model,
            "--effort",
            spec.reasoning_effort,
            "--tools",
            "",
            "--no-session-persistence",
            "--disable-slash-commands",
            "--strict-mcp-config",
        ]
    raise ProviderError(f"unknown provider: {spec.provider}")


def generate(spec: ModelSpec, prompt: str) -> str:
    command = build_command(spec)
    env = {key: value for key, value in os.environ.items() if key not in STRIPPED_ENV_KEYS}
    # Run outside the repository so the CLI does not load project instructions or touch the worktree.
    with tempfile.TemporaryDirectory(prefix="git-autocommit-") as workdir:
        try:
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                cwd=workdir,
                env=env,
                timeout=TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise ProviderError(f"{command[0]} is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"{command[0]} timed out after {TIMEOUT_SECONDS}s") from exc
    if result.returncode != 0:
        raise ProviderError(f"{command[0]} exited with {result.returncode}: {_tail(result.stderr)}")
    message = clean_message(result.stdout)
    if not message:
        raise ProviderError(f"{command[0]} returned an empty message")
    return message


def clean_message(text: str) -> str:
    lines = text.strip().splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        lines = lines[1:-1]
    return "\n".join(lines).strip()


def _tail(text: str, limit: int = 800) -> str:
    text = text.strip()
    return text if len(text) <= limit else "..." + text[-limit:]
