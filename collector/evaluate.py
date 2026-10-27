"""Qualitätsmessung der Bündelung.

python -m collector.evaluate export --n 100   -> evaluation/testset.csv
python -m collector.evaluate score            -> Tabelle aus evaluation/labelled.csv
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from itertools import combinations
from pathlib import Path

from .cluster import cluster_items
from .output import write_json_atomic
from .state import item_from_dict, load_state

HEADER = ["id", "quelle", "zeit", "ueberschrift", "link", "geschichte"]
THRESHOLDS = [round(0.20 + 0.05 * i, 2) for i in range(9)]  # 0.20 … 0.60


def export_testset(state: dict, n: int, out: Path, seed: int = 0) -> None:
    items = [item_from_dict(d) for d in state["items"].values()]
    rng = random.Random(seed)
    chosen = rng.sample(items, min(n, len(items)))
    chosen.sort(key=lambda it: it.published)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(HEADER)
        for it in chosen:
            w.writerow([it.id, it.source_id, it.published.strftime("%Y-%m-%d %H:%M"), it.title, it.link, ""])
    # Die Meldungen selbst sichern: der Zwischenspeicher hält nur 48 Stunden,
    # das Beschriften kann länger dauern.
    write_json_atomic(out.with_name("testset_items.json"), {"items": {it.id: state["items"][it.id] for it in chosen}})


def read_labels(path: Path) -> dict[str, str]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = csv.DictReader(f, delimiter=";")
        return {r["id"].strip(): r["geschichte"].strip() for r in rows if (r.get("geschichte") or "").strip()}


def _pairs(mapping: dict[str, str], ids: list[str]) -> set[tuple[str, str]]:
    return {(a, b) for a, b in combinations(sorted(ids), 2) if mapping.get(a) == mapping.get(b)}


def pairwise_scores(labels: dict[str, str], predicted: dict[str, str]) -> tuple[float, float]:
    ids = list(labels)
    true_pairs = _pairs(labels, ids)
    pred_pairs = _pairs(predicted, ids)
    hit = len(true_pairs & pred_pairs)
    precision = hit / len(pred_pairs) if pred_pairs else 1.0
    recall = hit / len(true_pairs) if true_pairs else 1.0
    return precision, recall


def score_table(state: dict, labels: dict[str, str], thresholds: list[float] = THRESHOLDS) -> list[dict]:
    items = [item_from_dict(d) for d in state["items"].values() if d["id"] in labels]
    if not items:
        return []
    now = max(it.published for it in items)
    rows = []
    for t in thresholds:
        stories = cluster_items(items, t, now)
        predicted = {it.id: str(i) for i, st in enumerate(stories) for it in st.items}
        p, r = pairwise_scores({k: v for k, v in labels.items() if k in predicted}, predicted)
        rows.append({"threshold": t, "precision": p, "recall": r, "stories": len(stories)})
    return rows


def _markdown(rows: list[dict]) -> str:
    lines = ["| Schwellwert | Präzision | Vollständigkeit | Geschichten |", "| --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['threshold']:.2f} | {r['precision']:.0%} | {r['recall']:.0%} | {r['stories']} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["export", "score"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--state", default="site/data/state.json")
    args = ap.parse_args(argv)
    if args.command == "export":
        export_testset(load_state(Path(args.state)), args.n, Path("evaluation/testset.csv"))
        print("evaluation/testset.csv und evaluation/testset_items.json geschrieben")
        return 0
    labels_path = Path("evaluation/labelled.csv")
    if not labels_path.exists():
        print("evaluation/labelled.csv fehlt. Bitte die ausgefüllte Tabelle unter diesem Namen hochladen.")
        return 1
    labels = read_labels(labels_path)
    saved = load_state(Path("evaluation/testset_items.json"))
    rows = score_table(saved, labels)
    if not rows:
        print("Keine beschriftete Meldung passt zu evaluation/testset_items.json. Bitte neu exportieren.")
        return 1
    print(_markdown(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
