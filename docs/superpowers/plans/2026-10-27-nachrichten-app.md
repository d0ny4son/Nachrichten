# Nachrichten-App – Bauplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Ziel:** Eine kostenlose, werbefreie Smartphone-Web-App, die RSS-Meldungen von 11 deutschsprachigen Medien zu Geschichten bündelt und pro Geschichte alle Quellen vergleichbar macht.

**Architektur:** Ein Python-Sammler (`collector/`) läuft per GitHub-Actions-Zeitplan alle 20 Minuten. Er holt die Feeds, bündelt die Meldungen, rankt sie und schreibt `site/data/stories.json`. Eine PWA ohne Build-Schritt (`site/`, Vanilla-JS-Module) wird über GitHub Pages ausgeliefert, lädt nur diese Datei und filtert sie auf dem Handy nach den lokal gespeicherten Einstellungen.

**Tech-Stack:** Python ≥ 3.12, `feedparser`, `requests`, `PyYAML`, `scikit-learn`, `snowballstemmer`, `pytest`; HTML/CSS/JS-ES-Module, Service Worker, `node --test` (Node ≥ 20, keine npm-Abhängigkeiten); GitHub Actions + GitHub Pages.

**Spec:** Claude-Dokument „Konzept: Nachrichten-App“, https://claude.ai/artifact/MdXNWr7kXjoBMtgZVXroQE (Lesen: `mcp__Claude_Docs__export`, container `{"kind":"project","id":"a7104403-6f97-4d0f-80fa-575071ba7d43"}`, file `1e48f99c-9ae3`, format `markdown`). Handy-Entwürfe: https://claude.ai/artifact/NzuHKqghDsB4SX8sLhGatf

## Global Constraints

- Laufende Kosten 0 €. Keine bezahlten Dienste, keine Werbung, kein Tracking, keine Benutzerkonten.
- Veröffentlichte Daten enthalten **keine Anrisstexte**. Pro Meldung nur Überschrift, Quelle, Zeit, Link, Bild-Adresse, Rubrik, Plus-Markierung und eine Liste wichtiger Wörter ohne Satzbau.
- Bilder werden nur verlinkt, nie kopiert oder gespeichert.
- Abruf höchstens alle 15 Minuten, mit User-Agent `NachrichtenApp/1.0 (privat; +https://github.com/<user>/<repo>)` und Zwischenspeicher (ETag/Last-Modified).
- Eine Geschichte = **ein Ereignis**. Meldungen, die mehr als 24 h auseinanderliegen, gehören nie zusammen. Das Gesamtfenster der Bündelung beträgt 48 h.
- Im Zweifel trennen: Präzision vor Vollständigkeit.
- Medientypen (exakt): `oeffentlich-rechtlich`, `zeitung`, `international`. Anzeigenamen: „Öffentlich-rechtlich“, „Zeitungen“, „International“.
- Kategorien (exakt): `wissenschaft`, `technik`, `wirtschaft`, `kultur`, `sport`. Regionen: `inland`, `ausland`.
- Ranking ohne Personalisierung. Ausgeblendete Themen wirken auf dem Handy **überall**, auch auf „Aktuell“.
- Einstellungen verlassen das Gerät nie.
- Gesamte Oberflächensprache Deutsch. Die untere Leiste hat genau drei Bereiche: „Aktuell“, „Für dich“, „Interessen“.
- Pflege ohne Programmierkenntnisse: Quellen werden im GitHub-Webeditor geändert, Tippfehler meldet ein Prüf-Workflow, der Zeitplan wird automatisch aktiv gehalten, das Testset ist eine normale CSV-Tabelle.

## Review Focus

1. **Eine Quelle ist kaputt** (404, Zeitüberschreitung, kaputtes XML): Alle anderen Quellen laufen weiter, und `status.json` nennt den Fehler. Liefern **alle** Quellen nichts, bleibt die alte `stories.json` stehen und wird nicht durch eine leere ersetzt. → Tests in Task 7.
2. **Dieselbe Meldung in mehreren Feeds einer Quelle** (Top-Feed und Inland-Feed): Sie erscheint nur einmal. Regionen und Kategorien werden zusammengeführt. → Test in Task 2.
3. **Meldung ohne Datum:** Als Zeit gilt der Moment, an dem der Sammler sie zum ersten Mal gesehen hat. Bei späteren Läufen bleibt dieser Zeitpunkt erhalten und springt nicht weiter. → Tests in Task 2 und Task 7.
4. **localStorage gesperrt** (privater Modus, iOS): Die App läuft mit den Standard-Einstellungen weiter und stürzt nicht ab. → Test in Task 10.
5. **Stichworte mit Umlauten, Großschreibung, Leerzeichen:** „wasserstoff“ findet „Wasserstoffnetz“, und „ärzte“ findet „Ärztekammer“. Ein leeres Stichwort wird nicht angenommen. → Tests in Task 10.

---

## Dateistruktur

