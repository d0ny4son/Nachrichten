import json
from datetime import timedelta

from collector.main import run
from tests.factory import NOW
from tests.helpers import FIXTURES, FakeResponse, FakeSession

CONFIG = """
clustering: {threshold: 0.35}
sources:
  - {id: a, name: A, media_type: oeffentlich-rechtlich, feeds: [{url: "https://a/feed", region: inland}]}
  - {id: b, name: B, media_type: zeitung, feeds: [{url: "https://b/feed"}]}
"""

BASIC = (FIXTURES / "rss_basic.xml").read_bytes()
ATOM = (FIXTURES / "atom_basic.xml").read_bytes()


def setup(tmp_path):
    cfg = tmp_path / "sources.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    data = tmp_path / "data"
    return cfg, data


def load(data, name):
    return json.loads((data / name).read_text(encoding="utf-8"))


def test_run_one_source_broken(tmp_path):
    cfg, data = setup(tmp_path)
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC)})
    assert run(cfg, data, NOW, session) == 0
    status = load(data, "status.json")
    assert status["sources"]["a"]["ok"] is True
    assert status["sources"]["a"]["items"] == 2
    assert status["sources"]["b"]["ok"] is False
    assert status["sources"]["b"]["errors"][0].startswith("https://b/feed: ")
    titles = {i["title"] for s in load(data, "stories.json")["stories"] for i in s["items"]}
    assert "Bundestag debattiert über den Haushaltsentwurf" in titles


def test_run_all_sources_broken_keeps_old_file(tmp_path):
    cfg, data = setup(tmp_path)
    data.mkdir()
    (data / "stories.json").write_bytes(b'{"alt": true}')
    assert run(cfg, data, NOW, FakeSession({})) == 1
    assert (data / "stories.json").read_bytes() == b'{"alt": true}'


def test_run_304_keeps_previous_items(tmp_path):
    cfg, data = setup(tmp_path)

    def etagged(body):
        def handler(headers):
            if headers.get("If-None-Match") == '"v1"':
                return FakeResponse(304)
            return FakeResponse(200, body, {"ETag": '"v1"'})
        return handler

    session = FakeSession({"https://a/feed": etagged(BASIC), "https://b/feed": etagged(ATOM)})
    assert run(cfg, data, NOW, session) == 0
    first = load(data, "stories.json")
    assert run(cfg, data, NOW + timedelta(minutes=20), session) == 0
    second = load(data, "stories.json")
    assert sorted(s["id"] for s in first["stories"]) == sorted(s["id"] for s in second["stories"])
    assert len(second["stories"]) == 3


def test_run_undated_item_keeps_first_seen_time(tmp_path):
    cfg, data = setup(tmp_path)
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC), "https://b/feed": FakeResponse(200, ATOM)})
    run(cfg, data, NOW, session)
    run(cfg, data, NOW + timedelta(minutes=20), session)
    items = {i["title"]: i for s in load(data, "stories.json")["stories"] for i in s["items"]}
    assert items["Meldung ohne Datum zur Bahn"]["published"] == "2026-10-27T11:00:00Z"


def test_no_teaser_in_any_written_file(tmp_path):
    cfg, data = setup(tmp_path)
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC), "https://b/feed": FakeResponse(200, ATOM)})
    run(cfg, data, NOW, session)
    for name in ("stories.json", "status.json", "state.json"):
        text = (data / name).read_text(encoding="utf-8")
        assert "Dieser Satz ist ein Anrisstext." not in text, name
        assert "teaser" not in text, name


def test_garbage_feed_is_reported_and_not_cached(tmp_path):
    cfg, data = setup(tmp_path)
    html = FakeResponse(200, b"<html><body>Wartung</body></html>", {"ETag": '"x"'})
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC), "https://b/feed": html})
    assert run(cfg, data, NOW, session) == 0
    status = load(data, "status.json")
    assert status["sources"]["b"]["ok"] is False
    assert "nicht lesbar" in status["sources"]["b"]["errors"][0]
    run(cfg, data, NOW + timedelta(minutes=20), session)
    sent = [h for url, h in session.calls if url == "https://b/feed"][-1]
    assert "If-None-Match" not in sent


def test_undated_item_does_not_return_as_new_after_window(tmp_path):
    cfg, data = setup(tmp_path)
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC), "https://b/feed": FakeResponse(200, ATOM)})
    run(cfg, data, NOW, session)
    run(cfg, data, NOW + timedelta(hours=49), session)
    run(cfg, data, NOW + timedelta(hours=50), session)
    titles = {i["title"] for s in load(data, "stories.json")["stories"] for i in s["items"]}
    assert "Meldung ohne Datum zur Bahn" not in titles


def test_state_stems_are_sorted(tmp_path):
    cfg, data = setup(tmp_path)
    session = FakeSession({"https://a/feed": FakeResponse(200, BASIC), "https://b/feed": FakeResponse(200, ATOM)})
    run(cfg, data, NOW, session)
    for it in load(data, "state.json")["items"].values():
        assert it["stems"] == sorted(it["stems"])
