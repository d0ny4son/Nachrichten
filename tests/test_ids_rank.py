from datetime import timedelta

import pytest

from collector.ids import assign_story_ids
from collector.models import Story
from collector.rank import score
from tests.factory import NOW, mk


def story(*specs, hours_ago=1.0):
    items = [mk(iid, src, f"Titel {iid}", hours_ago=hours_ago) for iid, src in specs]
    return Story(id="", items=items, lead=items[0], region=None, categories=set(), latest=max(i.published for i in items))


def test_id_kept_when_story_grows():
    s = story(("a", "x"), ("b", "y"), ("c", "z"))
    assign_story_ids([s], {"sold": ["a", "b"]})
    assert s.id == "sold"


def test_id_new_when_no_overlap():
    s = story(("c", "x"))
    assign_story_ids([s], {"sold": ["a", "b"]})
    assert s.id != "sold"
    assert s.id.startswith("s") and len(s.id) == 13


def test_new_id_is_deterministic():
    s1, s2 = story(("c", "x"), ("d", "y")), story(("d", "y"), ("c", "x"))
    assign_story_ids([s1], {})
    assign_story_ids([s2], {})
    assert s1.id == s2.id


def test_old_id_not_reused_twice():
    s1 = story(("a", "x"), ("b", "y"))
    s2 = story(("c", "x"), ("d", "y"))
    assign_story_ids([s1, s2], {"sold": ["a", "b", "c", "d"]})
    assert [s1.id, s2.id].count("sold") == 1


def test_score_counts_distinct_sources():
    s = story(("a", "x"), ("b", "x"), ("c", "y"), hours_ago=0)
    assert score(s, NOW) == pytest.approx(2.0)


def test_score_decays():
    fresh = story(("a", "x"), ("b", "y"), hours_ago=0)
    old = story(("c", "x"), ("d", "y"), hours_ago=6)
    assert score(old, NOW) == pytest.approx(score(fresh, NOW) / 2)
