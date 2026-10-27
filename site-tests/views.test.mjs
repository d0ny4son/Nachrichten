import { test } from "node:test";
import assert from "node:assert/strict";
import { aktuellView, escapeHtml, fuerDichView, interessenView, searchResults, storyCard, storyView } from "../site/js/views.js";
import { DEFAULTS } from "../site/js/settings.js";
import { DATA, NOW } from "./fixture.mjs";

const ctx = { now: NOW, read: [], sources: DATA.sources };

function bigStory() {
  const ids = ["tagesschau", "zeit", "dw", "x", "y"];
  const sources = { ...DATA.sources, x: { name: "X", media_type: "zeitung" }, y: { name: "Y", media_type: "zeitung" } };
  const items = ids.map((s, i) => ({ id: `i${i}`, source: s, title: `Titel ${i}`, link: `https://e.org/${i}`,
    published: "2026-10-27T10:00:00Z", image: null, plus: false, keywords: [] }));
  return { story: { id: "big", score: 5, region: "inland", categories: [], latest: "2026-10-27T10:00:00Z", lead: "i0", items }, sources };
}

test("escapes html in titles", () => {
  assert.equal(escapeHtml(`<img onerror="x">&'`), "&lt;img onerror=&quot;x&quot;&gt;&amp;&#39;");
  const s = structuredClone(DATA.stories[1]);
  s.items[0].title = "<img onerror=x>";
  const html = storyCard(s, DATA.sources, ctx);
  assert.ok(!html.includes("<img onerror"));
  assert.ok(html.includes("&lt;img onerror=x&gt;"));
});

test("card shows all further sources in a swipe strip and the count link", () => {
  const { story, sources } = bigStory();
  const html = storyCard(story, sources, { ...ctx, sources });
  assert.match(html, /<div class="strip" role="list" aria-label="Weitere Quellen">/);
  assert.equal((html.match(/class="relcard"/g) || []).length, 4);
  assert.ok(html.includes("Komplette Berichterstattung · 5 Quellen"));
  assert.ok(html.includes('href="#story/big"'));
});

test("single-source card has no full-coverage link", () => {
  const html = storyCard(DATA.stories[1], DATA.sources, ctx);
  assert.ok(!html.includes("Komplette Berichterstattung"));
});

test("card without image has no thumb element", () => {
  const s = DATA.stories[1];
  assert.ok(!storyCard(s, DATA.sources, ctx).includes('class="thumb"'));
  const withImg = structuredClone(s);
  withImg.items[0].image = "https://img.example.org/a.jpg";
  assert.ok(storyCard(withImg, DATA.sources, ctx).includes('class="thumb"'));
});

test("plus badge and read class", () => {
  const s = structuredClone(DATA.stories[1]);
  s.items[0].plus = true;
  const html = storyCard(s, DATA.sources, { ...ctx, read: ["s2"] });
  assert.ok(html.includes('class="plus"'));
  assert.ok(html.includes('class="card"'));
  assert.ok(!html.includes("card read"));
  assert.match(html, /<span class="readmark" title="Gelesen"><svg[^>]*role="img" aria-label="Gelesen"/);
});

test("unread card has no glasses mark", () => {
  assert.ok(!storyCard(DATA.stories[1], DATA.sources, ctx).includes("readmark"));
});

test("single-source card has no strip", () => {
  assert.ok(!storyCard(DATA.stories[1], DATA.sources, ctx).includes('class="strip"'));
});

test("aktuell tabs mark the active tab with aria-current", () => {
  const html = aktuellView(DATA.stories, "inland", ctx);
  assert.match(html, /<a class="tab on" href="#aktuell\/inland" aria-current="page">Inland<\/a>/);
  assert.match(html, /<a class="tab" href="#aktuell\/ausland">Ausland<\/a>/);
});

test("story view filters by media type", () => {
  const html = storyView(DATA.stories[0], DATA.sources, "zeitung", ctx);
  assert.ok(html.includes("Haushaltsdebatte im Bundestag"));
  assert.ok(html.includes('href="https://example.org/a2"'));
  assert.ok(!html.includes('href="https://example.org/a1"'));
  assert.match(html, /class="chip on"[^>]*>Zeitungen</);
});

test("fuer dich empty state and reason", () => {
  assert.ok(fuerDichView([], ctx).includes("Wähle unter Interessen Kategorien oder Stichworte."));
  const html = fuerDichView([{ story: DATA.stories[0], reason: "Stichwort: haushalt" }], ctx);
  assert.ok(html.includes("Stichwort: haushalt"));
});

test("interessen view shows settings", () => {
  const s = { ...DEFAULTS, categories: ["sport"], keywords: ["wasserstoff"], hidden: ["fußball", "kat:kultur"] };
  const html = interessenView(s);
  assert.match(html, /value="sport"[^>]*checked/);
  assert.ok(html.includes("wasserstoff"));
  assert.ok(html.includes("fußball"));
  assert.match(html, /data-hide-cat="kultur"[^>]*checked/);
});

