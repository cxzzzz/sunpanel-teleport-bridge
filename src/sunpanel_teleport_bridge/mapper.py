from __future__ import annotations

import hashlib
import re
import unicodedata

from .models import ManagedApp, SunPanelCard


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    if slug:
        return slug[:48].strip("-")
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"x-{digest}"


def pick_uri(card: SunPanelCard, strategy: str) -> str | None:
    strategy = strategy.strip()
    if strategy == "url":
        return card.url
    if strategy == "lanUrl":
        return card.lan_url
    if strategy == "preferUrl":
        return card.url or card.lan_url
    return card.lan_url or card.url


def map_cards_to_apps(cards: list[SunPanelCard], *, managed_by: str, url_field: str) -> list[ManagedApp]:
    apps: list[ManagedApp] = []
    seen: set[str] = set()
    for card in cards:
        uri = pick_uri(card, url_field)
        if not uri:
            continue
        base_name = slugify(card.title)
        name = base_name[:63].strip("-")
        if name in seen:
            digest = hashlib.sha1(f"{card.group.title}/{card.title}/{uri}".encode("utf-8")).hexdigest()[:6]
            name = f"{name[:56].strip('-')}-{digest}"
        seen.add(name)
        apps.append(
            ManagedApp(
                name=name,
                description=card.title,
                uri=uri,
                group_title=card.group.title,
                managed_by=managed_by,
            )
        )
    return apps
