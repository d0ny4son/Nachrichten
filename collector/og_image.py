"""Vorschaubild aus der Artikelseite (og:image), wenn der Feed keins liefert."""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from .fetch import USER_AGENT
from .models import Story

MAX_BYTES = 300_000
TIMEOUT = 10


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.og: str | None = None
        self.twitter: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        key = (a.get("property") or a.get("name") or "").lower()
        content = a.get("content", "").strip()
        if not content:
            return
        if key in ("og:image", "og:image:url", "og:image:secure_url") and self.og is None:
            self.og = content
        elif key in ("twitter:image", "twitter:image:src") and self.twitter is None:
            self.twitter = content


def extract_og_image(html: str, base_url: str) -> str | None:
    p = _MetaParser()
    try:
        p.feed(html)
    except Exception:  # kaputtes HTML: nehmen, was bis dahin gefunden wurde
        pass
    raw = p.og or p.twitter
    if not raw:
        return None
    try:
        url = urljoin(base_url, raw)
    except ValueError:
        return None
    return url if url.startswith(("http://", "https://")) else None


def _read_limited(resp) -> str:
    iter_content = getattr(resp, "iter_content", None)
    if iter_content is None:
        return resp.content[:MAX_BYTES].decode("utf-8", "replace")
    buf = b""
    for chunk in iter_content(chunk_size=16_384):
        buf += chunk
        if len(buf) >= MAX_BYTES:
            break
    return buf[:MAX_BYTES].decode("utf-8", "replace")


def fill_missing_images(stories: list[Story], cache: dict, session, max_fetches: int = 40) -> None:
    fetches = 0
    for st in stories:
        lead = st.lead
        if lead.image:
            continue
        if lead.link in cache:
            lead.image = cache[lead.link]
            continue
        if fetches >= max_fetches:
            continue
        fetches += 1
        image = None
        try:
            resp = session.get(lead.link, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, stream=True)
            if resp.status_code == 200:
                image = extract_og_image(_read_limited(resp), lead.link)
        except Exception:  # ein kaputtes Bild darf den Lauf nie stoppen
            image = None
        cache[lead.link] = image
        lead.image = image