function many(n) {
  return Array.from({ length: n }, (_, i) => ({ ...structuredClone(DATA.stories[1]), id: `m${i}` }));
}

test("aktuell shows only the limit and a more button", () => {
  const html = aktuellView(many(35), "alle", { ...ctx, limit: 30 });
  assert.equal((html.match(/<article/g) || []).length, 30);
  assert.match(html, /<button class="more-btn" data-more>Weitere Meldungen<\/button>/);
});

test("no more button when everything fits", () => {
  const html = aktuellView(many(12), "alle", { ...ctx, limit: 30 });
  assert.equal((html.match(/<article/g) || []).length, 12);
  assert.ok(!html.includes("data-more"));
});

test("source icon from the article's own site with initials fallback", () => {
  const html = storyCard(DATA.stories[1], DATA.sources, ctx);
  assert.match(html, /<img class="favicon" src="https:\/\/example\.org\/favicon\.ico"/);
  assert.ok(html.includes('class="logo"'));
  // erst nach dem Laden sichtbar, sonst verdeckt ein leeres Kästchen die Buchstaben
  assert.ok(html.includes(`onload="this.classList.add('ok')"`));
});

test("no source icon for non-http links", () => {
  const s = structuredClone(DATA.stories[1]);
  s.items[0].link = "javascript:alert(1)";
  assert.ok(!storyCard(s, DATA.sources, ctx).includes("favicon"));
});

test("interessen view offers theme choice with current one checked", () => {
  const html = interessenView({ ...DEFAULTS, theme: "dark" });
  assert.match(html, /name="theme" value="dark" checked/);
  assert.match(html, /name="theme" value="system"(?! checked)/);
});

const gItem = { id: "g1", source: "themen", publisher: "Handelsblatt", site: "https://www.handelsblatt.com",
  title: "Neues Wasserstoffnetz startet", link: "https://news.google.com/x", published: "2026-10-27T10:45:00Z",
  image: null, plus: false, keywords: [] };
const gStory = { id: "t1", score: 1, region: null, categories: [], latest: "2026-10-27T10:45:00Z", lead: "g1", topic_only: true, items: [gItem] };
const tctx = { ...ctx, sources: { ...DATA.sources, themen: { name: "Themen-Suche", media_type: "themen" } } };

test("topic items show their real publisher and its icon", () => {
  const html = storyCard(gStory, tctx.sources, tctx);
  assert.ok(html.includes(">Handelsblatt<"));
  assert.ok(html.includes('src="https://www.handelsblatt.com/favicon.ico"'));
  assert.ok(!html.includes("Themen-Suche"));
});

test("aktuell has a search field", () => {
  assert.match(aktuellView([], "alle", ctx), /<form class="search" role="search"[^>]*>.*<input id="q"/s);
});

test("search results show count and follow button", () => {
  const html = searchResults([gStory], "Wasserstoff", { ...tctx, keywords: [] });
  assert.ok(html.includes("1 Treffer für „Wasserstoff“"));
  assert.match(html, /<button class="follow" data-follow="wasserstoff">Thema folgen<\/button>/);
  assert.ok(!searchResults([gStory], "Wasserstoff", { ...tctx, keywords: ["wasserstoff"] }).includes("data-follow"));
});

test("search without hits explains the topic list", () => {
  const html = searchResults([], "Elektrolyse", { ...tctx, keywords: [] });
  assert.ok(html.includes("Keine Treffer für „Elektrolyse“"));
  assert.ok(html.includes("themen:"));
});

test("interessen shows feedback after adding a keyword", () => {
  assert.ok(interessenView(DEFAULTS, { term: "klima", hits: 12 }).includes("„klima“: gerade 12 Meldungen"));
  assert.ok(interessenView(DEFAULTS, { term: "elektrolyse", hits: 0 }).includes("themen:"));
});

test("feedback knows when a topic is already in the topic list", () => {
  const html = interessenView(DEFAULTS, { term: "elektrolyse", hits: 0, listed: true });
  assert.ok(html.includes("steht schon in der Themen-Liste"));
  assert.ok(!html.includes("config/sources.yaml"));
});

test("top rubric: nav says Top and list has a heading", () => {
  const html = aktuellView(DATA.stories, "alle", ctx);
  assert.match(html, /<span class="pill">.*<\/span>Top<\/a>/s);
  assert.ok(!html.includes(">Aktuell</a>"));
  assert.ok(html.includes('<h2 class="sec">Top-Meldungen</h2>'));
  assert.ok(aktuellView(DATA.stories, "inland", ctx).includes('<h2 class="sec">Top-Meldungen Inland</h2>'));
});
