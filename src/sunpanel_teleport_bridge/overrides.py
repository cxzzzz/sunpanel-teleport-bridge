from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)


def load_app_overrides(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    if path.is_dir():
        LOGGER.warning("App overrides path %s is a directory; ignoring it", path)
        return {}

    raw = yaml.safe_load(path.read_text())
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"App overrides file {path} must contain a mapping")

    apps = raw.get("apps", {})
    if apps is None:
        return {}
    if not isinstance(apps, dict):
        raise ValueError(f"App overrides file {path} field 'apps' must be a mapping")

    overrides: dict[str, dict[str, Any]] = {}
    for app_name, app_config in apps.items():
        if not isinstance(app_name, str):
            raise ValueError(f"App overrides file {path} contains a non-string app name")
        if app_config is None:
            continue
        if not isinstance(app_config, dict):
            raise ValueError(f"Override for app {app_name!r} must be a mapping")

        if "name" in app_config:
            raise ValueError(f"Override for app {app_name!r} must not override 'name'")

        overrides[app_name] = app_config

    return overrides


def merge_app_overrides(
    app_configs: list[dict[str, Any]],
    overrides: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not overrides:
        return app_configs

    seen = {str(app_config.get("name")) for app_config in app_configs}
    for app_name in sorted(set(overrides) - seen):
        LOGGER.warning("App override %s does not match any generated app", app_name)

    result: list[dict[str, Any]] = []
    for app_config in app_configs:
        app_name = str(app_config.get("name"))
        override = overrides.get(app_name)
        if not override:
            result.append(app_config)
            continue
        result.append(deep_merge(app_config, override))
    return result


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, override_value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = deep_merge(base_value, override_value)
            continue
        merged[key] = deepcopy(override_value)
    return merged
