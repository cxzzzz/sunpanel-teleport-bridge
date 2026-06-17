from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SunPanelGroup:
    id: str
    title: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SunPanelCard:
    title: str
    url: str | None
    lan_url: str | None
    group: SunPanelGroup
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ManagedApp:
    name: str
    description: str
    uri: str
    group_title: str
    managed_by: str

    def labels(self) -> dict[str, str]:
        return {
            "managed-by": self.managed_by,
            "sunpanel-group-title": self.group_title,
        }

    def comparable(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "labels": self.labels(),
            "uri": self.uri,
        }

    def to_teleport_resource(self) -> dict[str, Any]:
        return {
            "kind": "app",
            "version": "v3",
            "metadata": {
                "name": self.name,
                "description": self.description,
                "labels": self.labels(),
            },
            "spec": {
                "uri": self.uri,
            },
        }


@dataclass
class SyncPlan:
    create: list[ManagedApp] = field(default_factory=list)
    update: list[tuple[ManagedApp, ManagedApp]] = field(default_factory=list)
    delete: list[ManagedApp] = field(default_factory=list)
    noop: list[ManagedApp] = field(default_factory=list)

    def has_changes(self) -> bool:
        return bool(self.create or self.update or self.delete)
