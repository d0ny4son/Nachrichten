import { test } from "node:test";
import assert from "node:assert/strict";
import { relativeTime } from "../site/js/format.js";
import { loadData } from "../site/js/data.js";

const now = new Date("2026-10-27T11:00:00Z");
const ago = (sec) => new Date(now.getTime() - sec * 1000).toISOString();

test("relativeTime boundaries", () => {
  assert.equal(relativeTime(ago(59), now), "gerade eben");
  assert.equal(relativeTime(ago(60), now), "vor 1 Min.");
  assert.equal(relativeTime(ago(59 * 60), now), "vor 59 Min.");
  assert.equal(relativeTime(ago(60 * 60), now), "vor 1 Std.");
  assert.equal(relativeTime(ago(23 * 3600 + 59 * 60), now), "vor 23 Std.");
  assert.equal(relativeTime(ago(24 * 3600), now), "gestern");
  assert.equal(relativeTime(ago(48 * 3600), now), "vor 2 Tagen");
  assert.equal(relativeTime(ago(-120), now), "gerade eben");
});

test("loadData returns data", async () => {
  const fake = async () => ({ ok: true, headers: { get: () => null }, json: async () => ({ version: 1, stories: [] }) });
  const r = await loadData(fake);
  assert.deepEqual(r.data.stories, []);
  assert.equal(r.stale, false);
});

test("loadData reports error without throwing", async () => {
  const fake = async () => { throw new TypeError("offline"); };
  const r = await loadData(fake);
  assert.equal(r.error, "Keine Verbindung und noch keine gespeicherten Nachrichten.");
});
