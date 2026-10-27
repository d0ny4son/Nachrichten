import csv

import pytest

from collector.evaluate import export_testset, pairwise_scores, read_labels, score_table
from collector.state import item_to_dict
from tests.factory import BUDGET, OTHER, mk


def state_with(items):
    return {"items": {it.id: item_to_dict(it) for it in items}}


def test_pairwise_perfect():
    labels = {"a": "1", "b": "1", "c": "2"}
    assert pairwise_scores(labels, {"a": "x", "b": "x", "c": "y"}) == (1.0, 1.0)


def test_pairwise_overmerge_lowers_precision():
    labels = {"a": "1", "b": "1", "c": "2", "d": "2"}
    p, r = pairwise_scores(labels, {k: "x" for k in labels})
    assert p == pytest.approx(2 / 6)
    assert r == 1.0


def test_pairwise_split_lowers_recall():
    labels = {"a": "1", "b": "1", "c": "1"}
    p, r = pairwise_scores(labels, {"a": "x", "b": "x", "c": "y"})
    assert p == 1.0
    assert r == pytest.approx(1 / 3)


def test_pairwise_no_predicted_pairs_precision_one():
    p, r = pairwise_scores({"a": "1", "b": "1"}, {"a": "x", "b": "y"})
    assert (p, r) == (1.0, 0.0)


def test_export_csv_columns_and_bom(tmp_path):
    items = [mk(*row) for row in BUDGET + OTHER]
    out = tmp_path / "testset.csv"
    export_testset(state_with(items), 4, out)
    raw = out.read_bytes()
    assert raw.startswith("﻿".encode("utf-8"))
    rows = list(csv.reader(out.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    assert rows[0] == ["id", "quelle", "zeit", "ueberschrift", "link", "geschichte"]
    assert len(rows) == 5
    assert all(r[5] == "" for r in rows[1:])


def test_export_keeps_items_for_later_scoring(tmp_path):
    import json
    items = [mk(*row) for row in BUDGET + OTHER]
    out = tmp_path / "testset.csv"
    export_testset(state_with(items), 3, out)
    saved = json.loads((tmp_path / "testset_items.json").read_text(encoding="utf-8"))
    ids = [r.split(";")[0] for r in out.read_text(encoding="utf-8-sig").splitlines()[1:]]
    assert sorted(saved["items"]) == sorted(ids)
    assert "teaser" not in json.dumps(saved)


def test_score_reads_labels_ignoring_empty_rows(tmp_path):
    p = tmp_path / "labelled.csv"
    p.write_text("﻿id;quelle;zeit;ueberschrift;link;geschichte\nb1;x;;t;l;haushalt\nb2;x;;t;l;haushalt\no1;x;;t;l;\n", encoding="utf-8")
    assert read_labels(p) == {"b1": "haushalt", "b2": "haushalt"}


def test_score_table_rows():
    items = [mk(*row) for row in BUDGET + OTHER]
    labels = {"b1": "h", "b2": "h", "b3": "h", "b4": "h", "o1": "akku", "o2": "bahn"}
    rows = score_table(state_with(items), labels, [0.2, 0.5])
    assert [r["threshold"] for r in rows] == [0.2, 0.5]
    assert rows[0]["precision"] == 1.0 and rows[0]["recall"] == 1.0 and rows[0]["stories"] == 3
    assert rows[1]["recall"] < 1.0