```
collector/
  __init__.py
  models.py        Item, Story (Dataclasses)
  config.py        load_config(), ConfigError
  fetch.py         fetch_feed(), parse_feed(), dedupe_items(), item_id()
  text.py          tokens(), keywords()
  cluster.py       cluster_items(), choose_lead()
  ids.py           assign_story_ids()
  rank.py          score()
  og_image.py      extract_og_image(), fill_missing_images()
  output.py        build_output(), write_json_atomic()
  state.py         load_state(), save_state()
  main.py          run()  (python -m collector.main)
  evaluate.py      export_testset(), pairwise_scores()  (python -m collector.evaluate)
config/sources.yaml
tests/             pytest + tests/fixtures/*.xml|html
site/
  index.html  app.css  manifest.webmanifest  sw.js  icon.svg
  js/data.js  js/settings.js  js/filters.js  js/format.js  js/views.js  js/app.js
  data/            stories.json, status.json, state.json (vom Sammler geschrieben)
site-tests/        *.test.mjs (node --test)
evaluation/        testset.csv (vom Workflow), labelled.csv (von Yassine)
.github/workflows/ collect.yml  validate.yml  keepalive.yml  evaluate.yml
docs/ANLEITUNG.md
requirements.txt
```

---

### Task 1: Projektgerüst und Quellen-Konfiguration

**Files:**
- Create: `requirements.txt`, `collector/__init__.py`, `collector/models.py`, `collector/config.py`, `config/sources.yaml`, `tests/test_config.py`, `.gitignore`

**Interfaces:**
- Produces:
  - `@dataclass Feed(url: str, region: str | None, category: str | None)`
  - `@dataclass Source(id: str, name: str, media_type: str, feeds: list[Feed], plus_patterns: list[str])`
  - `@dataclass Config(sources: list[Source], threshold: float)`
  - `load_config(path: str | Path) -> Config`, wirft `ConfigError(message: str)`
  - `@dataclass Item(id: str, source_id: str, title: str, link: str, published: datetime, image: str | None, regions: set[str], categories: set[str], plus: bool, has_date: bool, stems: list[str], keywords: list[str])`. Es gibt **kein Feld für den Anrisstext**: Er wird beim Lesen sofort in `stems` (für die Bündelung) und `keywords` (für die Suche) umgewandelt und danach verworfen. `state.json` liegt im öffentlichen Repository und darf ihn deshalb nicht enthalten.
  - `@dataclass Story(id: str, items: list[Item], lead: Item, region: str | None, categories: set[str], latest: datetime, score: float = 0.0)`

`sources.yaml` hat das Format:

```yaml
clustering:
  threshold: 0.35
sources:
  - id: tagesschau
    name: Tagesschau
    media_type: oeffentlich-rechtlich
    plus_patterns: []
    feeds:
      - {url: "https://www.tagesschau.de/index~rss2.xml"}
      - {url: "https://www.tagesschau.de/inland/index~rss2.xml", region: inland}
      - {url: "https://www.tagesschau.de/ausland/index~rss2.xml", region: ausland}
```

Trage alle 11 Quellen aus der Spec ein: tagesschau, zdfheute, deutschlandfunk, spiegel, sueddeutsche, zeit, taz, faz, welt, nzz, dw. Nimm Feed-Adressen nach bestem Wissen, inklusive Inland-, Ausland- und Kategorie-Feeds. Die Adressen werden erst beim ersten echten Lauf über `status.json` geprüft. Schreibe deshalb an jede Adresse, deren Existenz du nicht sicher kennst, den Kommentar `# ungeprüft`. Als `plus_patterns` nimm die bekannten URL-Muster, z. B. `"/plus/"` und `"spiegel\\.de/.*\\+"`, ebenfalls mit `# ungeprüft`.

- [ ] **Step 1: Write failing tests** in `tests/test_config.py`:
  - `test_loads_example_config`: Die echte `config/sources.yaml` lädt. Erwartet: `len(cfg.sources) == 11`, `cfg.threshold == 0.35`, alle IDs eindeutig.
  - `test_rejects_unknown_media_type`: `media_type: zeitschrift` → `ConfigError`, die Meldung enthält `"tagesschau"` und `"media_type"`.
  - `test_rejects_unknown_region_and_category`: `region: europa` bzw. `category: politik` → `ConfigError`.
  - `test_rejects_duplicate_source_id` und `test_rejects_source_without_feeds`.
  - `test_rejects_invalid_plus_pattern`: Das Muster `"("` → `ConfigError`.
  - `test_yaml_syntax_error_is_configerror`: Kaputtes YAML → `ConfigError`. Die Meldung ist auf Deutsch und nennt die Zeilennummer.
- [ ] **Step 2:** Run `pytest tests/test_config.py -v`. Erwartet: FAIL (ImportError).
- [ ] **Step 3:** Implementiere `models.py` und `config.py`. Alle `ConfigError`-Meldungen sind deutsche, verständliche Sätze, z. B. „Quelle ‚tagesschau‘: media_type ‚zeitschrift‘ ist unbekannt. Erlaubt: oeffentlich-rechtlich, zeitung, international.“ `requirements.txt` listet: `feedparser`, `requests`, `PyYAML`, `scikit-learn`, `snowballstemmer`, `pytest`.
- [ ] **Step 4:** Run `pytest tests/test_config.py -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: Quellen-Konfiguration mit Prüfung`

---

