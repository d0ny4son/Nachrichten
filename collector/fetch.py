"""Feeds abrufen und in Items umwandeln."""
from __future__ import annotations

import calendar
import hashlib
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

import feedparser
import requests

from .models import Feed, Item, Source
from .text import keywords, stems

_repo = os.environ.get("GITHUB_REPOSITORY", "<user>/<repo>")
USER_AGENT = f"NachrichtenApp/1.0 (privat; +https://github.com/{_repo})"
TIMEOUT = 20


class FetchError(Exception):
    """Ein Feed konnte nicht geladen werden."""


class FeedParseError(Exception):
    """Die Antwort ist kein lesbarer Feed (z. B. eine Wartungsseite)."""


def item_id(link: str) -> str:
    parts = urlsplit(link.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), ""))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]


def fetch_feed(url: str, http_cache: dict, session) -> bytes | None:
    headers = {"User-Agent": USER_AGENT}
    cached = http_cache.get(url) or {}
    if cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    if cached.get("last_modified"):
        headers["If-Modified-Since"] = cached["last_modified"]
    try:
        resp = session.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise FetchError(f"nicht erreichbar ({type(e).__name__})") from e
    if resp.status_code == 304:
        return None
    if resp.status_code != 200:
        raise FetchError(f"HTTP {resp.status_code}")
    entry = {}
    if resp.headers.get("ETag"):
        entry["etag"] = resp.headers["ETag"]
    if resp.headers.get("Last-Modified"):
        entry["last_modified"] = resp.headers["Last-Modified"]
    http_cache[url] = entry
    return resp.content


class _TextAndImg(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.img: str | None = None

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == "img" and self.img is None:
            src = dict(attrs).get("src")
            if src and src.startswith(("http://", "https://")):
                self.img = src


def _strip_html(html: str) -> tuple[str, str | None]:
    p = _TextAndImg()
    p.feed(html or "")
    text = re.sub(r"\s+", " ", "".join(p.parts)).strip()
    return text, p.img


def _is_image_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("http://", "https://"))


def _image(entry, desc_img: str | None) -> str | None:
    for m in entry.get("media_content", []) or []:
        medium = m.get("medium", "")
        typ = m.get("type", "")
        if _is_image_url(m.get("url")) and (medium == "image" or typ.startswith("image/") or not (medium or typ)):
            return m["url"]
    for m in entry.get("media_thumbnail", []) or []:
        if _is_image_url(m.get("url")):
            return m["url"]
    for link in entry.get("links", []) or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image/") and _is_image_url(link.get("href")):
            return link["href"]
    return desc_img


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return None


def parse_feed(data: bytes, source: Source, feed: Feed, now: datetime, first_seen: dict[str, str]) -> list[Item]:
    parsed = feedparser.parse(data)
    if not parsed.entries and (parsed.bozo or not parsed.get("version")):
        reason = parsed.get("bozo_exception")
        raise FeedParseError(type(reason).__name__ if reason else "kein RSS/Atom")
    plus_res = [re.compile(p) for p in source.plus_patterns]
    items: list[Item] = []
    for e in parsed.entries:
        link = (e.get("link") or "").strip()
        title = re.sub(r"\s+", " ", (e.get("title") or "")).strip()
        if not link.startswith(("http://", "https://")) or not title:
            continue
        try:
            iid = item_id(link)
        except ValueError:  # kaputte Adresse: nur diesen Eintrag überspringen
            continue
        raw = e.get("summary") or ""
        if not raw and e.get("content"):
            raw = e["content"][0].get("value", "")
        teaser, desc_img = _strip_html(raw)
        pub = _published(e)
        has_date = pub is not None
        if pub is None:
            seen = first_seen.get(iid)
            pub = datetime.fromisoformat(seen) if seen else now
        items.append(
            Item(
                id=iid,
                source_id=source.id,
                title=title,
                link=link,
                published=pub,
                image=_image(e, desc_img),
                regions={feed.region} if feed.region else set(),
                categories={feed.category} if feed.category else set(),
                plus=any(r.search(link) for r in plus_res),
                has_date=has_date,
                stems=sorted(stems(f"{title} {teaser}")),  # sortiert: kein Satzbau
                keywords=keywords(title, teaser),
            )
        )
    return items


def dedupe_items(items: list[Item]) -> list[Item]:
    merged: dict[str, Item] = {}
    for it in items:
        cur = merged.get(it.id)
        if cur is None:
            merged[it.id] = it
            continue
        cur.regions |= it.regions
        cur.categories |= it.categories
        cur.image = cur.image or it.image
        cur.plus = cur.plus or it.plus
        if not cur.has_date and it.has_date:
            cur.published, cur.has_date = it.published, True
    return list(merged.values())


TOPIC_SOURCE_ID = "themen"


def topic_feed_url(term: str) -> str:
    """Google-News-Suche nach einem Thema, nur Meldungen der letzten 2 Tage, deutschsprachig."""
    return f"https://news.google.com/rss/search?q={quote_plus(term + ' when:2d')}&hl=de&gl=DE&ceid=DE:de"


def parse_topic_feed(data: bytes, term: str, now: datetime, first_seen: dict[str, str]) -> list[Item]:
    parsed = feedparser.parse(data)
    if not parsed.entries and (parsed.bozo or not parsed.get("version")):
        reason = parsed.get("bozo_exception")
        raise FeedParseError(type(reason).__name__ if reason else "kein RSS/Atom")
    items: list[Item] = []
    for e in parsed.entries:
        link = (e.get("link") or "").strip()
        title = re.sub(r"\s+", " ", (e.get("title") or "")).strip()
        src = e.get("source") or {}
        publisher = (src.get("title") or "").strip() or None
        site = (src.get("href") or "").strip() or None
        if site and not site.startswith(("http://", "https://")):
            site = None
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3].strip()
        elif " - " in title:
            title = title.rsplit(" - ", 1)[0].strip()
        if not link.startswith(("http://", "https://")) or not title:
            continue
        try:
            iid = item_id(link)
        except ValueError:
            continue
        pub = _published(e)
        has_date = pub is not None
        if pub is None:
            seen = first_seen.get(iid)
            pub = datetime.fromisoformat(seen) if seen else now
        items.append(
            Item(
                id=iid,
                source_id=TOPIC_SOURCE_ID,
                title=title,
                link=link,
                published=pub,
                image=None,
                regions=set(),
                categories=set(),
                plus=False,
                has_date=has_date,
                stems=sorted(stems(title)),  # Google liefert keinen echten Anrisstext
                keywords=keywords(title, ""),
                publisher=publisher,
                site=site,
                topic=term,
            )
        )
    return items
