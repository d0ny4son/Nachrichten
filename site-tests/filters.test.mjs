import { test } from "node:test";
import assert from "node:assert/strict";
import { aktuell, byRegion, fuerDich, isHidden, itemsByMediaType, matchesTerm, searchStories } from "../site/js/filters.js";
import { DEFAULTS } from "../site/js/settings.js";
import { DATA } from "./fixture.mjs";

const story = (id) => DATA.stories.find((s) => s.id === id);

test("prefix match with umlauts", () => {
  assert.equal(matchesTerm(story("s3").items[0], "ärzte"), true);
  assert.equal(matchesTerm(story("s2").items[0], "wasserstoff"), true);
  assert.equal(matchesTerm({ title: "Neues Wasserstoffnetz", keywords: [] }, "wasserstoff"), true);
  assert.equal(matchesTerm(story("s1").items[0], "stoff"), false);
});

test("region tabs", () => {
  assert.deepEqual(byRegion(DATA.stories, "alle").map((s) => s.id), ["s1", "s2", "s3"]);
  assert.deepEqual(byRegion(DATA.stories, "inland").map((s) => s.id), ["s1"]);
  assert.deepEqual(byRegion(DATA.stories, "ausland").map((s) => s.id), ["s2"]);
});

test("hidden applies in aktuell and fuerDich", () => {
  const s = { ...DEFAULTS, keywords: ["haushalt"], hidden: ["fußball"], categories: ["sport"] };
  assert.deepEqual(aktuell(DATA, "alle", s).map((x) => x.id), ["s1", "s2"]);
  assert.deepEqual(fuerDich(DATA, s).map((e) => e.story.id), ["s1"]);
});

test("hidden category", () => {
  assert.equal(isHidden(story("s3"), ["kat:sport"]), true);
  assert.equal(isHidden(story("s1"), ["kat:sport"]), false);
});

test("fuerDich gives reason and sorts by latest", () => {
  const s = { ...DEFAULTS, keywords: ["wasserstoff"], categories: ["wissenschaft", "wirtschaft"] };
  const out = fuerDich(DATA, s);
  assert.deepEqual(out.map((e) => e.story.id), ["s3", "s1", "s2"]);
  assert.deepEqual(out.map((e) => e.reason), ["Wissenschaft", "Wirtschaft", "Stichwort: wasserstoff"]);
});

test("fuerDich empty without interests", () => {
  assert.deepEqual(fuerDich(DATA, DEFAULTS), []);
});

test("media type filter", () => {
  const s = story("s1");
  assert.deepEqual(itemsByMediaType(s, DATA.sources, "alle").map((i) => i.id), ["a1", "a2"]);
  assert.deepEqual(itemsByMediaType(s, DATA.sources, "zeitung").map((i) => i.id), ["a2"]);
  assert.deepEqual(itemsByMediaType(s, DATA.sources, "international"), []);
});

test("multi-word and hyphenated terms match all parts", () => {
  const scholz = { title: "Olaf Scholz besucht Paris", keywords: [] };
  const other = { title: "Scholz-Biografie erscheint", keywords: [] };
  assert.equal(matchesTerm(scholz, "Olaf Scholz"), true);
  assert.equal(matchesTerm(other, "Olaf Scholz"), false);
  assert.equal(matchesTerm({ title: "Nahost-Konflikt eskaliert", keywords: ["nahost", "konflikt"] }, "nahost-konflikt"), true);
  assert.equal(matchesTerm({ title: "Neues E-Auto vorgestellt", keywords: ["auto"] }, "E-Auto"), true);
});

const topicStory = {
  id: "t1", score: 1, region: null, categories: [], latest: "2026-10-27T10:45:00Z", lead: "g1", topic_only: true,
  items: [{ id: "g1", source: "themen", publisher: "Handelsblatt", site: "https://www.handelsblatt.com",
    title: "Neues Wasserstoffnetz startet", link: "https://news.google.com/x", published: "2026-10-27T10:45:00Z",
    image: null, plus: false, keywords: ["neues", "startet", "wasserstoffnetz"] }],
};
const withTopic = { ...DATA, stories: [...DATA.stories, topicStory] };

test("aktuell leaves out topic-only stories", () => {
  assert.ok(!aktuell(withTopic, "alle", DEFAULTS).some((s) => s.id === "t1"));
});

test("fuerDich includes topic-only stories", () => {
  const out = fuerDich(withTopic, { ...DEFAULTS, keywords: ["wasserstoff"] });
  assert.deepEqual(out.map((e) => e.story.id), ["t1", "s2"]);
});

test("search finds across everything, newest first, respects hidden", () => {
  assert.deepEqual(searchStories(withTopic, "wasserstoff", DEFAULTS).map((s) => s.id), ["t1", "s2"]);
  assert.deepEqual(searchStories(withTopic, "wasserstoff", { ...DEFAULTS, hidden: ["europa"] }).map((s) => s.id), ["t1"]);
  assert.deepEqual(searchStories(withTopic, "   ", DEFAULTS), []);
});
