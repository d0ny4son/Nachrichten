import { test } from "node:test";
import assert from "node:assert/strict";
import { DEFAULTS, addHidden, addKeyword, loadSettings, markRead, saveSettings } from "../site/js/settings.js";

const broken = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };

function memory() {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) };
}

test("loads defaults when storage throws", () => {
  assert.deepEqual(loadSettings(broken), DEFAULTS);
  assert.equal(saveSettings(loadSettings(broken), broken), false);
});

test("loads defaults when storage is missing", () => {
  assert.deepEqual(loadSettings(undefined), DEFAULTS);
});

test("ignores corrupt stored json", () => {
  const s = memory();
  s.setItem("nachrichten.settings", "{kaputt");
  assert.deepEqual(loadSettings(s), DEFAULTS);
});

test("roundtrip through storage", () => {
  const s = memory();
  const v = { ...DEFAULTS, keywords: ["wasserstoff"] };
  assert.equal(saveSettings(v, s), true);
  assert.deepEqual(loadSettings(s).keywords, ["wasserstoff"]);
});

test("addKeyword trims, lowercases, rejects empty and duplicates", () => {
  const a = addKeyword(DEFAULTS, "  Wasserstoff ");
  assert.deepEqual(a.keywords, ["wasserstoff"]);
  assert.equal(addKeyword(a, "WASSERSTOFF"), null);
  assert.equal(addKeyword(a, "   "), null);
  assert.deepEqual(DEFAULTS.keywords, []);
});

test("addHidden works like addKeyword", () => {
  const a = addHidden(DEFAULTS, " Fußball ");
  assert.deepEqual(a.hidden, ["fußball"]);
  assert.equal(addHidden(a, ""), null);
});

test("markRead caps at 500", () => {
  let s = DEFAULTS;
  for (let i = 0; i < 510; i++) s = markRead(s, `s${i}`);
  assert.equal(s.read.length, 500);
  assert.equal(s.read[0], "s10");
  assert.equal(markRead(s, "s509").read.length, 500);
});

test("default storage that throws on access does not crash", () => {
  const desc = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, get() { throw new Error("SecurityError"); } });
  try {
    assert.deepEqual(loadSettings(), DEFAULTS);
    assert.equal(saveSettings(DEFAULTS), false);
  } finally {
    if (desc) Object.defineProperty(globalThis, "localStorage", desc);
    else delete globalThis.localStorage;
  }
});

test("theme defaults to system and rejects unknown values", () => {
  assert.equal(DEFAULTS.theme, "system");
  const s = memory();
  s.setItem("nachrichten.settings", JSON.stringify({ theme: "lila" }));
  assert.equal(loadSettings(s).theme, "system");
  s.setItem("nachrichten.settings", JSON.stringify({ theme: "dark" }));
  assert.equal(loadSettings(s).theme, "dark");
});
