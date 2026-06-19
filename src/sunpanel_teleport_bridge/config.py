from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_duration(value: str) -> timedelta:
    value = value.strip().lower()
    if value.endswith("ms"):
        return timedelta(milliseconds=float(value[:-2]))
    if value.endswith("s"):
        return timedelta(seconds=float(value[:-1]))
    if value.endswith("m"):
        return timedelta(minutes=float(value[:-1]))
    if value.endswith("h"):
        return timedelta(hours=float(value[:-1]))
    return timedelta(seconds=float(value))


@dataclass(frozen=True)
class Config:
    sunpanel_base_url: str
    sunpanel_username: str | None
    sunpanel_password: str | None
    sunpanel_insecure_skip_verify: bool
    sunpanel_url_field: str
    sunpanel_login_endpoint: str
    sunpanel_items_endpoint: str
    teleport_bin: str
    teleport_proxy: str | None
    teleport_join_token: str | None
    teleport_insecure_skip_verify: bool
    teleport_app_insecure_skip_verify: bool
    teleport_app_use_any_proxy_public_addr: bool
    teleport_data_dir: Path
    teleport_config_path: Path
    app_overrides_path: Path | None
    teleport_managed_by: str
    sync_interval: timedelta
    dry_run: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        base_url = _env("SUNPANEL_BASE_URL")
        username = _env("SUNPANEL_USERNAME")
        password = _env("SUNPANEL_PASSWORD")
        if not base_url:
            raise ValueError("SUNPANEL_BASE_URL is required")
        if not username or not password:
            raise ValueError("SUNPANEL_USERNAME and SUNPANEL_PASSWORD are required")

        return cls(
            sunpanel_base_url=base_url.rstrip("/"),
            sunpanel_username=username,
            sunpanel_password=password,
            sunpanel_insecure_skip_verify=parse_bool(_env("SUNPANEL_INSECURE_SKIP_VERIFY"), False),
            sunpanel_url_field=_env("SUNPANEL_URL_FIELD", "preferLanUrl") or "preferLanUrl",
            sunpanel_login_endpoint=_env("SUNPANEL_LOGIN_ENDPOINT", "/api/login") or "/api/login",
            sunpanel_items_endpoint=_env("SUNPANEL_ITEMS_ENDPOINT", "/api/panel/itemIcon/getListAllGroup")
            or "/api/panel/itemIcon/getListAllGroup",
            teleport_bin=_env("TELEPORT_BIN", "teleport") or "teleport",
            teleport_proxy=_env("TELEPORT_PROXY"),
            teleport_join_token=_env("TELEPORT_JOIN_TOKEN"),
            teleport_insecure_skip_verify=parse_bool(_env("TELEPORT_INSECURE_SKIP_VERIFY"), False),
            teleport_app_insecure_skip_verify=parse_bool(_env("TELEPORT_APP_INSECURE_SKIP_VERIFY"), True),
            teleport_app_use_any_proxy_public_addr=parse_bool(
                _env("TELEPORT_APP_USE_ANY_PROXY_PUBLIC_ADDR"), True
            ),
            teleport_data_dir=Path(_env("TELEPORT_DATA_DIR", "/var/lib/teleport") or "/var/lib/teleport"),
            teleport_config_path=Path(
                _env("TELEPORT_CONFIG_PATH", "/etc/teleport/sunpanel-apps.yaml")
                or "/etc/teleport/sunpanel-apps.yaml"
            ),
            app_overrides_path=Path(_env("APP_OVERRIDES_PATH", "/etc/sunpanel-teleport-bridge/overrides.yaml"))
            if _env("APP_OVERRIDES_PATH", "/etc/sunpanel-teleport-bridge/overrides.yaml")
            else None,
            teleport_managed_by=_env("TELEPORT_MANAGED_BY", "sunpanel-teleport-bridge")
            or "sunpanel-teleport-bridge",
            sync_interval=parse_duration(_env("SYNC_INTERVAL", "300s") or "300s"),
            dry_run=parse_bool(_env("DRY_RUN"), True),
            log_level=(_env("LOG_LEVEL", "info") or "info").lower(),
        )
