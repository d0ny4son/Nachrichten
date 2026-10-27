"""Items für Tests bauen."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from collector.models import Item
from collector.text import keywords, stems

NOW = datetime(2026, 10, 27, 11, 0, tzinfo=timezone.utc)


def mk(iid, source, title, teaser="", hours_ago=1.0, plus=False, regions=None, categories=None, image=None, has_date=True):
    return Item(
        id=iid,
        source_id=source,
        title=title,
        link=f"https://example.org/{iid}",
        published=NOW - timedelta(hours=hours_ago),
        image=image,
        regions=set(regions or ()),
        categories=set(categories or ()),
        plus=plus,
        has_date=has_date,
        stems=stems(f"{title} {teaser}"),
        keywords=keywords(title, teaser),
    )


BUDGET = [
    ("b1", "tagesschau", "Bundestag debattiert über den Haushaltsentwurf", "Der Bundestag berät den Haushalt 2027 und die Schuldenbremse."),
    ("b2", "zeit", "Haushaltsdebatte im Bundestag: Was im Entwurf steht", "Der Haushaltsentwurf 2027 sieht Kürzungen vor, der Bundestag debattiert."),
    ("b3", "faz", "Opposition kritisiert Haushaltsentwurf im Bundestag", "Im Bundestag kritisiert die Opposition den Haushalt 2027 scharf."),
    ("b4", "taz", "Haushalt 2027: Bundestag streitet über Kürzungen", "Bei der Haushaltsdebatte im Bundestag geht es um Kürzungen und Schulden."),
]
OTHER = [
    ("o1", "spiegel", "Forschende entwickeln langlebigere Batteriespeicher", "Neue Kathoden sollen Akkus länger halten lassen."),
    ("o2", "welt", "Bahn legt neue Pünktlichkeitszahlen vor", "Die Deutsche Bahn war im Oktober seltener pünktlich."),
]
