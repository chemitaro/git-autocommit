from pathlib import Path

import pytest

from git_autocommit.config import Config, ConfigError, Identity, ModelSpec, load_config


def test_missing_file_uses_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "absent.toml")

    assert config == Config(
        primary=ModelSpec(provider="codex", model="gpt-6-luna", reasoning_effort="low"),
        secondary=ModelSpec(provider="claude", model="claude-haiku-5-5", reasoning_effort="low"),
        identity=None,
        language="日本語",
    )


def test_file_values_override_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
language = "English"

[primary]
provider = "claude"
model = "claude-haiku-5-5"
reasoning_effort = "medium"

[identity]
name = "Alice"
email = "alice@example.com"
""",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config == Config(
        primary=ModelSpec(provider="claude", model="claude-haiku-5-5", reasoning_effort="medium"),
        secondary=ModelSpec(provider="claude", model="claude-haiku-5-5", reasoning_effort="low"),
        identity=Identity(name="Alice", email="alice@example.com"),
        language="English",
    )


def test_unknown_provider_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[secondary]\nprovider = "gemini"\nmodel = "x"\nreasoning_effort = "low"\n', encoding="utf-8")

    with pytest.raises(ConfigError, match=r"\[secondary\]\.provider"):
        load_config(path)
