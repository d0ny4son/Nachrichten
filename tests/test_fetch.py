from datetime import datetime, timedelta, timezone

import pytest

from collector.fetch import FetchError, dedupe_items, fetch_feed, item_id, parse_feed
from collector.models import Feed, Source
from collector.text import keywords, stems
from tests.helpers import FIXTURES, FakeResponse, FakeSession

NOW = datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc)


def src(plus=None):
    return Source(id="ts", name="TS", media_type="oeffentlich-rechtlich", feeds=[], plus_patterns=plus or [])


def parse(name, feed=None, source=None, now=NOW, first_seen=None):
    data = (FIXTURES / name).read_bytes()
    return parse_feed(data, source or src(), feed or Feed(url="https://example.org/feed"), now, first_seen if first_seen is not None else {})


def test_parse_rss_basic():
    items = parse("rss_basic.xml", feed=Feed(url="u", region="inland", category="wirtschaft"))
    first = items[0]
    assert first.title == "Bundestag debattiert über den Haushaltsentwurf"
    assert first.link == "https://example.org/inland/haushalt-100.html?utm_source=rss"
    assert first.published == datetime(2026, 10, 27, 10, 8, tzinfo=timezone.utc)
    assert first.has_date is True
    assert first.regions == {"inland"}
    assert first.categories == {"wirtschaft"}
    teaser = "Dieser Satz ist ein Anrisstext. Der Bundestag streitet über Schulden."
    assert first.stems == sorted(stems(first.title + " " + teaser))
    assert first.keywords == keywords(first.title, teaser)
    assert not any("Anrisstext." in str(v) for v in vars(first).values())


def test_parse_atom():
    items = parse("atom_basic.xml")
    assert items[0].title == "EU-Gipfel berät über Energiepolitik"
    assert items[0].link == "https://example.org/eu-gipfel"


def test_image_from_media_content_and_enclosure():
    items = {i.title: i for i in parse("rss_media.xml")}
    assert items["Mit media content"].image == "https://img.example.org/content.jpg"
    assert items["Mit media thumbnail"].image == "https://img.example.org/thumb.jpg"
    assert items["Mit enclosure"].image == "https://img.example.org/enc.jpg"
    assert items["Plus-Artikel ohne Bild"].image is None


def test_image_from_description_img():
    items = {i.title: i for i in parse("rss_media.xml")}
    assert items["Mit Bild im Text"].image == "https://img.example.org/inline.jpg"


def test_plus_detection():
    items = {i.title: i for i in parse("rss_media.xml", source=src(plus=["/plus/"]))}
    assert items["Plus-Artikel ohne Bild"].plus is True
    assert items["Mit enclosure"].plus is False


def test_missing_date_uses_first_seen():
    items = {i.title: i for i in parse("rss_basic.xml")}
    undated = items["Meldung ohne Datum zur Bahn"]
    assert undated.published == NOW
    assert undated.has_date is False
    earlier = NOW - timedelta(minutes=40)
    later = parse("rss_basic.xml", now=NOW, first_seen={undated.id: earlier.isoformat()})
    again = {i.title: i for i in later}["Meldung ohne Datum zur Bahn"]
    assert again.published == earlier


def test_item_id_canonical():
    assert item_id("https://X.de/a?utm_source=x#top") == item_id("https://x.de/a")
    assert item_id("https://x.de/a?id=2") != item_id("https://x.de/a")
    assert len(item_id("https://x.de/a")) == 16


def test_dedupe_merges_regions_and_categories():
    a = parse("rss_basic.xml", feed=Feed(url="u1", region="inland"))[0]
    b = parse("rss_basic.xml", feed=Feed(url="u2", category="wirtschaft"))[0]
    b.image = "https://img.example.org/x.jpg"
    merged = dedupe_items([a, b])
    assert len(merged) == 1
    assert merged[0].regions == {"inland"}
    assert merged[0].categories == {"wirtschaft"}
    assert merged[0].image == "https://img.example.org/x.jpg"


def test_fetch_feed_sends_etag():
    cache = {"https://f": {"etag": '"abc"', "last_modified": "Tue, 27 Oct 2026 09:00:00 GMT"}}
    s = FakeSession({"https://f": FakeResponse(200, b"<rss/>", {"ETag": '"neu"'})})
    data = fetch_feed("https://f", cache, s)
    assert data == b"<rss/>"
    sent = s.calls[0][1]
    assert sent["If-None-Match"] == '"abc"'
    assert sent["If-Modified-Since"] == "Tue, 27 Oct 2026 09:00:00 GMT"
    assert "NachrichtenApp" in sent["User-Agent"]
    assert cache["https://f"]["etag"] == '"neu"'


def test_fetch_feed_304_returns_none():
    s = FakeSession({"https://f": FakeResponse(304)})
    assert fetch_feed("https://f", {}, s) is None


def test_fetch_feed_error_raises():
    with pytest.raises(FetchError):
        fetch_feed("https://f", {}, FakeSession({"https://f": FakeResponse(404)}))
    with pytest.raises(FetchError):
        fetch_feed("https://f", {}, FakeSession({}))


def test_bad_link_skips_only_that_entry():
    xml = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
    <item><title>Kaputt</title><link>http://[bad/x</link></item>
    <item><title>Gut</title><link>https://example.org/gut</link></item></channel></rss>"""
    items = parse_feed(xml, src(), Feed(url="u"), NOW, {})
    assert [i.title for i in items] == ["Gut"]


def test_stems_and_keywords_have_no_sentence_order():
    first = parse("rss_basic.xml")[0]
    assert first.stems == sorted(first.stems)
    assert first.keywords == sorted(first.keywords)


def test_broken_feed_raises_parse_error():
    from collector.fetch import FeedParseError
    with pytest.raises(FeedParseError):
        parse_feed(b"<html><body>Wartungsarbeiten</body></html>", src(), Feed(url="u"), NOW, {})