### Task 2: Feeds abrufen, lesen und Dubletten entfernen

*(Reihenfolge: Task 3 vor Task 2 ausführen, da `parse_feed` `stems()` und `keywords()` braucht.)*

**Files:**
- Create: `collector/fetch.py`, `tests/test_fetch.py`, `tests/fixtures/rss_basic.xml`, `tests/fixtures/rss_media.xml`, `tests/fixtures/atom_basic.xml`

**Interfaces:**
- Consumes: `Source`, `Feed`, `Item` (Task 1), `stems()`, `keywords()` (Task 3)
- Produces:
  - `item_id(link: str) -> str`: sha1 der kanonischen URL (ohne Query-Parameter `utm_*`, ohne `#fragment`, kleingeschriebener Host), die ersten 16 Hex-Zeichen.
  - `fetch_feed(url: str, http_cache: dict, session: requests.Session) -> bytes | None`: Timeout 20 s, sendet If-None-Match/If-Modified-Since aus `http_cache[url]` und aktualisiert den Cache. 304 → `None`. Fehler → wirft `FetchError`.
  - `parse_feed(data: bytes, source: Source, feed: Feed, now: datetime, first_seen: dict[str, str]) -> list[Item]`
  - `dedupe_items(items: list[Item]) -> list[Item]`

- [ ] **Step 1: Write failing tests:**
  - `test_parse_rss_basic`: Felder `title`, `link` und `published` (UTC-aware) sind korrekt. `regions == {feed.region}`, wenn gesetzt. `stems == stems(title + " " + anriss_ohne_html)` und `keywords == keywords(title, anriss_ohne_html)` (Task 3). Das Item hat kein Attribut mit dem Anrisstext.
  - `test_image_from_media_content_and_enclosure`: Das Bild kommt aus `media:content`, `media:thumbnail` oder `enclosure` mit `type` `image/*`, in dieser Reihenfolge. Ohne Bild → `None`.
  - `test_image_from_description_img`: Steht ein `<img src>` im Beschreibungstext, wird es als Bild genommen.
  - `test_plus_detection`: Der Link passt auf `plus_patterns` → `plus is True`.
  - `test_missing_date_uses_first_seen`: Beim ersten Lauf gilt `published == now` und `has_date is False`. Ist `first_seen[id]` gesetzt, wird dieser Wert genommen, auch wenn sich `now` geändert hat.
  - `test_item_id_canonical`: `https://X.de/a?utm_source=x#top` und `https://x.de/a` ergeben dieselbe ID. `?id=2` ergibt eine andere.
  - `test_dedupe_merges_regions_and_categories`: Dieselbe ID in zwei Feeds → ein Item. `regions` und `categories` sind vereinigt, das Bild ist das erste vorhandene.
  - `test_fetch_feed_304_returns_none` und `test_fetch_feed_sends_etag`: mit einer gefälschten Session ohne Netzwerk.
- [ ] **Step 2:** Run `pytest tests/test_fetch.py -v`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere mit `feedparser.parse(data)`. HTML-Tags im Anrisstext entfernst du mit `html.parser` aus der Standardbibliothek.
- [ ] **Step 4:** Run `pytest tests/test_fetch.py -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: Feeds lesen, Bilder, Plus-Erkennung, Dubletten`

---

### Task 3: Text-Aufbereitung und Stichwort-Listen

**Files:**
- Create: `collector/text.py`, `tests/test_text.py`

**Interfaces:**
- Produces:
  - `tokens(text: str) -> list[str]`: Kleinschreibung, Umlaute und ß bleiben erhalten, Satzzeichen werden entfernt, deutsche Stoppwörter fallen weg, Länge ≥ 3. Zahlen bleiben, wenn sie ≥ 3 Zeichen haben (z. B. 2027).
  - `stems(text: str) -> list[str]`: `tokens()` + `snowballstemmer.stemmer("german")`. Wird nur für die Bündelung genutzt.
  - `keywords(title: str, teaser: str, limit: int = 25) -> list[str]`: eindeutige `tokens()` aus Titel und Anrisstext, zuerst die aus dem Titel, höchstens `limit`. Ungestemmt, damit die Präfixsuche auf dem Handy funktioniert.

- [ ] **Step 1: Write failing tests:**
  - `test_tokens_lowercase_and_umlauts`: `"Ärzte warnen: Hitze!"` → `["ärzte", "warnen", "hitze"]`.
  - `test_tokens_drop_stopwords`: `"Der Bundestag und die Länder"` → `["bundestag", "länder"]`.
  - `test_stems_merge_inflections`: `stems("Haushalts")` und `stems("Haushalt")` ergeben denselben Stamm.
  - `test_keywords_no_sentence_and_limit`: Das Ergebnis enthält keine Duplikate und keine Stoppwörter, hat höchstens `limit` Einträge, und die Titelwörter stehen vorn.
- [ ] **Step 2:** Run `pytest tests/test_text.py -v`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere. Die Stoppwortliste ist eine Konstante `STOPWORDS` in `text.py`: gängige deutsche Funktionswörter, ca. 150 Einträge.
- [ ] **Step 4:** Run `pytest tests/test_text.py -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: Text-Aufbereitung und Stichwort-Listen`

