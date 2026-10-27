from collector.cluster import choose_lead, cluster_items, similarity_matrix
from tests.factory import BUDGET, NOW, OTHER, mk


def groups(stories):
    return sorted(sorted(i.id for i in s.items) for s in stories)


def test_same_event_grouped():
    items = [mk(*row) for row in BUDGET + OTHER]
    stories = cluster_items(items, threshold=0.2, now=NOW)
    assert groups(stories) == [["b1", "b2", "b3", "b4"], ["o1"], ["o2"]]


def test_more_than_24h_apart_never_grouped():
    a = mk("x1", "a", "Bundestag debattiert Haushalt", "Haushalt Bundestag", hours_ago=1)
    b = mk("x2", "b", "Bundestag debattiert Haushalt", "Haushalt Bundestag", hours_ago=31)
    stories = cluster_items([a, b], threshold=0.2, now=NOW)
    assert len(stories) == 2


def test_older_than_48h_dropped():
    a = mk("x1", "a", "Alte Meldung", hours_ago=49)
    b = mk("x2", "b", "Neue Meldung", hours_ago=1)
    stories = cluster_items([a, b], threshold=0.2, now=NOW)
    assert groups(stories) == [["x2"]]


def test_lead_prefers_free_article():
    a = mk("p1", "spiegel", "Bundestag beschließt Haushalt 2027", "Haushalt Bundestag beschlossen", plus=True)
    b = mk("f1", "tagesschau", "Bundestag beschließt Haushalt 2027", "Haushalt Bundestag beschlossen heute")
    c = mk("f2", "zeit", "Bundestag beschließt den Haushalt", "Haushalt beschlossen")
    items = [a, b, c]
    lead = choose_lead(items, similarity_matrix(items))
    assert lead.plus is False


def test_region_majority_and_none():
    a = mk("r1", "a", "Haushalt Bundestag Debatte", regions=["inland"])
    b = mk("r2", "b", "Haushalt Bundestag Debatte heute", regions=["inland"])
    c = mk("r3", "c", "Haushalt Bundestag Debatte Streit", regions=["ausland"])
    story = cluster_items([a, b, c], threshold=0.2, now=NOW)[0]
    assert story.region == "inland"
    lone = cluster_items([mk("n1", "a", "Ohne Region")], threshold=0.2, now=NOW)[0]
    assert lone.region is None


def test_region_tie_prefers_inland_and_categories_union():
    a = mk("r1", "a", "Haushalt Bundestag Debatte", regions=["ausland"], categories=["wirtschaft"])
    b = mk("r2", "b", "Haushalt Bundestag Debatte heute", regions=["inland"], hours_ago=0.5)
    story = cluster_items([a, b], threshold=0.2, now=NOW)[0]
    assert story.region == "inland"
    assert story.categories == {"wirtschaft"}
    assert story.latest == b.published


def test_single_item_and_empty_input():
    assert cluster_items([], threshold=0.35, now=NOW) == []
    one = cluster_items([mk("s1", "a", "Einzelmeldung")], threshold=0.35, now=NOW)
    assert len(one) == 1 and one[0].lead.id == "s1" and one[0].id == ""
