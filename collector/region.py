"""Inland/Ausland schätzen, wenn der Feed keine Region liefert.

Bewusst eine nachvollziehbare Namensliste statt eines lernenden Modells:
Ein Test mit echten Daten (27.10.2026) zeigte, dass ein gelerntes Modell
außerhalb von Politikmeldungen viel falsch zuordnet. Treffen Wörter aus
beiden Listen zu (z. B. „Merz in Singapur“), bleibt die Region offen.

Einträge ab 5 Buchstaben gelten auch als Wortanfang („russisch“ trifft
„russischen“), kürzere nur als ganzes Wort („usa“, „oman“).
"""
from __future__ import annotations

import re

AUSLAND = """
usa amerika amerikan vereinigten washington trump biden vance harris kalifornien texas florida
kanada kanadisch mexiko mexikan brasilien brasilian argentinien argentin chile venezuela kolumbien kuba peru
lula milei maduro
russland russisch moskau kreml putin
ukraine ukrain kiew selenskyj charkiw odessa
belarus lukaschenko
china chinesisch peking xi taiwan taiwanes hongkong japan japanisch tokio korea koreanisch pjöngjang seoul
indien indisch modi pakistan pakistanisch afghanistan afghanisch taliban bangladesch
thailand thailänd vietnam indonesien philippinen singapur malaysia myanmar australien australisch neuseeland
israel israelisch netanjahu jerusalem gaza hamas hisbollah westjordanland palästin libanon libanes
syrien syrisch damaskus iran iranisch teheran irak irakisch bagdad jemen huthi
saudi arabien arabisch katar emirate dubai jordanien ägypten ägyptisch türkei türkisch erdogan ankara istanbul
afrika afrikan nigeria kenia äthiopien sudan südafrika marokko algerien tunesien libyen kongo mali
frankreich französisch paris macron großbritannien britisch england englisch london starmer schottland irland
spanien spanisch madrid italien italienisch rom meloni portugal griechenland griechisch
niederlande niederländisch amsterdam belgien belgisch luxemburg
schweiz schweizer zürich bern österreich österreichisch wien
polen polnisch warschau tschechien tschechisch prag slowakei ungarn ungarisch orban budapest
rumänien bulgarien serbien kroatien bosnien kosovo albanien moldau georgien armenien aserbaidschan
dänemark dänisch schweden schwedisch norwegen norwegisch finnland finnisch estland lettland litauen
nato eu brüssel uno vereinte
"""

INLAND = """
deutschland bundestag bundesrat bundesregierung bundesland bundesländer bundesverfassungsgericht bundesminister
bundespräsident bundesamt bundesagentur bundesliga dfb
cdu csu spd afd fdp bsw grüne grünen linke linkspartei
merz scholz söder habeck lindner weidel klingbeil dobrindt pistorius wadephul hubig steinmeier wüst
bayern bayerisch baden württemberg hessen hessisch sachsen sächsisch thüringen thüringisch brandenburg
niedersachsen nordrhein westfalen rheinland pfalz saarland schleswig holstein mecklenburg vorpommern
berlin hamburg münchen köln frankfurt stuttgart düsseldorf dortmund leipzig bremen dresden hannover
nürnberg duisburg bochum wuppertal bielefeld bonn mannheim karlsruhe augsburg wiesbaden kiel magdeburg
erfurt mainz potsdam schwerin saarbrücken rostock chemnitz freiburg
"""

_WORD = re.compile(r"[0-9a-zäöüß]+")


def _terms(text: str) -> tuple[frozenset[str], tuple[str, ...]]:
    words = text.split()
    exact = frozenset(words)
    prefixes = tuple(w for w in words if len(w) >= 5)
    return exact, prefixes


_AUS = _terms(AUSLAND)
_IN = _terms(INLAND)


def _hits(words: list[str], terms) -> bool:
    exact, prefixes = terms
    return any(w in exact or w.startswith(prefixes) for w in words)


def guess_region(title: str, keywords: list[str]) -> str | None:
    words = _WORD.findall(title.lower()) + [k.lower() for k in keywords]
    aus = _hits(words, _AUS)
    inl = _hits(words, _IN)
    if aus and not inl:
        return "ausland"
    if inl and not aus:
        return "inland"
    return None