---

### Task 4: Bündelung zu Geschichten

**Files:**
- Create: `collector/cluster.py`, `tests/test_cluster.py`

**Interfaces:**
- Consumes: `Item`, `Story` (Task 1), `stems()` (Task 3)
- Produces:
  - `similarity_matrix(items: list[Item]) -> numpy.ndarray`: TF-IDF über `item.stems` (`TfidfVectorizer(analyzer=lambda s: s)`), Kosinus-Ähnlichkeit. Für Paare mit `|Δ published| > 24 h` gilt Ähnlichkeit 0.
  - `cluster_items(items: list[Item], threshold: float, now: datetime) -> list[Story]`: Zuerst werden Items außerhalb von 48 h vor `now` verworfen. Dann `AgglomerativeClustering(metric="precomputed", linkage="average", distance_threshold=1 - threshold, n_clusters=None)` auf `1 - similarity`. Ein einzelnes Item ergibt eine eigene Geschichte. `Story.id` bleibt hier `""`, IDs vergibt Task 5.
  - `choose_lead(items: list[Item], sim: ndarray) -> Item`: das Item mit der höchsten mittleren Ähnlichkeit zu den anderen. Unter allen Items, deren Wert höchstens 0.05 unter dem besten liegt, wird das beste **nicht-Plus**-Item vorgezogen.
  - Region der Geschichte: die häufigste Region ihrer Items. Bei Gleichstand gewinnt `inland`. Hat kein Item eine Region → `None`. Kategorien sind die Vereinigung, `latest` ist das Maximum von `published`.

- [ ] **Step 1: Write failing tests:**
  - `test_same_event_grouped`: Vier Überschriften und Anrisstexte zur Haushaltsdebatte aus vier Quellen plus zwei fachfremde Meldungen → genau eine Geschichte mit vier Items und zwei Einzel-Geschichten.
  - `test_more_than_24h_apart_never_grouped`: Zwei nahezu identische Texte im Abstand von 30 h → zwei Geschichten.
  - `test_older_than_48h_dropped`
  - `test_lead_prefers_free_article`: Zwei fast gleichwertige Kandidaten, der beste ist Plus → das freie Item wird Hauptmeldung.
  - `test_region_majority_and_none`
  - `test_single_item_and_empty_input`: `[]` → `[]`.
- [ ] **Step 2:** Run `pytest tests/test_cluster.py -v`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `pytest tests/test_cluster.py -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: Bündelung zu Geschichten`

---

### Task 5: Stabile Geschichten-IDs und Ranking

**Files:**
- Create: `collector/ids.py`, `collector/rank.py`, `tests/test_ids_rank.py`

**Interfaces:**
- Consumes: `Story` (Task 1)
- Produces:
  - `assign_story_ids(stories: list[Story], previous: dict[str, list[str]]) -> None`: `previous` ordnet einer alten Geschichten-ID ihre Item-IDs zu. Jede neue Geschichte übernimmt die alte ID mit der größten Überlappung der Item-IDs, wenn diese Überlappung ≥ 50 % der kleineren Menge beträgt. Eine alte ID wird höchstens einmal vergeben. Sonst ist die ID `"s" + sha1(sorted item ids)[:12]`.
  - `score(story: Story, now: datetime, half_life_h: float = 6.0) -> float`: Anzahl **verschiedener Quellen** × `0.5 ** (Alter_der_neuesten_Meldung_h / half_life_h)`.

- [ ] **Step 1: Write failing tests:**
  - `test_id_kept_when_story_grows`: Alte Geschichte {a,b}, neue {a,b,c} → gleiche ID.
  - `test_id_new_when_no_overlap`
  - `test_old_id_not_reused_twice`: Eine alte Geschichte zerfällt in zwei neue → nur eine davon erbt die ID.
  - `test_score_counts_distinct_sources`: Zwei Items derselben Quelle zählen als 1.
  - `test_score_decays`: Bei gleicher Quellenzahl wiegt eine 6 h alte Geschichte halb so viel wie eine frische.
- [ ] **Step 2:** Run. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `pytest tests/test_ids_rank.py -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: stabile IDs und Ranking`

---

### Task 6: Vorschaubilder über die Artikelseite

**Files:**
- Create: `collector/og_image.py`, `tests/test_og_image.py`, `tests/fixtures/article_og.html`

**Interfaces:**
- Consumes: `Story`, `Item`
- Produces:
  - `extract_og_image(html: str, base_url: str) -> str | None`: liest `og:image`, ersatzweise `twitter:image`. Relative URLs werden absolut gemacht. Nur `http(s)` ist erlaubt.
  - `fill_missing_images(stories: list[Story], cache: dict[str, str | None], session, max_fetches: int = 40) -> None`: Betrifft nur die **Hauptmeldung** ohne Bild. Zuerst wird in `cache` (Link → Bild oder `None`) nachgesehen, sonst die Seite geladen (Timeout 10 s, nur die ersten 300 KB). Fehler zählen als `None` und landen im Cache. Pro Lauf gibt es höchstens `max_fetches` Seitenabrufe.

