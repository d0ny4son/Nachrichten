"""Ein kompletter Lauf des Sammlers: python -m collector.main"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .cluster import WINDOW, cluster_items
from .config import load_config
from .fetch import TOPIC_SOURCE_ID, FetchError, dedupe_items, fetch_feed, parse_feed, parse_topic_feed, topic_feed_url
from .ids import assign_story_ids
from .og_image import fill_missing_images
from .output import build_output, iso, write_json_atomic
from .rank import score
from .state import item_from_dict, item_to_dict, load_state, save_state

FIRST_SEEN_KEEP = timedelta(days=14)


def run(config_path: Path, data_dir: Path, now: datetime, session) -> int:
    config = load_config(config_path)
    data_dir = Path(data_dir)
    state = load_state(data_dir / "state.json")

    stored = [item_from_dict(d) for d in state["items"].values()]
    fresh = []
    status: dict[str, dict] = {}
    feeds_total = feeds_failed = 0

    for source in config.sources:
        errors: list[str] = []
        for feed in source.feeds:
            feeds_total += 1
            old_cache = state["http_cache"].get(feed.url)
            try:
                data = fetch_feed(feed.url, state["http_cache"], session)
            except FetchError as e:
                feeds_failed += 1
                errors.append(f"{feed.url}: {e}")
                continue
            if data is None:  # 304: unverändert, gespeicherte Items bleiben
                continue
            try:
                parsed = parse_feed(data, source, feed, now, state["first_seen"])
            except Exception as e:  # kaputtes XML einer Quelle darf den Lauf nicht stoppen
                errors.append(f"{feed.url}: nicht lesbar ({e})")
                # Validator nicht behalten, sonst käme beim nächsten Mal nur „304“.
                if old_cache is None:
                    state["http_cache"].pop(feed.url, None)
                else:
                    state["http_cache"][feed.url] = old_cache
                continue
            for it in parsed:
                if not it.has_date and it.id not in state["first_seen"]:
                    state["first_seen"][it.id] = iso(now)
            fresh.extend(parsed)
        status[source.id] = {"ok": not errors, "errors": errors}

    # Themen-Suche (Google News) – zählt nicht zu „alle Quellen ausgefallen“
    if config.topics:
        errors = []
        for term in config.topics:
            url = topic_feed_url(term)
            old_cache = state["http_cache"].get(url)
            try:
                data = fetch_feed(url, state["http_cache"], session)
                if data is None:
                    continue
                parsed = parse_topic_feed(data, term, now, state["first_seen"])
            except Exception as e:
                errors.append(f"Thema „{term}“: {e}")
                if old_cache is None:
                    state["http_cache"].pop(url, None)
                else:
                    state["http_cache"][url] = old_cache
                continue
            for it in parsed:
                if not it.has_date and it.id not in state["first_seen"]:
                    state["first_seen"][it.id] = iso(now)
            fresh.extend(parsed)
        status[TOPIC_SOURCE_ID] = {"ok": not errors, "errors": errors}

    if feeds_total and feeds_failed == feeds_total:
        _write_status(data_dir, now, status, [])
        save_state(data_dir / "state.json", state)
        return 1

    known_sources = {s.id for s in config.sources}
    topics = set(config.topics)
    items = [
        it
        for it in dedupe_items(fresh + stored)
        if (it.source_id in known_sources or (it.source_id == TOPIC_SOURCE_ID and it.topic in topics))
        and now - it.published <= WINDOW
    ]
    # Themen-Treffer, die wir schon direkt von einem der Medien haben, nicht doppelt zeigen
    direct_titles = {_norm(it.title) for it in items if not it.topic}
    items = [it for it in items if not it.topic or _norm(it.title) not in direct_titles]

    stories = cluster_items(items, config.threshold, now)
    assign_story_ids(stories, state["stories"])
    for st in stories:
        st.score = score(st, now)
    fill_missing_images(stories, state["og_cache"], session)

    write_json_atomic(data_dir / "stories.json", build_output(stories, config, now))
    _write_status(data_dir, now, status, items)

    state["items"] = {it.id: item_to_dict(it) for it in items}
    state["stories"] = {st.id: [it.id for it in st.items] for st in stories}
    # Länger als das Fenster merken, sonst kämen undatierte Meldungen nach 48 h als „neu“ zurück.
    state["first_seen"] = {
        k: v for k, v in state["first_seen"].items() if now - datetime.fromisoformat(v.replace("Z", "+00:00")) <= FIRST_SEEN_KEEP
    }
    links = {it.link for it in items}
    state["og_cache"] = {k: v for k, v in state["og_cache"].items() if k in links}
    save_state(data_dir / "state.json", state)
    return 0


def _norm(title: str) -> str:
    return " ".join(title.lower().split())


def _write_status(data_dir: Path, now: datetime, status: dict, items) -> None:
    for sid, entry in status.items():
        mine = [it for it in items if it.source_id == sid]
        entry["items"] = len(mine)
        entry["with_image"] = sum(1 for it in mine if it.image)
        entry["plus"] = sum(1 for it in mine if it.plus)
    write_json_atomic(data_dir / "status.json", {"generated_at": iso(now), "sources": status})


def main() -> int:
    return run(Path("config/sources.yaml"), Path("site/data"), datetime.now(timezone.utc), requests.Session())


if __name__ == "__main__":
    sys.exit(main())
