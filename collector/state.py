"""Zustand zwischen zwei Läufen (state.json). Enthält keine Anrisstexte."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import Item
from .output import iso, write_json_atomic

EMPTY = {"http_cache": {}, "first_seen": {}, "og_cache": {}, "icon_cache": {}, "items": {}, "stories": {}}


def load_state(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {k: dict(data.get(k) or {}) for k in EMPTY}


def save_state(path: Path, state: dict) -> None:
    write_json_atomic(path, state)


def item_to_dict(it: Item) -> dict:
    return {
        "id": it.id,
        "source_id": it.source_id,
        "title": it.title,
        "link": it.link,
        "published": iso(it.published),
        "image": it.image,
        "regions": sorted(it.regions),
        "categories": sorted(it.categories),
        "plus": it.plus,
        "has_date": it.has_date,
        "stems": it.stems,
        "keywords": it.keywords,
        "publisher": it.publisher,
        "site": it.site,
        "topic": it.topic,
    }


def item_from_dict(d: dict) -> Item:
    return Item(
        id=d["id"],
        source_id=d["source_id"],
        title=d["title"],
        link=d["link"],
        published=datetime.fromisoformat(d["published"].replace("Z", "+00:00")),
        image=d.get("image"),
        regions=set(d.get("regions") or ()),
        categories=set(d.get("categories") or ()),
        plus=bool(d.get("plus")),
        has_date=bool(d.get("has_date", True)),
        stems=list(d.get("stems") or ()),
        keywords=list(d.get("keywords") or ()),
        publisher=d.get("publisher"),
        site=d.get("site"),
        topic=d.get("topic"),
    )