- [ ] **Step 1: Write failing tests:**
  - `test_extract_og_image`, `test_extract_twitter_fallback`, `test_relative_url_made_absolute`, `test_rejects_javascript_url`
  - `test_fill_only_leads_and_respects_cache_and_limit`: Bei drei Geschichten ohne Bild, einer davon im Cache, und `max_fetches=1` wird genau ein Abruf gemacht. Die Nicht-Hauptmeldungen bleiben unberührt.
- [ ] **Step 2:** Run. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere mit `html.parser` aus der Standardbibliothek.
- [ ] **Step 4:** Run `pytest tests/test_og_image.py -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: Vorschaubilder per og:image`

---

### Task 7: Ausgabe, Zustand und Gesamtlauf

**Files:**
- Create: `collector/output.py`, `collector/state.py`, `collector/main.py`, `tests/test_output.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: alles aus Task 1–6
- Produces:
  - `build_output(stories: list[Story], config: Config, generated_at: datetime) -> dict` mit **Schema v1**. Dieses Schema ist der Vertrag mit der App aus Task 10:

```json
{
  "version": 1,
  "generated_at": "2026-10-27T11:20:00Z",
  "sources": {"tagesschau": {"name": "Tagesschau", "media_type": "oeffentlich-rechtlich"}},
  "stories": [
    {"id": "s1a2b3c4d5e6", "score": 3.7, "region": "inland",
     "categories": ["wirtschaft"], "latest": "2026-10-27T11:08:00Z",
     "lead": "ab12cd34ef56ab78",
     "items": [{"id": "ab12cd34ef56ab78", "source": "tagesschau",
                "title": "…", "link": "https://…", "published": "2026-10-27T11:08:00Z",
                "image": "https://…" , "plus": false, "keywords": ["bundestag", "haushalt"]}]}
  ]
}
```

    Die Geschichten sind nach `score` absteigend sortiert, die Items innerhalb einer Geschichte nach `published` absteigend. `image` steht nur an der Hauptmeldung, sonst ist es `null`.
  - `write_json_atomic(path: Path, data: dict) -> None`: schreibt erst in eine temporäre Datei und ersetzt dann per `os.replace`.
  - `load_state(path) -> dict` / `save_state(path, state)`. Schlüssel: `http_cache`, `first_seen` (Item-ID → ISO), `og_cache`, `items` (Item-ID → serialisiertes Item mit `stems` und `keywords`, nur Items der letzten 48 h), `stories` (Geschichten-ID → Item-IDs). `state.json` liegt in `site/data/`, wird aber **nicht** auf Pages veröffentlicht, weil Task 8 sie vor dem Hochladen herausfiltert.
  - `run(config_path: Path, data_dir: Path, now: datetime, session) -> int`: Ablauf: Konfiguration laden → jeden Feed holen (bei `None` die gespeicherten Items dieser Quelle behalten) → `parse_feed` → mit den gespeicherten Items zusammenführen → `dedupe_items` → `cluster_items` → `assign_story_ids` → `score` → `fill_missing_images` → `stories.json`, `status.json` und `state.json` schreiben. Rückgabe ist der Exit-Code: 0 ok; 1, wenn **alle** Quellen fehlschlagen. In diesem Fall wird `stories.json` **nicht** überschrieben.
  - `status.json`: `{"generated_at": …, "sources": {"<id>": {"ok": bool, "items": int, "with_image": int, "plus": int, "errors": ["<feed-url>: <meldung>"]}}}`
  - `python -m collector.main` ruft `run(Path("config/sources.yaml"), Path("site/data"), datetime.now(UTC), requests.Session())` auf.

- [ ] **Step 1: Write failing tests:**
  - `test_no_teaser_in_any_written_file`: Nach `run()` mit einer Fixture, deren Anrisstext den Satz „Dieser Satz ist ein Anrisstext.“ enthält, kommt dieser Satz weder in `stories.json` noch in `status.json` noch in `state.json` vor.
  - `test_output_schema_and_sorting`: Schlüssel wie oben, Sortierung nach `score` und `published`, `image` nur an der Hauptmeldung.
  - `test_write_json_atomic`
  - `test_run_one_source_broken`: Die gefälschte Session wirft für eine Quelle einen Fehler, die anderen liefern Fixtures → Exit 0, `status["sources"][kaputt]["ok"] is False`, die anderen sind `True`, und die Geschichten enthalten Meldungen der funktionierenden Quellen.
  - `test_run_all_sources_broken_keeps_old_file`: Eine alte `stories.json` existiert, alle Abrufe scheitern → Exit 1, die Datei ist byte-gleich.
  - `test_run_304_keeps_previous_items`: Zweiter Lauf mit 304 für alle Feeds → dieselben Geschichten-IDs wie im ersten Lauf.
  - `test_run_undated_item_keeps_first_seen_time`: Eine Meldung ohne Datum, zwei Läufe mit `now` im Abstand von 20 Min → Im zweiten Lauf ist `published` noch der Zeitpunkt des ersten Laufs.
- [ ] **Step 2:** Run `pytest tests/test_output.py tests/test_main.py -v`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `pytest -v`. Erwartet: alle PASS.
- [ ] **Step 5: Commit** `feat: Gesamtlauf mit Ausgabe, Status und Zustand`

---

### Task 8: GitHub-Workflows und Einrichtungsanleitung

**Files:**
- Create: `.github/workflows/collect.yml`, `.github/workflows/validate.yml`, `.github/workflows/keepalive.yml`, `docs/ANLEITUNG.md`, `tests/test_workflows.py`

**Interfaces:**
- Consumes: `python -m collector.main` (Task 7), `load_config` (Task 1)

Festlegungen:
- `collect.yml`: `schedule: cron "*/20 * * * *"` + `workflow_dispatch`; `permissions: contents: write, pages: write, id-token: write`; `concurrency: collect` mit `cancel-in-progress: false`. Schritte: Checkout → `actions/setup-python` mit 3.12 und pip-Cache → `pip install -r requirements.txt` → `python -m collector.main` → Commit von `site/data/` als `github-actions[bot]`, nur bei Änderungen → `site/` nach `_site/` kopieren **ohne** `data/state.json` → `actions/upload-pages-artifact` (path `_site`) → `actions/deploy-pages`. Exit 1 aus dem Sammler lässt den Lauf rot werden, deployed aber trotzdem die alte Datei.
- `validate.yml`: Läuft bei `push` und `pull_request` auf `config/**`, `collector/**`, `site/**`, `tests/**`, `site-tests/**`. Schritte: `pytest -q` und `node --test site-tests/`. Ein Tippfehler in `sources.yaml` erzeugt eine rote Prüfung mit der deutschen `ConfigError`-Meldung.
- `keepalive.yml`: monatlich (`cron "17 4 1 * *"`) + `workflow_dispatch`, `permissions: actions: write`. Schritt: `gh api -X PUT repos/${{ github.repository }}/actions/workflows/collect.yml/enable` mit `GH_TOKEN: ${{ github.token }}`.
- `docs/ANLEITUNG.md` (Deutsch, nur Klicks im Browser): GitHub-Konto anlegen → Projekt hochladen bzw. Repository anlegen und Dateien hochladen → Settings › Pages › Source „GitHub Actions“ → Actions › „collect“ › „Run workflow“ → Link öffnen → auf dem Handy zum Startbildschirm hinzufügen (iPhone: Teilen › „Zum Home-Bildschirm“; Android: Menü › „App installieren“) → Quelle ändern im Webeditor (Stift-Symbol bei `config/sources.yaml`, danach auf grünen oder roten Haken achten) → `site/data/status.json` lesen, um kaputte Quellen zu finden.

- [ ] **Step 1: Write failing test** `tests/test_workflows.py`: Lädt die drei YAML-Dateien und prüft:
  - Der Cron von `collect.yml` ist `*/20 * * * *`.
  - Es gibt einen Schritt mit `deploy-pages`.
  - Der Kopierschritt schließt `state.json` aus (der String `state.json` kommt im Kopierschritt vor).
  - `keepalive.yml` enthält `/enable` und `actions: write`.
  - `validate.yml` ruft `pytest` und `node --test` auf.
- [ ] **Step 2:** Run `pytest tests/test_workflows.py -v`. Erwartet: FAIL.
- [ ] **Step 3:** Schreibe die Workflows und die Anleitung.
- [ ] **Step 4:** Run `pytest -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `ci: Zeitplan, Prüfung, Aktivhalten, Anleitung`

