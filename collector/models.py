"""Datenklassen des Sammlers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

MEDIA_TYPES = ("oeffentlich-rechtlich", "zeitung", "international")
REGIONS = ("inland", "ausland")
CATEGORIES = ("wissenschaft", "technik", "wirtschaft", "kultur", "sport")


@dataclass
class Feed:
    url: str
    region: str | None = None
    category: str | None = None


@dataclass
class Source:
    id: str
    name: str
    media_type: str
    feeds: list[Feed]
    plus_patterns: list[str] = field(default_factory=list)


@dataclass
class Config:
    sources: list[Source]
    threshold: float


@dataclass
class Item:
    """Eine Meldung. Der Anrisstext wird bewusst nicht gespeichert."""

    id: str
    source_id: str
    title: str
    link: str
    published: datetime
    image: str | None
    regions: set[str]
    categories: set[str]
    plus: bool
    has_date: bool
    stems: list[str]
    keywords: list[str]


@dataclass
class Story:
    id: str
    items: list[Item]
    lead: Item
    region: str | None
    categories: set[str]
    latest: datetime
    score: float = 0.0
