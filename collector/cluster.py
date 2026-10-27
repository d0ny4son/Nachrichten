"""Bündelung von Meldungen zu Geschichten (eine Geschichte = ein Ereignis)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Item, Story

WINDOW = timedelta(hours=48)
MAX_GAP = timedelta(hours=24)
LEAD_TOLERANCE = 0.05


def _identity(x):
    return x


def similarity_matrix(items: list[Item]) -> np.ndarray:
    n = len(items)
    if n == 0:
        return np.zeros((0, 0))
    docs = [it.stems or [it.id] for it in items]
    tfidf = TfidfVectorizer(analyzer=_identity).fit_transform(docs)
    sim = cosine_similarity(tfidf)
    times = np.array([it.published.timestamp() for it in items])
    far = np.abs(times[:, None] - times[None, :]) > MAX_GAP.total_seconds()
    sim[far] = 0.0
    np.fill_diagonal(sim, 1.0)
    return sim


def choose_lead(items: list[Item], sim: np.ndarray) -> Item:
    if len(items) == 1:
        return items[0]
    n = len(items)
    mean = (sim.sum(axis=1) - 1.0) / (n - 1)
    best = float(mean.max())
    candidates = [i for i in range(n) if mean[i] >= best - LEAD_TOLERANCE]
    free = [i for i in candidates if not items[i].plus]
    pool = free or candidates
    return items[max(pool, key=lambda i: mean[i])]


def _region(items: list[Item]) -> str | None:
    counts = Counter(r for it in items for r in it.regions)
    if not counts:
        return None
    top = max(counts.values())
    winners = [r for r, c in counts.items() if c == top]
    return "inland" if "inland" in winners else winners[0]


def cluster_items(items: list[Item], threshold: float, now: datetime) -> list[Story]:
    items = [it for it in items if now - it.published <= WINDOW]
    if not items:
        return []
    sim = similarity_matrix(items)
    if len(items) == 1:
        labels = np.array([0])
    else:
        model = AgglomerativeClustering(
            metric="precomputed", linkage="average", distance_threshold=1.0 - threshold, n_clusters=None
        )
        labels = model.fit_predict(np.clip(1.0 - sim, 0.0, 1.0))

    stories: list[Story] = []
    for label in sorted(set(labels.tolist())):
        idx = [i for i, l in enumerate(labels) if l == label]
        members = [items[i] for i in idx]
        sub = sim[np.ix_(idx, idx)]
        stories.append(
            Story(
                id="",
                items=members,
                lead=choose_lead(members, sub),
                region=_region(members),
                categories=set().union(*(it.categories for it in members)),
                latest=max(it.published for it in members),
            )
        )
    return stories
