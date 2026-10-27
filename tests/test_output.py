import json

from collector.models import Config, Feed, Source, Story
from collector.output import build_output, write_json_atomic
from tests.factory import NOW, mk

CFG = Config(
    sources=[
        Source(id="a", name="Quelle A", media_type="zeitung", feeds=[Feed(url="https://a")]),
        Source(id="b", name="Quelle B", media_type="international", feeds=[Feed(url="https://b")]),
    ],
    threshold=0.35,
)


def _story(sid, score, items, lead=None):
    return Story(id=sid, items=items, lead=lead or items[0], region="inland", categories={"wirtschaft"},
                 latest=max(i.published for i in items), score=score)


def test_output_schema_and_sorting():
    old = mk("i1", "a", "Alt", hours_ago=3, image="https://img/1.jpg")
    new = mk("i2", "b", "Neu", hours_ago=1, image="https://img/2.jpg", plus=True)
    s_low = _story("s1", 1.0, [mk("i3", "a", "Einzeln")])
    s_high = _story("s2", 3.0, [old, new], lead=old)
    out = build_output([s_low, s_high], CFG, NOW)
    assert out["version"] == 1
    assert out["generated_at"] == "2026-10-27T11:00:00Z"
    assert out["sources"]["a"] == {"name": "Quelle A", "media_type": "zeitung"}
    assert [s["id"] for s in out["stories"]] == ["s2", "s1"]
    top = out["stories"][0]
    assert set(top) == {"id", "score", "region", "categories", "latest", "lead", "topic_only", "items"}
    assert top["topic_only"] is False
    assert top["lead"] == "i1"
    assert top["categories"] == ["wirtschaft"]
    assert [i["id"] for i in top["items"]] == ["i2", "i1"]
    by_id = {i["id"]: i for i in top["items"]}
    assert by_id["i1"]["image"] == "https://img/1.jpg"
    assert by_id["i2"]["image"] is None
    assert by_id["i2"]["plus"] is True
    assert set(by_id["i1"]) == {"id", "source", "title", "link", "published", "image", "plus", "keywords"}
    assert by_id["i1"]["published"] == "2026-10-27T08:00:00Z"


def test_write_json_atomic(tmp_path):
    p = tmp_path / "x" / "d.json"
    write_json_atomic(p, {"ä": 1})
    assert json.loads(p.read_text(encoding="utf-8")) == {"ä": 1}
    assert [f.name for f in p.parent.iterdir()] == ["d.json"]
