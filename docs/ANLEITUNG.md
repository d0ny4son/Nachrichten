# Anleitung: Nachrichten-App einrichten und pflegen

Alles geht im Browser, ohne Programmieren. Du brauchst nur ein kostenloses GitHub-Konto.

## 1. Einmalig einrichten

1. **GitHub-Konto anlegen:** auf [github.com](https://github.com) „Sign up“.
2. **Projekt anlegen:** oben rechts „+“ › „New repository“. Name z. B. `nachrichten`, Sichtbarkeit **Public** (nur dann ist alles kostenlos), „Create repository“.
3. **Dateien hochladen:** im neuen Projekt „uploading an existing file“ anklicken, den kompletten Inhalt des Projektordners hineinziehen (inklusive des Ordners `.github`) und „Commit changes“.
   *Tipp:* Der Ordner `.github` ist auf manchen Rechnern versteckt. Unter macOS im Finder `Cmd + Umschalt + .` drücken, unter Windows im Explorer „Ansicht › Ausgeblendete Elemente“.
4. **Schreibrechte für die Abläufe:** „Settings“ › „Actions“ › „General“ › ganz unten „Workflow permissions“ › **Read and write permissions** › „Save“.
5. **Seite einschalten:** „Settings“ › „Pages“ › bei „Source“ **GitHub Actions** wählen.
6. **Ersten Lauf starten:** Reiter „Actions“ › links „collect“ › rechts „Run workflow“ › „Run workflow“. Nach 1–3 Minuten ist der Lauf grün.
7. **App öffnen:** „Settings“ › „Pages“ zeigt oben den Link, z. B. `https://deinname.github.io/nachrichten/`.

Ab jetzt aktualisiert sich die App alle 20 Minuten von selbst.

## 2. Auf dem Handy installieren

- **iPhone (Safari):** Link öffnen › Teilen-Symbol › „Zum Home-Bildschirm“.
- **Android (Chrome):** Link öffnen › Menü (⋮) › „App installieren“ bzw. „Zum Startbildschirm hinzufügen“.

Danach startet die App wie eine normale App und zeigt auch ohne Internet den zuletzt geladenen Stand.

## 3. Quellen ändern

1. Im Projekt die Datei `config/sources.yaml` öffnen.
2. Oben rechts das **Stift-Symbol** anklicken, ändern, unten „Commit changes“.
3. Reiter „Actions“ › Ablauf „validate“: **grüner Haken** = alles in Ordnung. **Rotes X** = anklicken, der Fehler steht dort auf Deutsch (z. B. „Quelle ‚taz‘: Es ist kein Feed eingetragen.“).

Eine Quelle vorübergehend abschalten: die ganze Quelle löschen oder jede Zeile mit `#` am Anfang auskommentieren.

## 4. Prüfen, ob alle Quellen funktionieren

Die Datei `site/data/status.json` im Projekt öffnen. Für jede Quelle steht dort:

- `"ok": true` – alles gut
- `"ok": false` – unter `"errors"` steht, welche Adresse nicht geht (z. B. `HTTP 404` = Adresse gibt es nicht mehr)
- `"items"`, `"with_image"`, `"plus"` – Anzahl Meldungen, davon mit Bild, davon Bezahlartikel

Adressen mit `# ungeprüft` in `sources.yaml` waren beim Bau nicht überprüfbar. Ist eine davon kaputt: Auf der Seite des Mediums nach „RSS“ suchen und die neue Adresse eintragen, oder die Zeile löschen.

## 5. Bündelung prüfen (Qualitätsmessung)

So findest du heraus, ob die App Meldungen richtig zu Geschichten zusammenfasst.

1. **Testtabelle erzeugen:** „Actions“ › „evaluate“ › „Run workflow“ › Schritt **export** › „Run workflow“. Danach liegt im Projekt `evaluation/testset.csv`.
2. **Herunterladen:** Datei anklicken › Download-Symbol. Mit Excel oder LibreOffice öffnen (Trennzeichen: Semikolon).
3. **Ausfüllen:** In der Spalte `geschichte` jeder Meldung einen kurzen Namen für ihr Ereignis geben, z. B. `haushalt`. Meldungen zum **selben Ereignis** bekommen **denselben** Namen. Regel: ein Ereignis, nicht ein ganzes Thema. Die Fortsetzung am nächsten Tag bekommt einen neuen Namen. Zeilen, bei denen du unsicher bist, einfach leer lassen.
4. **Speichern** als CSV (Semikolon getrennt, UTF-8) unter dem Namen `labelled.csv`.
5. **Hochladen:** im Projekt Ordner `evaluation` öffnen › „Add file“ › „Upload files“ › „Commit changes“.
6. **Auswerten:** „Actions“ › „evaluate“ › Schritt **score**. Im Ergebnis steht eine Tabelle:
   - **Präzision:** Wie oft liegt die App richtig, wenn sie zwei Meldungen zusammenlegt? Soll möglichst hoch sein.
   - **Vollständigkeit:** Wie viele zusammengehörige Meldungen findet sie?
7. **Schwellwert anpassen:** den Wert mit hoher Präzision und noch ordentlicher Vollständigkeit in `config/sources.yaml` bei `threshold:` eintragen.

## 6. Wenn die App „Aktualisierung hängt“ zeigt

GitHub pausiert Zeitpläne in seltenen Fällen (z. B. nach 60 Tagen ohne Änderungen am Projekt). Der Ablauf „keepalive“ schaltet ihn monatlich wieder ein. Falls es trotzdem hängt:

1. Reiter „Actions“ › links „collect“.
2. Erscheint ein gelber Hinweis „This scheduled workflow is disabled…“: **Enable workflow** anklicken.
3. Sonst den letzten Lauf anklicken und die rote Meldung lesen.
