"""Laden und Prüfen von config/sources.yaml.

Alle Fehlermeldungen sind deutsch, damit sie in der GitHub-Prüfung
ohne Programmierkenntnisse verständlich sind.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import CATEGORIES, MEDIA_TYPES, REGIONS, Config, Feed, Source

DEFAULT_THRESHOLD = 0.35


class ConfigError(Exception):
    """Fehler in der Quellen-Konfiguration."""


def _fail(msg: str) -> None:
    raise ConfigError(msg)


def _optional_choice(value, allowed, where: str, key: str):
    if value is None:
        return None
    if value not in allowed:
        _fail(f"{where}: {key} „{value}“ ist unbekannt. Erlaubt: {', '.join(allowed)} (oder weglassen).")
    return value


def load_config(path: str | Path) -> Config:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = f" in Zeile {mark.line + 1}" if mark is not None else ""
        _fail(f"Die Datei {path.name} ist nicht korrekt formatiert{line}. Häufige Ursache: falsche Einrückung oder fehlendes Anführungszeichen.")
    except OSError as e:
        _fail(f"Die Datei {path} konnte nicht gelesen werden: {e}")

    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        _fail(f"{path.name}: Es fehlt die Liste „sources:“.")

    threshold = DEFAULT_THRESHOLD
    clustering = raw.get("clustering") or {}
    if "threshold" in clustering:
        threshold = clustering["threshold"]
        if not isinstance(threshold, (int, float)) or not 0 < threshold < 1:
            _fail(f"clustering.threshold muss eine Zahl zwischen 0 und 1 sein, nicht „{threshold}“.")

    sources: list[Source] = []
    seen: set[str] = set()
    for i, s in enumerate(raw["sources"], start=1):
        if not isinstance(s, dict):
            _fail(f"Quelle Nr. {i} ist kein gültiger Eintrag.")
        sid = s.get("id")
        if not sid or not isinstance(sid, str):
            _fail(f"Quelle Nr. {i}: Es fehlt die „id“.")
        where = f"Quelle „{sid}“"
        if sid in seen:
            _fail(f"{where}: Die id kommt doppelt vor.")
        seen.add(sid)
        name = s.get("name")
        if not name:
            _fail(f"{where}: Es fehlt der „name“.")
        media_type = s.get("media_type")
        if media_type not in MEDIA_TYPES:
            _fail(f"{where}: media_type „{media_type}“ ist unbekannt. Erlaubt: {', '.join(MEDIA_TYPES)}.")

        patterns = s.get("plus_patterns") or []
        for pat in patterns:
            try:
                re.compile(pat)
            except (re.error, TypeError):
                _fail(f"{where}: Das plus_pattern „{pat}“ ist kein gültiges Suchmuster.")

        feeds_raw = s.get("feeds") or []
        if not feeds_raw:
            _fail(f"{where}: Es ist kein Feed eingetragen.")
        feeds: list[Feed] = []
        for f in feeds_raw:
            if not isinstance(f, dict) or not str(f.get("url", "")).startswith(("http://", "https://")):
                _fail(f"{where}: Jeder Feed braucht eine „url“, die mit https:// beginnt.")
            feeds.append(
                Feed(
                    url=f["url"],
                    region=_optional_choice(f.get("region"), REGIONS, where, "region"),
                    category=_optional_choice(f.get("category"), CATEGORIES, where, "category"),
                )
            )
        sources.append(Source(id=sid, name=str(name), media_type=media_type, feeds=feeds, plus_patterns=list(patterns)))

    topics_raw = raw.get("themen") or []
    if not isinstance(topics_raw, list):
        _fail("„themen:“ muss eine Liste sein, z. B. themen: [Wasserstoff, Elektrolyse]")
    topics: list[str] = []
    for t in topics_raw:
        t = str(t).strip() if t is not None else ""
        if not t:
            _fail("„themen:“ enthält einen leeren Eintrag.")
        if t not in topics:
            topics.append(t)
    if len(topics) > 20:
        _fail("Höchstens 20 Themen in „themen:“ eintragen.")

    return Config(sources=sources, threshold=float(threshold), topics=topics)
