from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml


_ENV_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")
_PATH_KEYS = {"raw_data", "processed_data", "report_output"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {} if data is None else data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_env_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env_values(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_resolve_env_values(item) for item in value]
    if isinstance(value, str):
        match = _ENV_PATTERN.match(value)
        if match:
            env_name = match.group(1)
            if env_name not in os.environ:
                raise ValueError(f"missing required environment variable: {env_name}")
            return os.environ[env_name]
    return value


def _resolve_paths(settings: dict[str, Any], project_root: Path) -> dict[str, Any]:
    paths = dict(settings.get("paths", {}))
    for key in _PATH_KEYS:
        if key in paths and paths[key] is not None:
            path_value = Path(paths[key])
            if not path_value.is_absolute():
                path_value = project_root / path_value
            paths[key] = path_value
    settings["paths"] = paths
    return settings


def load_settings(config_path: str | Path, project_root: Path | None = None) -> dict[str, Any]:
    config_path = Path(config_path)
    if project_root is None:
        project_root = config_path.resolve().parents[1]
    base_config_path = config_path.parent / "base.yaml"

    base_cfg = _load_yaml(base_config_path)
    env_cfg = _load_yaml(config_path)
    merged = _deep_merge(base_cfg, env_cfg)
    merged = _resolve_env_values(merged)
    return _resolve_paths(merged, project_root)
