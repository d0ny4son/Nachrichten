"""Wichtigkeit einer Geschichte: Anzahl Quellen, abgewertet nach Alter."""
from __future__ import annotations

from datetime import datetime

from .models import Story


def score(story: Story, now: datetime, half_life_h: float = 6.0) -> float:
    sources = len({it.source_id for it in story.items})
    age_h = max(0.0, (now - story.latest).total_seconds() / 3600)
    return sources * 0.5 ** (age_h / half_life_h)
