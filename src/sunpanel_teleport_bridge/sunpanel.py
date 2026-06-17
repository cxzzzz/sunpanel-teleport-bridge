from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import requests

from .config import Config
from .models import SunPanelCard, SunPanelGroup

LOGGER = logging.getLogger(__name__)


class SunPanelClient:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.login()

    def login(self) -> None:
        if not self.config.sunpanel_username or not self.config.sunpanel_password:
            raise RuntimeError("SunPanel username/password are required")
        payload = self.request_json(
            self.config.sunpanel_login_endpoint,
            json_body={
                "username": self.config.sunpanel_username,
                "password": self.config.sunpanel_password,
            },
            skip_auth=True,
        )
        data = self._unwrap_data(payload)
        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise RuntimeError(f"SunPanel login did not return a token: {payload!r}")
        self.session.headers.update({"token": str(token)})

    def request_json(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        skip_auth: bool = False,
    ) -> Any:
        url = urljoin(f"{self.config.sunpanel_base_url}/", endpoint.lstrip("/"))
        if skip_auth:
            headers = headers or {}
        response = self.session.request(
            method,
            url,
            json=json_body or {},
            headers=headers,
            timeout=15,
            verify=not self.config.sunpanel_insecure_skip_verify,
        )
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()

    def probe(self) -> dict[str, Any]:
        groups = self.load_groups_with_cards()
        return {
            "login": "ok",
            "group_count": len(groups),
            "card_count": sum(len(self._first(group, "itemInfos") or []) for group in groups),
            "groups": [
                {
                    "id": self._first(group, "id"),
                    "title": self._first(group, "title"),
                    "card_count": len(self._first(group, "itemInfos") or []),
                }
                for group in groups
            ],
        }

    def load_cards(self) -> list[SunPanelCard]:
        return self._load_panel_cards()

    def load_groups_with_cards(self) -> list[dict[str, Any]]:
        payload = self._unwrap_data(self.request_json(self.config.sunpanel_items_endpoint))
        return self._unwrap_list(payload)

    def _load_panel_cards(self) -> list[SunPanelCard]:
        items = self.load_groups_with_cards()
        cards: list[SunPanelCard] = []
        for item in items:
            nested = self._first(item, "itemInfos", "itemIcons", "items", "list", "children", "cards")
            if isinstance(nested, list):
                group_title = str(self._first(item, "title", "name", "itemGroupTitle", "groupTitle") or "default")
                group_id = str(
                    self._first(item, "id", "itemIconGroupId", "itemGroupID", "itemGroupId", "groupId") or group_title
                )
                group = SunPanelGroup(id=group_id, title=group_title, raw=item)
                for child in nested:
                    if isinstance(child, dict):
                        card = self._parse_card(child, group)
                        if card is not None:
                            cards.append(card)
                continue

            group_title = str(self._first(item, "itemIconGroupTitle", "itemGroupTitle", "groupTitle", "groupName") or "default")
            group_id = str(self._first(item, "itemIconGroupId", "itemGroupID", "itemGroupId", "groupId") or group_title)
            group = SunPanelGroup(id=group_id, title=group_title, raw={})
            card = self._parse_card(item, group)
            if card is not None:
                cards.append(card)
        return cards

    def _parse_card(self, item: dict[str, Any], group: SunPanelGroup) -> SunPanelCard | None:
        title = self._first(item, "title", "name", "label")
        if not title:
            LOGGER.debug("Skipping card with unknown shape: %r", item)
            return None
        return SunPanelCard(
            title=str(title),
            url=self._optional_str(self._first(item, "url", "Url")),
            lan_url=self._optional_str(self._first(item, "lanUrl", "LanUrl", "lan_url")),
            group=group,
            raw=item,
        )

    @staticmethod
    def _unwrap_data(payload: Any) -> Any:
        if isinstance(payload, dict):
            for key in ("data", "Data", "result", "Result"):
                if key in payload:
                    return payload[key]
        return payload

    @classmethod
    def _unwrap_list(cls, payload: Any) -> list[dict[str, Any]]:
        payload = cls._unwrap_data(payload)
        if isinstance(payload, dict):
            for key in ("list", "items", "rows", "data"):
                if isinstance(payload.get(key), list):
                    return payload[key]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    @staticmethod
    def _first(item: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in item and item[key] not in (None, ""):
                return item[key]
        return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None
