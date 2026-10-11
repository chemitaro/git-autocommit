import io

import pytest

from git_autocommit.cli import main
from tests.conftest import Env


def test_commits_staged_changes_with_primary_message(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    env.stage("hello.txt", "hello\n")
    env.fake("codex", output="feat: 挨拶ファイルを追加\n\n- hello.txt を追加\n")

    exit_code = main([])

    assert exit_code == 0
    assert env.last_commit_message() == "feat: 挨拶ファイルを追加\n\n- hello.txt を追加"
    assert "feat: 挨拶ファイルを追加" in capsys.readouterr().out
    assert "hello" in env.stdin("codex")
    assert not env.called("claude")


def test_falls_back_to_secondary_when_primary_fails(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    env.stage("a.txt", "a\n")
    env.fake("codex", exit_code=1, stderr="model is not available")
    env.fake("claude", output="chore: a.txt を追加")

    exit_code = main([])

    assert exit_code == 0
    assert env.last_commit_message() == "chore: a.txt を追加"
    assert "model is not available" in capsys.readouterr().err
    assert "a.txt" in env.stdin("claude")


def test_fails_without_commit_when_both_providers_fail(env: Env) -> None:
    env.stage("a.txt", "a\n")
    env.fake("codex", exit_code=1)
    env.fake("claude", output="   \n")

    assert main([]) == 1
    assert env.commit_count() == 0


def test_provider_cli_receives_configured_model_without_api_keys(env: Env) -> None:
    env.write_config(
        """
[primary]
provider = "codex"
model = "gpt-test"
reasoning_effort = "medium"

[secondary]
provider = "claude"
model = "claude-test"
reasoning_effort = "high"
"""
    )
    env.monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")
    env.monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-secret")
    env.stage("a.txt", "a\n")
    env.fake("codex", exit_code=1)
    env.fake("claude", output="chore: a.txt を追加")

    assert main([]) == 0

    codex_args = env.args("codex")
    assert codex_args[:3] == ["exec", "--model", "gpt-test"]
    assert 'model_reasoning_effort="medium"' in codex_args
    assert codex_args[codex_args.index("--sandbox") : codex_args.index("--sandbox") + 2] == ["--sandbox", "read-only"]
    claude_args = env.args("claude")
    assert claude_args[:5] == ["-p", "--model", "claude-test", "--effort", "high"]
    for provider in ("codex", "claude"):
        child_env = env.child_env(provider)
        assert "ANTHROPIC_API_KEY" not in child_env
        assert "OPENAI_API_KEY" not in child_env


def test_dry_run_prints_message_without_committing(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    env.stage("a.txt", "a\n")
    env.fake("codex", output="chore: a.txt を追加")

    assert main(["--dry-run"]) == 0

    assert capsys.readouterr().out.strip() == "chore: a.txt を追加"
    assert env.commit_count() == 0
    assert env.git("diff", "--cached", "--name-only").strip() == "a.txt"


class FakeTty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.mark.parametrize(("answer", "commits"), [("y\n", 1), ("n\n", 0), ("\n", 0)])
def test_confirm_commits_only_after_yes(env: Env, answer: str, commits: int) -> None:
    env.stage("a.txt", "a\n")
    env.fake("codex", output="chore: a.txt を追加")
    env.monkeypatch.setattr("sys.stdin", FakeTty(answer))

    assert main(["--confirm"]) == 0
    assert env.commit_count() == commits


def test_confirm_without_tty_aborts(env: Env) -> None:
    env.stage("a.txt", "a\n")
    env.fake("codex", output="chore: a.txt を追加")
    env.monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))

    assert main(["--confirm"]) == 1
    assert env.commit_count() == 0
    assert not env.called("codex")


def test_no_staged_changes_exits_without_calling_providers(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    (env.repo / "untracked.txt").write_text("x\n", encoding="utf-8")

    assert main([]) == 1
    assert "No staged changes" in capsys.readouterr().err
    assert not env.called("codex")


IDENTITY_CONFIG = """
[identity]
name = "Expected User"
email = "expected@example.com"
"""


def test_identity_mismatch_refuses_before_generating(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    env.write_config(IDENTITY_CONFIG)
    env.stage("a.txt", "a\n")
    env.fake("codex", output="chore: a.txt を追加")

    assert main([]) == 1
    assert "author" in capsys.readouterr().err.lower()
    assert not env.called("codex")
    assert env.commit_count() == 0


def test_identity_match_allows_commit(env: Env) -> None:
    env.write_config(IDENTITY_CONFIG)
    env.git("config", "user.name", "Expected User")
    env.git("config", "user.email", "expected@example.com")
    env.stage("a.txt", "a\n")
    env.fake("codex", output="chore: a.txt を追加")

    assert main([]) == 0
    assert env.git("log", "-1", "--format=%an <%ae>|%cn <%ce>").strip() == (
        "Expected User <expected@example.com>|Expected User <expected@example.com>"
    )


def test_large_diff_sends_summary_and_excerpts_instead_of_full_diff(env: Env) -> None:
    env.write_config("max_diff_bytes = 4000\n")
    big_lines = [f"line {i:04d} of the large generated file" for i in range(400)]
    env.stage("big.txt", "\n".join(big_lines) + "\n")
    env.stage("small.txt", "small change\n")
    env.fake("codex", output="chore: ファイルを追加")

    assert main([]) == 0

    prompt = env.stdin("codex")
    assert "FULL STAGED DIFF" not in prompt
    assert "A\tbig.txt" in prompt
    assert "A\tsmall.txt" in prompt
    assert "+small change" in prompt
    assert "+line 0000 of the large generated file" in prompt
    assert "+line 0399 of the large generated file" not in prompt
    assert "[TRUNCATED" in prompt


def test_large_diff_excerpts_follow_renamed_paths(env: Env) -> None:
    content = "".join(f"stable line {i}\n" for i in range(50))
    env.stage("old name.txt", content)
    env.git("commit", "-q", "-m", "init")
    env.git("mv", "old name.txt", "new name.txt")
    (env.repo / "new name.txt").write_text(content + "appended line\n", encoding="utf-8")
    env.git("add", "--", "new name.txt")
    env.write_config("max_diff_bytes = 10\n")
    env.fake("codex", output="refactor: ファイル名を変更")

    assert main([]) == 0
    assert "# FILE: new name.txt\n" in env.stdin("codex")


def test_failing_pre_commit_hook_blocks_commit(env: Env) -> None:
    hook = env.repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    env.stage("a.txt", "a\n")
    env.fake("codex", output="chore: a.txt を追加")

    assert main([]) != 0
    assert env.commit_count() == 0


def test_code_fence_around_message_is_removed(env: Env) -> None:
    env.stage("a.txt", "a\n")
    env.fake("codex", output="```\nchore: a.txt を追加\n```\n")

    assert main([]) == 0
    assert env.last_commit_message() == "chore: a.txt を追加"
