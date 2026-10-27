from datetime import timedelta

from collector.icons import extract_icon, resolve_icons
from tests.factory import NOW
from tests.helpers import FakeResponse, FakeSession

ZDF = """<html><head>
<link rel="apple-touch-icon" sizes="180x180" href="/_next/static/media/apple-touch-icon-180x180.png">
<link rel="icon" sizes="48x48" href="/_next/static/media/favicon.ico">
<link rel="icon" href="/_next/static/media/app-icon.svg">
</head></html>"""


def test_prefers_small_png_or_svg_then_touch_icon():
    sz = """<link rel="apple-touch-icon" sizes="180x180" href="/a.png"><link rel="icon" sizes="32x32" href="/f32.png"><link rel="icon" sizes="16x16" href="/f16.png">"""
    assert extract_icon(sz, "https://www.sueddeutsche.de/") == "https://www.sueddeutsche.de/f32.png"
    assert extract_icon(ZDF, "https://www.zdfheute.de/") == "https://www.zdfheute.de/_next/static/media/app-icon.svg"


def test_touch_icon_when_only_ico():
    html = '<link rel="shortcut icon" href="/x.ico"><link rel="apple-touch-icon" href="https://cdn.example.org/t.png">'
    assert extract_icon(html, "https://example.org/") == "https://cdn.example.org/t.png"


def test_no_icon_links():
    assert extract_icon("<html></html>", "https://example.org/") is None
    assert extract_icon('<link rel="icon" href="javascript:x">', "https://example.org/") is None


def test_resolve_uses_cache_limits_fetches_and_remembers_failures():
    session = FakeSession({"https://www.zdfheute.de/": FakeResponse(200, ZDF.encode())}, default=FakeResponse(403))
    cache = {"https://cached.example": {"url": "https://cached.example/i.png", "checked": NOW.isoformat()}}
    icons = resolve_icons(["https://www.zdfheute.de", "https://cached.example", "https://blocked.example", "https://later.example"], cache, session, NOW, max_fetches=2)
    assert icons["https://www.zdfheute.de"].endswith("app-icon.svg")
    assert icons["https://cached.example"] == "https://cached.example/i.png"
    assert "https://blocked.example" not in icons
    assert cache["https://blocked.example"]["url"] is None
    assert "https://later.example" not in cache  # Limit erreicht
    assert len(session.calls) == 2


def test_resolve_refreshes_after_a_week():
    old = (NOW - timedelta(days=8)).isoformat()
    cache = {"https://a.example": {"url": "https://a.example/old.png", "checked": old}}
    session = FakeSession(default=FakeResponse(200, b'<link rel="icon" sizes="32x32" href="/new.png">'))
    assert resolve_icons(["https://a.example"], cache, session, NOW)["https://a.example"] == "https://a.example/new.png"
