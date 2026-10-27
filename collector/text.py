"""Text-Aufbereitung: Wörter, Wortstämme und Stichwort-Listen."""
from __future__ import annotations

import re

import snowballstemmer

STOPWORDS = frozenset(
    """
    aber alle allem allen aller alles als also am an ander andere anderem anderen anderer anderes
    auch auf aus bei beim bin bis bist da damit dann das dass dein deine dem den denn der des dessen
    deshalb die dies diese diesem diesen dieser dieses doch dort du durch ein eine einem einen einer
    eines einige einmal er es etwa etwas euch euer für gegen gewesen hab habe haben hat hatte hatten
    hier hin hinter ich ihr ihre ihrem ihren ihrer ihres im in indem ins ist ja jede jedem jeden jeder
    jedes jetzt kann kein keine keinem keinen keiner können könnte machen man manche mehr mein meine
    mit muss müssen nach nicht nichts noch nun nur ob oder ohne sehr sein seine seinem seinen seiner
    seit sich sie sind so solche soll sollen sondern sowie über um und uns unser unter viel vom von
    vor wann war waren warum was weil weiter welche welchem welchen welcher wenn wer werde werden wie
    wieder will wir wird wo wollen worden wurde wurden zu zum zur zwar zwischen neue neuen neuer neues
    heute gestern morgen sagt sagte laut rund mal schon immer bereits sei seien ab beim wegen trotz
    während diesem jenen jener jenes ihm ihn ihnen dich dir mich mir uns euch sich selbst kaum zudem
    dabei dazu darauf darüber davon dafür dagegen daher dies gibt geht gab
    """.split()
)

_WORD = re.compile(r"[0-9a-zäöüß]+", re.IGNORECASE)
_stemmer = snowballstemmer.stemmer("german")


def tokens(text: str) -> list[str]:
    """Kleingeschriebene Wörter ohne Stoppwörter, Länge >= 3."""
    out = []
    for w in _WORD.findall(text.lower()):
        if len(w) < 3 or w in STOPWORDS:
            continue
        out.append(w)
    return out


def stems(text: str) -> list[str]:
    """Wortstämme für die Bündelung."""
    return _stemmer.stemWords(tokens(text))


def keywords(title: str, teaser: str, limit: int = 25) -> list[str]:
    """Eindeutige Wörter (Titel zuerst bei der Auswahl), alphabetisch sortiert."""
    seen: dict[str, None] = {}
    for w in tokens(title) + tokens(teaser):
        if w not in seen:
            seen[w] = None
            if len(seen) >= limit:
                break
    # Alphabetisch sortiert: eine Wortliste ohne Satzbau, kein Textauszug.
    return sorted(seen)
