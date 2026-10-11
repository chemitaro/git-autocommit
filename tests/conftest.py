from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

FAKE_CLI = """#!/bin/sh
name=$(basename "$0")
upper=$(printf '%s' "$name" | tr '[:lower:]' '[:upper:]')
log="$FAKE_LOG_DIR/$name"
mkdir -p "$log"
cat > "$log/stdin"
printf '%s\\n' "$@" > "$log/args"
env > "$log/env"
pwd > "$log/cwd"
eval "output=\\${FAKE_${upper}_OUTPUT-}"
eval "code=\\${FAKE_${upper}_EXIT:-0}"
eval "err=\\${FAKE_${upper}_STDERR-}"
printf '%s' "$output"
[ -n "$err" ] && printf '%s\\n' "$err" >&2
exit "$code"
"""


@dataclass
class Env:
    repo: Path
    home: Path
    log_dir: Path
    monkeypatch: pytest.MonkeyPatch

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def stage(self, name: str, content: str) -> None:
        (self.repo / name).write_text(content, encoding="utf-8")
        self.git("add", "--", name)

    def fake(self, provider: str, *, output: str = "", exit_code: int = 0, stderr: str = "") -> None:
        upper = provider.upper()
        self.monkeypatch.setenv(f"FAKE_{upper}_OUTPUT", output)
        self.monkeypatch.setenv(f"FAKE_{upper}_EXIT", str(exit_code))
        self.monkeypatch.setenv(f"FAKE_{upper}_STDERR", stderr)

    def called(self, provider: str) -> bool:
        return (self.log_dir / provider).is_dir()

    def args(self, provider: str) -> list[str]:
        return (self.log_dir / provider / "args").read_text(encoding="utf-8").splitlines()

    def stdin(self, provider: str) -> str:
        return (self.log_dir / provider / "stdin").read_text(encoding="utf-8")

    def child_env(self, provider: str) -> dict[str, str]:
        lines = (self.log_dir / provider / "env").read_text(encoding="utf-8").splitlines()
        return dict(line.split("=", 1) for line in lines if "=" in line)

    def write_config(self, text: str) -> None:
        path = self.home / ".config" / "git-autocommit" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def last_commit_message(self) -> str:
        return self.git("log", "-1", "--format=%B").strip()

    def commit_count(self) -> int:
        result = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=self.repo, capture_output=True, text=True)
        return int(result.stdout) if result.returncode == 0 else 0


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Env:
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("codex", "claude"):
        script = bin_dir / name
        script.write_text(FAKE_CLI, encoding="utf-8")
        script.chmod(0o755)
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_LOG_DIR", str(log_dir))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(repo)

    environment = Env(repo=repo, home=home, log_dir=log_dir, monkeypatch=monkeypatch)
    environment.git("init", "-q", "-b", "main")
    environment.git("config", "user.name", "Test User")
    environment.git("config", "user.email", "test@example.com")
    environment.git("config", "commit.gpgsign", "false")
    return environment
