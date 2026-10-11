"""Load the user configuration file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class Identity:
    name: str
    email: str


@dataclass(frozen=True)
class Config:
    primary: ModelSpec
    secondary: ModelSpec
    identity: Identity | None
    language: str
    max_diff_bytes: int = 250_000


DEFAULT_CONFIG = Config(
    primary=ModelSpec(provider="codex", model="gpt-6-luna", reasoning_effort="low"),
    secondary=ModelSpec(provider="claude", model="claude-haiku-5-5", reasoning_effort="low"),
    identity=None,
    language="日本語",
)


PROVIDERS = ("codex", "claude")


class ConfigError(Exception):
    pass


def default_config_path() -> Path:
    return Path.home() / ".config" / "git-autocommit" / "config.toml"


def load_config(path: Path) -> Config:
    if not path.is_file():
        return DEFAULT_CONFIG
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc

    return Config(
        primary=_model_spec(path, data, "primary", DEFAULT_CONFIG.primary),
        secondary=_model_spec(path, data, "secondary", DEFAULT_CONFIG.secondary),
        identity=_identity(path, data),
        language=_string(path, data, "language", DEFAULT_CONFIG.language),
        max_diff_bytes=_positive_int(path, data, "max_diff_bytes", DEFAULT_CONFIG.max_diff_bytes),
    )


def _model_spec(path: Path, data: dict[str, Any], key: str, default: ModelSpec) -> ModelSpec:
    if key not in data:
        return default
    table = _table(path, data, key)
    spec = ModelSpec(
        provider=_required_string(path, table, key, "provider"),
        model=_required_string(path, table, key, "model"),
        reasoning_effort=_required_string(path, table, key, "reasoning_effort"),
    )
    if spec.provider not in PROVIDERS:
        raise ConfigError(f"{path}: [{key}].provider must be one of {', '.join(PROVIDERS)}")
    return spec


def _identity(path: Path, data: dict[str, Any]) -> Identity | None:
    if "identity" not in data:
        return None
    table = _table(path, data, "identity")
    return Identity(
        name=_required_string(path, table, "identity", "name"),
        email=_required_string(path, table, "identity", "email"),
    )


def _table(path: Path, data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data[key]
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: [{key}] must be a table")
    return value


def _required_string(path: Path, table: dict[str, Any], section: str, key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{path}: [{section}].{key} must be a non-empty string")
    return value


def _string(path: Path, data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{path}: {key} must be a non-empty string")
    return value


def _positive_int(path: Path, data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{path}: {key} must be a positive integer")
    return value
