from collector.text import keywords, stems, tokens


def test_tokens_lowercase_and_umlauts():
    assert tokens("Ärzte warnen: Hitze!") == ["ärzte", "warnen", "hitze"]


def test_tokens_drop_stopwords():
    assert tokens("Der Bundestag und die Länder") == ["bundestag", "länder"]


def test_tokens_keep_long_numbers_drop_short():
    assert tokens("Haushalt 2027 in 12 Punkten") == ["haushalt", "2027", "punkten"]


def test_stems_merge_inflections():
    assert stems("Haushalts") == stems("Haushalt")


def test_keywords_no_sentence_and_limit():
    kw = keywords("Bundestag debattiert Haushalt", "Der Bundestag streitet über den Haushalt und die Schulden der Länder.", limit=5)
    assert {"bundestag", "debattiert", "haushalt"} <= set(kw)
    assert kw == sorted(kw)
    assert len(kw) == len(set(kw))
    assert len(kw) <= 5
    assert "der" not in kw and "und" not in kw
