from collector.cluster import cluster_items
from collector.region import guess_region
from tests.factory import NOW, mk


def test_foreign_countries_and_leaders_are_ausland():
    assert guess_region("Amtsinhaber Lula gewinnt Stichwahl in Brasilien", []) == "ausland"
    assert guess_region("Wahl in Israel: Endet die Ära Netanjahu?", []) == "ausland"
    assert guess_region("Midterms in den USA: Trump verliert junge Männer", []) == "ausland"
    assert guess_region("Russische Drohnen über Kiew", []) == "ausland"


def test_german_places_and_institutions_are_inland():
    assert guess_region("Weitere Bundesländer ausgeschieden: Endlagersuche wird konkreter", []) == "inland"
    assert guess_region("Bundestag beschließt Haushalt", []) == "inland"
    assert guess_region("Schlachthof in Bayern: Verfahren eingeleitet", []) == "inland"
    assert guess_region("SPD und CDU streiten über Rente", []) == "inland"


def test_keywords_count_too():
    assert guess_region("Neue Regierung vereidigt", ["frankreich", "paris"]) == "ausland"


def test_unclear_or_mixed_stays_none():
    assert guess_region("Typische Fehler: Diese Dinge bringen jede Beziehung zum Scheitern", []) is None
    assert guess_region("Kanzler Merz wirbt in Singapur für Freihandel", []) is None


def test_no_false_prefix_hits():
    # „Roman“ darf nicht als „Oman“, „Indianer“ nicht als „Indien“ gelten
    assert guess_region("Ein Roman über Indianer", []) is None


def test_feed_region_wins_over_guess():
    a = mk("x1", "a", "Bundestag debattiert Haushalt", regions=["ausland"])
    assert cluster_items([a], 0.35, NOW)[0].region == "ausland"


def test_guess_used_when_no_feed_region():
    a = mk("x1", "a", "Amtsinhaber Lula gewinnt Stichwahl in Brasilien")
    b = mk("x2", "b", "Typische Fehler in Beziehungen")
    stories = {s.items[0].id: s for s in cluster_items([a, b], 0.35, NOW)}
    assert stories["x1"].region == "ausland"
    assert stories["x2"].region is None
