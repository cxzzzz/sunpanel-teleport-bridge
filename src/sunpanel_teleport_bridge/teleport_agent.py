from __future__ import annotations

import logging
import signal
import subprocess

import yaml

from .config import Config
from .models import ManagedApp

LOGGER = logging.getLogger(__name__)


class TeleportAgent:
    def __init__(self, config: Config):
        self.config = config
        self.process: subprocess.Popen[str] | None = None

    def render_config(self, apps: list[ManagedApp]) -> str:
        if not self.config.teleport_proxy:
            raise RuntimeError("TELEPORT_PROXY is required")

        teleport_config: dict[str, object] = {
            "version": "v3",
            "teleport": {
                "data_dir": str(self.config.teleport_data_dir),
                "proxy_server": self.config.teleport_proxy,
                "log": {
                    "output": "stderr",
                    "severity": "INFO",
                    "format": {"output": "text"},
                },
                "ca_pin": "",
                "diag_addr": "",
            },
            "auth_service": {"enabled": "no"},
            "proxy_service": {"enabled": "no", "acme": {}},
            "ssh_service": {"enabled": "no"},
            "app_service": {
                "enabled": "yes",
                "debug_app": False,
                "mcp_demo_server": False,
                "apps": [self._app_config(app) for app in apps],
            },
        }
        if self.config.teleport_join_token:
            teleport_config["teleport"]["join_params"] = {  # type: ignore[index]
                "token_name": self.config.teleport_join_token,
                "method": "token",
            }

        return yaml.safe_dump(teleport_config, sort_keys=False, allow_unicode=True)

    def write_config_if_changed(self, apps: list[ManagedApp]) -> bool:
        rendered = self.render_config(apps)
        path = self.config.teleport_config_path
        previous = path.read_text() if path.exists() else None
        if previous == rendered:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered)
        return True

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        LOGGER.info("Starting Teleport agent with %s", self.config.teleport_config_path)
        command = [self.config.teleport_bin, "start", "--config", str(self.config.teleport_config_path)]
        if self.config.teleport_insecure_skip_verify:
            command.append("--insecure")
        self.process = subprocess.Popen(
            command,
            text=True,
        )

    def restart(self) -> None:
        self.stop()
        self.start()

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        LOGGER.info("Stopping Teleport agent")
        self.process.send_signal(signal.SIGTERM)
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            LOGGER.warning("Teleport agent did not stop after SIGTERM; sending SIGKILL")
            self.process.kill()
            self.process.wait(timeout=10)

    def ensure_running(self) -> None:
        if self.process and self.process.poll() is not None:
            LOGGER.warning("Teleport agent exited with code %s; starting again", self.process.returncode)
            self.process = None
        self.start()

    def _app_config(self, app: ManagedApp) -> dict[str, object]:
        return {
            "name": app.name,
            "uri": app.uri,
            "public_addr": "",
            "insecure_skip_verify": self.config.teleport_app_insecure_skip_verify,
            "use_any_proxy_public_addr": self.config.teleport_app_use_any_proxy_public_addr,
            "description": app.description,
            "labels": app.labels(),
        }

    def install_signal_handlers(self) -> None:
        def handle_signal(signum: int, _frame: object) -> None:
            LOGGER.info("Received signal %s", signum)
            self.stop()
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
