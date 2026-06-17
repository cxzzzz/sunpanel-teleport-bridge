from __future__ import annotations

import logging
import time

from .config import Config
from .mapper import map_cards_to_apps
from .models import ManagedApp, SyncPlan
from .sunpanel import SunPanelClient
from .teleport_agent import TeleportAgent

LOGGER = logging.getLogger(__name__)


def build_plan(desired_apps: list[ManagedApp], current_apps: list[ManagedApp]) -> SyncPlan:
    desired = {app.name: app for app in desired_apps}
    current = {app.name: app for app in current_apps}
    plan = SyncPlan()

    for name, desired_app in desired.items():
        current_app = current.get(name)
        if current_app is None:
            plan.create.append(desired_app)
        elif desired_app.comparable() != current_app.comparable():
            plan.update.append((current_app, desired_app))
        else:
            plan.noop.append(desired_app)

    for name, current_app in current.items():
        if name not in desired:
            plan.delete.append(current_app)

    return plan


def load_desired(config: Config) -> list[ManagedApp]:
    cards = SunPanelClient(config).load_cards()
    return map_cards_to_apps(
        cards,
        managed_by=config.teleport_managed_by,
        url_field=config.sunpanel_url_field,
    )


def run_sync_once(config: Config, *, force_dry_run: bool | None = None) -> SyncPlan:
    dry_run = config.dry_run if force_dry_run is None else force_dry_run
    desired_apps = load_desired(config)
    agent = TeleportAgent(config)
    current_apps: list[ManagedApp] = []

    plan = build_plan(desired_apps, current_apps)
    print_plan(plan)

    if dry_run:
        print("---")
        print(agent.render_config(desired_apps).strip())
        return plan

    changed = agent.write_config_if_changed(desired_apps)
    if changed:
        LOGGER.info("Teleport agent config changed")
    else:
        LOGGER.info("Teleport agent config unchanged")

    return plan


def run_agent_loop(config: Config, *, force_dry_run: bool | None = None) -> None:
    dry_run = config.dry_run if force_dry_run is None else force_dry_run
    if dry_run:
        while True:
            try:
                run_sync_once(config, force_dry_run=True)
            except Exception:
                logging.exception("sync failed")

            time.sleep(config.sync_interval.total_seconds())

    agent = TeleportAgent(config)
    agent.install_signal_handlers()
    while True:
        try:
            desired_apps = load_desired(config)
            changed = agent.write_config_if_changed(desired_apps)
            if changed:
                LOGGER.info("Teleport config changed; restarting agent")
                agent.restart()
            else:
                LOGGER.info("Teleport config unchanged; keeping agent running")
                agent.ensure_running()
        except Exception:
            logging.exception("sync failed")

        time.sleep(config.sync_interval.total_seconds())


def print_plan(plan: SyncPlan) -> None:
    for app in plan.create:
        print(f"CREATE {app.name} uri={app.uri} group={app.group_title}")
    for current, desired in plan.update:
        print(f"UPDATE {desired.name} uri={current.uri} -> {desired.uri} group={desired.group_title}")
    for app in plan.delete:
        print(f"DELETE {app.name} uri={app.uri} group={app.group_title}")
    for app in plan.noop:
        print(f"NOOP {app.name}")
    if not plan.create and not plan.update and not plan.delete and not plan.noop:
        print("NOOP no managed apps")
