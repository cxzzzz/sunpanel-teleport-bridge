from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import Config
from .sunpanel import SunPanelClient
from .sync import run_agent_loop, run_sync_once


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_probe(config: Config) -> int:
    client = SunPanelClient(config)
    print(json.dumps(client.probe(), ensure_ascii=False, indent=2))
    return 0


def cmd_sync(config: Config, args: argparse.Namespace) -> int:
    dry_run = True if args.dry_run else None
    if args.once:
        run_sync_once(config, force_dry_run=dry_run)
        return 0

    run_agent_loop(config, force_dry_run=dry_run)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sunpanel-teleport-bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("probe")
    sync = subparsers.add_parser("sync")
    sync.add_argument("--once", action="store_true", help="Run one sync pass and exit")
    sync.add_argument("--dry-run", action="store_true", help="Force dry-run mode")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        config = Config.from_env()
        configure_logging(config.log_level)
        if args.command == "probe":
            return cmd_probe(config)
        if args.command == "sync":
            return cmd_sync(config, args)
    except Exception as exc:  # noqa: BLE001 - command-line boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
