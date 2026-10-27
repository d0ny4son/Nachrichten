"""Symbol jeder Website aus ihrem Seitenkopf lesen (<link rel="icon">).

Viele Seiten haben kein /favicon.ico (z. B. ZDF heute: 404) oder legen es auf
einem anderen Server ab. Das Ergebnis wird pro Website eine Woche gemerkt.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin

from .fetch import USER_AGENT
from .og_image import _read_limited

REFRESH = timedelta(days=7)
TIMEOUT = 10


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            a = {k.lower(): (v or "") for k, v in attrs}
            if a.get("href"):
                self.links.append(a)


def _size(sizes: str) -> int:
    nums = [int(n) for n in re.findall(r"(\d+)x\d+", sizes or "")]
    return max(nums) if nums else 0


def extract_icon(html: str, base_url: str) -> str | None:
    p = _LinkParser()
    try:
        p.feed(html)
    except Exception:
        pass
    raster, svg, touch, ico = [], [], [], []
    for link in p.links:
        rels = link.get("rel", "").lower().split()
        try:
            url = urljoin(base_url, link["href"].strip())
        except ValueError:
            continue
        if not url.startswith(("http://", "https://")):
            continue
        path = url.split("?")[0].lower()
        if "apple-touch-icon" in rels:
            touch.append(url)
        elif "icon" in rels:
            if path.endswith(".svg") or "svg" in link.get("type", ""):
                svg.append(url)
            elif path.endswith(".ico"):
                ico.append(url)
            else:
                raster.append((_size(link.get("sizes", "")), url))
    # 1. kleines Rasterbild ab 32 px, 2. SVG, 3. Touch-Icon, 4. .ico
    good = sorted((s, u) for s, u in raster if 32 <= s <= 196)
    if good:
        return good[0][1]
    for group in (svg, touch, ico, [u for _, u in raster]):
        if group:
            return group[0]
    return None


def resolve_icons(origins, cache: dict, session, now: datetime, max_fetches: int = 15) -> dict[str, str]:
    fetches = 0
    for origin in dict.fromkeys(origins):  # Reihenfolge = Wichtigkeit (häufigste Seiten zuerst)
        entry = cache.get(origin)
        if entry and now - datetime.fromisoformat(entry["checked"]) < REFRESH:
            continue
        if fetches >= max_fetches:
            continue
        fetches += 1
        url = None
        try:
            resp = session.get(origin + "/", headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, stream=True)
            if resp.status_code == 200:
                url = extract_icon(_read_limited(resp), origin + "/")
        except Exception:  # ein Symbol darf den Lauf nie stoppen
            url = None
        cache[origin] = {"url": url, "checked": now.isoformat()}
    return {o: cache[o]["url"] for o in set(origins) if o in cache and cache[o]["url"]}
