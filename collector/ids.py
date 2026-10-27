"""Stabile Geschichten-IDs über mehrere Läufe hinweg."""
from __future__ import annotations

import hashlib

from .models import Story

MIN_OVERLAP = 0.5


def _new_id(item_ids: list[str]) -> str:
    return "s" + hashlib.sha1("|".join(sorted(item_ids)).encode()).hexdigest()[:12]


def assign_story_ids(stories: list[Story], previous: dict[str, list[str]]) -> None:
    prev_sets = {sid: set(ids) for sid, ids in previous.items()}
    # Alle Kandidatenpaare nach Überlappung sortieren, beste zuerst vergeben.
    pairs = []
    for idx, st in enumerate(stories):
        cur = {it.id for it in st.items}
        for sid, old in prev_sets.items():
            inter = len(cur & old)
            if inter and inter / min(len(cur), len(old)) >= MIN_OVERLAP:
                pairs.append((inter, inter / min(len(cur), len(old)), idx, sid))
    pairs.sort(key=lambda p: (-p[0], -p[1], p[2], p[3]))
    used_old: set[str] = set()
    taken: dict[int, str] = {}
    for _, _, idx, sid in pairs:
        if idx in taken or sid in used_old:
            continue
        taken[idx] = sid
        used_old.add(sid)
    for idx, st in enumerate(stories):
        st.id = taken.get(idx) or _new_id([it.id for it in st.items])
