"""Erzeugt die veröffentlichte Datei stories.json (Schema v1)."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Config, Item, Story


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item(it: Item, is_lead: bool) -> dict:
    return {
        "id": it.id,
        "source": it.source_id,
        "title": it.title,
        "link": it.link,
        "published": iso(it.published),
        "image": it.image if is_lead else None,
        "plus": it.plus,
        "keywords": it.keywords,
    }


def build_output(stories: list[Story], config: Config, generated_at: datetime) -> dict:
    ordered = sorted(stories, key=lambda s: (-s.score, s.id))
    return {
        "version": 1,
        "generated_at": iso(generated_at),
        "sources": {s.id: {"name": s.name, "media_type": s.media_type} for s in config.sources},
        "stories": [
            {
                "id": st.id,
                "score": round(st.score, 4),
                "region": st.region,
                "categories": sorted(st.categories),
                "latest": iso(st.latest),
                "lead": st.lead.id,
                "items": [_item(it, it.id == st.lead.id) for it in sorted(st.items, key=lambda i: i.published, reverse=True)],
            }
            for st in ordered
        ],
    }


def write_json_atomic(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
