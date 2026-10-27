from datetime import timedelta
import json

import pytest

from collector.config import ConfigError, load_config
from collector.fetch import parse_topic_feed, topic_feed_url
from collector.main import run
from collector.rank import score
from collector.models import Story
from tests.factory import NOW, mk
from tests.helpers import FIXTURES, FakeResponse, FakeSession

GNEWS = (FIXTURES / "gnews.xml").read_bytes()
BASIC = (FIXTURES / "rss_basic.xml").read_bytes()


def test_config_reads_topics(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("themen: [Wasserstoff, ' Elektrolyse ']\nsources:\n  - {id: a, name: A, media_type: zeitung, feeds: [{url: 'https://a'}]}\n", encoding="utf-8")
    assert load_config(p).topics == ["Wasserstoff", "Elektrolyse"]


def test_config_topics_optional_and_validated(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("sources:\n  - {id: a, name: A, media_type: zeitung, feeds: [{url: 'https://a'}]}\n", encoding="utf-8")
    assert load_config(p).topics == []
    p.write_text("themen: ['']\nsources:\n  - {id: a, name: A, media_type: zeitung, feeds: [{url: 'https://a'}]}\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_topic_feed_url():
    u = topic_feed_url("Grüner Wasserstoff")
    assert u.startswith("https://news.google.com/rss/search?q=")
    assert "Gr%C3%BCner+Wasserstoff+when%3A2d" in u
    assert u.endswith("&hl=de&gl=DE&ceid=DE:de")


def test_parse_topic_feed_uses_real_publisher():
    items = parse_topic_feed(GNEWS, "Wasserstoff", NOW, {})
    first = items[0]
    assert first.title == "Neues Wasserstoffnetz: Erste Leitungen in Betrieb"
    assert first.publisher == "Handelsblatt"
    assert first.site == "https://www.handelsblatt.com"
    assert first.topic == "Wasserstoff"
    assert first.source_id == "themen"
    assert "handelsblatt" not in first.keywords  # Google-Beschreibung ist kein Anrisstext


def test_score_counts_publishers_as_sources():
    a = mk("a", "themen", "Wasserstoff A", hours_ago=0)
    b = mk("b", "themen", "Wasserstoff B", hours_ago=0)
    a.publisher, b.publisher = "Handelsblatt", "FAZ"
    st = Story(id="", items=[a, b], lead=a, region=None, categories=set(), latest=a.published)
    assert score(st, NOW) == pytest.approx(2.0)


CONFIG = """
themen: [Wasserstoff]
sources:
  - {id: a, name: A, media_type: oeffentlich-rechtlich, feeds: [{url: "https://a/feed"}]}
"""


def test_run_adds_topic_stories_marked_topic_only_and_drops_title_duplicates(tmp_path):
    cfg = tmp_path / "s.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    data = tmp_path / "data"
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC), topic_feed_url("Wasserstoff"): FakeResponse(200, GNEWS)})
    assert run(cfg, data, NOW, session) == 0
    out = json.loads((data / "stories.json").read_text(encoding="utf-8"))
    items = [i for s in out["stories"] for i in s["items"]]
    titles = [i["title"] for i in items]
    assert titles.count("Bundestag debattiert über den Haushaltsentwurf") == 1  # Google-Dublette entfernt
    topic = next(s for s in out["stories"] if any(i["title"].startswith("Neues Wasserstoffnetz") for i in s["items"]))
    assert topic["topic_only"] is True
    it = topic["items"][0]
    assert it["publisher"] == "Handelsblatt" and it["site"] == "https://www.handelsblatt.com"
    normal = next(s for s in out["stories"] if any(i["title"].startswith("Bundestag") for i in s["items"]))
    assert normal["topic_only"] is False
    status = json.loads((data / "status.json").read_text(encoding="utf-8"))
    assert status["sources"]["themen"]["ok"] is True


def test_output_lists_topics(tmp_path):
    cfg = tmp_path / "s.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    data = tmp_path / "data"
    run(cfg, data, NOW, FakeSession({"https://a/feed": FakeResponse(200, BASIC), topic_feed_url("Wasserstoff"): FakeResponse(200, GNEWS)}))
    assert json.loads((data / "stories.json").read_text(encoding="utf-8"))["topics"] == ["Wasserstoff"]
