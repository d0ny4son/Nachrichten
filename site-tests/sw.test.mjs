import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const code = readFileSync(new URL("../site/sw-strategy.js", import.meta.url), "utf8");
const sandbox = { URL, setTimeout, clearTimeout };
vm.runInNewContext(code, sandbox);
const { strategyFor } = sandbox;
const scope = "https://name.github.io/nachrichten/";

test("data file is network-first", () => {
  assert.equal(strategyFor("https://name.github.io/nachrichten/data/stories.json", scope), "network-first");
  assert.equal(strategyFor("https://name.github.io/nachrichten/data/stories.json?x=1", scope), "network-first");
});

test("app shell is cache-first", () => {
  assert.equal(strategyFor("https://name.github.io/nachrichten/js/app.js", scope), "cache-first");
  assert.equal(strategyFor("https://name.github.io/nachrichten/", scope), "cache-first");
});

test("foreign urls go to the network", () => {
  assert.equal(strategyFor("https://img.example.org/a.jpg", scope), "network");
  assert.equal(strategyFor("https://fonts.googleapis.com/css2?family=Inter", scope), "network");
});

test("status and state files are not cached", () => {
  assert.equal(strategyFor("https://name.github.io/nachrichten/data/status.json", scope), "network");
});

test("withTimeout rejects slow promises and passes fast ones", async () => {
  const { withTimeout } = sandbox;
  await assert.rejects(withTimeout(new Promise(() => {}), 10));
  assert.equal(await withTimeout(Promise.resolve(42), 1000), 42);
});