---

### Task 9: Qualitätsmessung der Bündelung

**Files:**
- Create: `collector/evaluate.py`, `.github/workflows/evaluate.yml`, `tests/test_evaluate.py`
- Modify: `docs/ANLEITUNG.md` (Abschnitt „Bündelung prüfen“)

**Interfaces:**
- Consumes: `load_state` (Task 7), `cluster_items` (Task 4), `Item`
- Produces:
  - `export_testset(state: dict, n: int, out: Path, seed: int = 0) -> None`: CSV (Trennzeichen `;`, UTF-8 mit BOM, damit Excel Umlaute korrekt anzeigt) mit den Spalten `id;quelle;zeit;ueberschrift;link;geschichte`. Die Spalte `geschichte` bleibt leer. Gezogen werden `n` Items aus dem Zustand, zeitlich sortiert.
  - `pairwise_scores(labels: dict[str, str], predicted: dict[str, str]) -> tuple[float, float]`: (Präzision, Vollständigkeit) über alle Paare von Item-IDs, die in `labels` stehen. Bei 0 vorhergesagten Paaren gilt die Präzision als 1.0.
  - CLI: `python -m collector.evaluate export --n 100` → `evaluation/testset.csv`. `python -m collector.evaluate score` liest `evaluation/labelled.csv`, bündelt die beschrifteten Items mit den Schwellwerten 0.20, 0.25, …, 0.60 und gibt eine Markdown-Tabelle `Schwellwert | Präzision | Vollständigkeit | Geschichten` aus.
- `evaluate.yml`: `workflow_dispatch` mit Auswahl `export` | `score`. Bei `export` wird die CSV als Artefakt hochgeladen. Bei `score` landet die Tabelle in `$GITHUB_STEP_SUMMARY`.

