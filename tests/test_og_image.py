from collector.models import Story
from collector.og_image import extract_og_image, fill_missing_images
from tests.factory import mk
from tests.helpers import FIXTURES, FakeResponse, FakeSession


def test_extract_og_image():
    html = (FIXTURES / "article_og.html").read_text(encoding="utf-8")
    assert extract_og_image(html, "https://example.org/a") == "https://img.example.org/og.jpg"


def test_extract_twitter_fallback():
    html = '<head><meta name="twitter:image" content="https://img.example.org/tw.jpg"></head>'
    assert extract_og_image(html, "https://example.org/a") == "https://img.example.org/tw.jpg"


def test_relative_url_made_absolute():
    html = '<meta property="og:image" content="/bilder/x.jpg">'
    assert extract_og_image(html, "https://example.org/artikel/1") == "https://example.org/bilder/x.jpg"


def test_rejects_javascript_url():
    html = '<meta property="og:image" content="javascript:alert(1)">'
    assert extract_og_image(html, "https://example.org/a") is None
    assert extract_og_image("<p>nichts</p>", "https://example.org/a") is None


def _story(lead, *others):
    items = [lead, *others]
    return Story(id="", items=items, lead=lead, region=None, categories=set(), latest=lead.published)


def test_fill_only_leads_and_respects_cache_and_limit():
    og = FakeResponse(200, b'<meta property="og:image" content="https://img.example.org/og.jpg">')
    session = FakeSession(default=og)
    s1 = _story(mk("l1", "a", "Eins"), mk("n1", "b", "Nebenmeldung"))
    s2 = _story(mk("l2", "a", "Zwei"))
    s3 = _story(mk("l3", "a", "Drei"))
    cache = {s2.lead.link: "https://img.example.org/cached.jpg"}
    fill_missing_images([s1, s2, s3], cache, session, max_fetches=1)
    assert len(session.calls) == 1
    assert s1.lead.image == "https://img.example.org/og.jpg"
    assert s1.items[1].image is None
    assert s2.lead.image == "https://img.example.org/cached.jpg"
    assert s3.lead.image is None


def test_fetch_error_cached_as_none():
    session = FakeSession(default=FakeResponse(500))
    s = _story(mk("l1", "a", "Eins"))
    cache = {}
    fill_missing_images([s], cache, session)
    assert s.lead.image is None
    assert cache[s.lead.link] is None


def test_malformed_og_url_does_not_crash_and_is_cached():
    html = '<meta property="og:image" content="http://[foo/x.jpg">'
    assert extract_og_image(html, "https://example.org/a") is None
    session = FakeSession(default=FakeResponse(200, html.encode()))
    s = _story(mk("l1", "a", "Eins"))
    cache = {}
    fill_missing_images([s], cache, session)
    assert cache[s.lead.link] is None