- [ ] **Step 1: Write failing tests:**
  - `test_pairwise_perfect`: identische Zuordnung → (1.0, 1.0)
  - `test_pairwise_overmerge_lowers_precision`: Zwei echte Geschichten {a,b} und {c,d}, vorhergesagt {a,b,c,d} → Präzision 2/6, Vollständigkeit 1.0.
  - `test_pairwise_split_lowers_recall`
  - `test_export_csv_columns_and_bom`: Der Header ist exakt `id;quelle;zeit;ueberschrift;link;geschichte`, die Datei beginnt mit `﻿`.
  - `test_score_reads_labels_ignoring_empty_rows`: Zeilen ohne `geschichte` werden ignoriert.
- [ ] **Step 2:** Run. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `pytest -v`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: Qualitätsmessung der Bündelung`

---

### Task 10: App-Logik (Daten, Einstellungen, Filter)

**Files:**
- Create: `site/js/settings.js`, `site/js/filters.js`, `site/js/format.js`, `site/js/data.js`, `site-tests/settings.test.mjs`, `site-tests/filters.test.mjs`, `site-tests/format.test.mjs`

**Interfaces:**
- Consumes: Schema v1 (Task 7)
- Produces (ES-Module, nur benannte Exporte):
  - `settings.js`: `DEFAULTS = {categories: [], keywords: [], hidden: [], read: []}`; `loadSettings(storage = globalThis.localStorage) -> Settings`; `saveSettings(s, storage = …) -> boolean`; `addKeyword(s, text) -> Settings | null` (getrimmt, Kleinschreibung; leer oder Duplikat → `null`); `markRead(s, storyId)` (höchstens 500 IDs, die ältesten fallen heraus). Jeder Zugriff auf `storage` steht in `try/catch`.
  - `filters.js`:
    - `matchesTerm(item, term) -> boolean`: Treffer, wenn ein Wort aus `item.keywords` oder aus der kleingeschriebenen Überschrift mit `term` **beginnt**.
    - `isHidden(story, hidden) -> boolean`: Ein Eintrag in `hidden` ist entweder `"kat:<kategorie>"` oder ein Stichwort. Ein Treffer bei irgendeinem Item der Geschichte blendet sie aus.
    - `byRegion(stories, tab)` mit `tab ∈ {"alle","inland","ausland"}`
    - `aktuell(data, tab, settings)`: nach Region gefiltert, ohne ausgeblendete, Reihenfolge wie in den Daten.
    - `fuerDich(data, settings) -> Array<{story, reason}>`: Grund `"Stichwort: <wort>"` oder der Kategoriename. Sortiert nach `story.latest` absteigend, ohne ausgeblendete.
    - `itemsByMediaType(story, sources, type)` mit `type ∈ {"alle","oeffentlich-rechtlich","zeitung","international"}`
  - `format.js`: `relativeTime(iso, now) -> string`: < 60 s „gerade eben“; < 60 Min. „vor N Min.“; < 24 Std. „vor N Std.“; < 48 Std. „gestern“; sonst „vor N Tagen“; `CATEGORY_LABELS`, `MEDIA_LABELS`.
  - `data.js`: `loadData(fetchFn = fetch) -> Promise<{data, stale: boolean} | {error: string}>`. Lädt `data/stories.json` (`cache: "no-cache"`). Bei Fehler gibt es `{error: "Keine Verbindung und noch keine gespeicherten Nachrichten."}`. Den Fall mit Cache deckt der Service Worker aus Task 12 ab.

- [ ] **Step 1: Write failing tests** (`node:test` + `node:assert`):
  - `settings`: `loads defaults when storage throws` (Storage-Attrappe wirft bei `getItem` und `setItem` → Standardwerte, `saveSettings` liefert `false`); `addKeyword trims, lowercases, rejects empty and duplicates` (`"  Wasserstoff "` → `"wasserstoff"`; `"   "` → `null`); `markRead caps at 500`
  - `filters`: `prefix match with umlauts` (Stichwort `"ärzte"` findet das Keyword `"ärztekammer"`; `"wasserstoff"` findet die Überschrift „Neues Wasserstoffnetz“); `hidden applies in aktuell and fuerDich`; `hidden category`; `region tabs`; `fuerDich gives reason and sorts by latest`; `media type filter`
  - `format`: Grenzfälle von `relativeTime` (59 s, 59 Min, 23 Std, gestern)
- [ ] **Step 2:** Run `node --test site-tests/`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `node --test site-tests/`. Erwartet: PASS.
- [ ] **Step 5: Commit** `feat: App-Logik für Filter und Einstellungen`

---

### Task 11: App-Oberfläche (vier Bildschirme)

**Files:**
- Create: `site/index.html`, `site/app.css`, `site/js/views.js`, `site/js/app.js`, `site-tests/views.test.mjs`, `site/data/stories.json` (Beispieldaten nach Schema v1 mit dem Hinweis „Beispiel“ in den Titeln, damit die Seite vor dem ersten Lauf etwas zeigt)

**Interfaces:**
- Consumes: Task 10 (alle Exporte)
- Produces:
  - Routen (Hash): `#aktuell/alle` (Start), `#aktuell/inland`, `#aktuell/ausland`, `#story/<id>`, `#fuerdich`, `#interessen`
  - `views.js` exportiert reine Funktionen, die HTML-Strings liefern. Alle Fremdtexte laufen durch `escapeHtml()`. Funktionen: `escapeHtml(s)`, `storyCard(story, sources, {read, now})`, `aktuellView(stories, tab, ctx)`, `storyView(story, sources, mediaType, ctx)`, `fuerDichView(entries, ctx)`, `interessenView(settings)`
  - `app.js`: Router, Event-Delegation, Speichern der Einstellungen. Der Tipp auf die Überschrift einer Karte öffnet `item.link` in einem neuen Tab (`rel="noopener"`) und markiert die Geschichte als gelesen.

Aussehen und Aufbau richten sich nach den Handy-Entwürfen (Link oben): Farben `#16181D` (Text), `#5B616E` (Nebentext), `#1F5BD8` (Akzent), `#F6F7F9` (Feed-Hintergrund); Schriften Source Serif 4 (Überschriften) und Inter, beide über Google Fonts; Karten mit 14 px Radius; Vorschaubild 76 × 76 px rechts, nur bei vorhandenem `image`; Touch-Ziele ≥ 44 px. Zusätzlich zu den Entwürfen:
- Plus-Markierung: kleines Badge „Plus“ neben dem Quellennamen
- Gelesene Karten mit `opacity: .55`
- Abschnitt „Themen ausblenden“ in Interessen, mit eigenem Eingabefeld (wie bei Stichworten) und Schaltern „Kategorie ausblenden“
- Leerer Zustand in „Für dich“: „Wähle unter Interessen Kategorien oder Stichworte.“

- [ ] **Step 1: Write failing tests** in `site-tests/views.test.mjs`:
  - `escapes html in titles`: Der Titel `<img onerror=x>` erscheint escaped.
  - `card shows up to two further sources and the count link`: Bei 5 Quellen zeigt die Karte 2 weitere und den Link „Komplette Berichterstattung · 5 Quellen“.
  - `card without image has no thumb element`
  - `plus badge and read class`
  - `aktuell tabs mark the active tab with aria-current`
- [ ] **Step 2:** Run `node --test site-tests/`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `node --test site-tests/`. Erwartet: PASS. Starte dann `python3 -m http.server -d site 8000` und mache mit Playwright Screenshots bei 390 × 844 von `#aktuell/alle`, `#story/<id>`, `#fuerdich` und `#interessen`. Prüfe sie auf Überlauf und abgeschnittenen Text.
- [ ] **Step 5: Commit** `feat: App-Oberfläche`

---

### Task 12: Offline, Installierbarkeit und Aktualitätsanzeige

**Files:**
- Create: `site/sw.js`, `site/sw-strategy.js`, `site/manifest.webmanifest`, `site/icon.svg`, `site-tests/sw.test.mjs`
- Modify: `site/index.html` (Manifest, Service-Worker-Registrierung), `site/js/app.js` (Anzeige „Stand“ und offline), `docs/ANLEITUNG.md` (Abschnitt Installieren)

**Interfaces:**
- Consumes: `relativeTime` (Task 10), `loadData` (Task 10)
- Produces:
  - `sw.js`: `CACHE = "app-v1"`. Die App-Hülle (index.html, app.css, js/*.js, icon.svg, manifest) wird beim `install` vorab gespeichert und per Cache-First ausgeliefert. `data/stories.json` läuft Network-First mit Rückfall auf den Cache. Bei `activate` werden alte Caches gelöscht.
  - `site/sw-strategy.js` (klassisches Skript, kein Modul) definiert `function strategyFor(url, scope) -> "cache-first" | "network-first" | "network"`. Dabei gilt: gleiche Herkunft und Pfad endet auf `data/stories.json` → network-first; andere Dateien gleicher Herkunft → cache-first; fremde Herkunft → network. `sw.js` lädt die Datei mit `importScripts("sw-strategy.js")`, der Test liest sie mit `vm.runInNewContext` ein.
  - Anzeige unter dem Datum: „Stand: vor X Min.“ aus `generated_at`. Ist `generated_at` älter als 2 Stunden, erscheint der Zusatz „– Aktualisierung hängt, siehe Anleitung“. Bei `navigator.onLine === false` erscheint das Banner „Offline – du siehst den zuletzt geladenen Stand.“
  - Manifest: `name` „Nachrichten“, `display: standalone`, `start_url: "./#aktuell/alle"`, `lang: "de"`, Icon als SVG.

- [ ] **Step 1: Write failing test** `site-tests/sw.test.mjs`: Prüft `strategyFor`: `.../data/stories.json` → network-first, `.../js/app.js` → cache-first, fremde Bild-URLs → network.
- [ ] **Step 2:** Run `node --test site-tests/`. Erwartet: FAIL.
- [ ] **Step 3:** Implementiere.
- [ ] **Step 4:** Run `node --test site-tests/` und `pytest -q`. Erwartet: alle PASS. Danach in Playwright: Seite laden, `context.setOffline(true)`, neu laden → Die Karten sind sichtbar und das Offline-Banner erscheint.
- [ ] **Step 5: Commit** `feat: Offline-Modus und Installierbarkeit`
