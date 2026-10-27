// Einstieg der App: Daten laden, Route auswerten, Bildschirm zeichnen.
import { loadData } from "./data.js";
import { aktuell, fuerDich, searchStories } from "./filters.js";
import { addHidden, addKeyword, loadSettings, markRead, removeFrom, saveSettings, toggle } from "./settings.js";
import { aktuellView, escapeHtml, fuerDichView, interessenView, searchResults, storyView } from "./views.js";

const HANG_MS = 2 * 60 * 60 * 1000;
const PAGE = 30; // Top-Meldungen pro Seite, „Weitere Meldungen“ zeigt jeweils 30 mehr
let limit = PAGE;
let query = ""; // Suchbegriff in „Aktuell“
let info = null; // Rückmeldung nach neuem Stichwort
const root = document.getElementById("app");
let settings = loadSettings();
let loaded = null; // {data, stale} | {error}

function route() {
  const [screen = "aktuell", a = "", b = ""] = location.hash.replace(/^#/, "").split("/");
  return { screen, a: decodeURIComponent(a), b: decodeURIComponent(b) };
}

function ctx() {
  const now = new Date();
  const data = loaded?.data;
  const gen = data?.generated_at;
  return {
    now,
    read: settings.read,
    sources: data?.sources || {},
    icons: data?.icons || {},
    generatedAt: gen,
    hangs: gen ? now - new Date(gen) > HANG_MS : false,
    offline: navigator.onLine === false || Boolean(loaded?.stale),
  };
}

function render() {
  const r = route();
  if (r.screen === "interessen") {
    root.innerHTML = interessenView(settings, info);
    return;
  }
  if (!loaded) return;
  if (loaded.error) {
    root.innerHTML = `<p class="empty">${escapeHtml(loaded.error)}</p>`;
    return;
  }
  const data = loaded.data;
  const c = ctx();
  if (r.screen === "story") {
    const story = data.stories.find((s) => s.id === r.a);
    root.innerHTML = story
      ? storyView(story, data.sources, r.b || "alle", c)
      : '<p class="empty">Diese Geschichte ist nicht mehr aktuell. <a href="#aktuell/alle">Zur Übersicht</a></p>';
  } else if (r.screen === "fuerdich") {
    root.innerHTML = fuerDichView(fuerDich(data, settings), c);
  } else {
    const tab = ["alle", "inland", "ausland"].includes(r.a) ? r.a : "alle";
    root.innerHTML = aktuellView(aktuell(data, tab, settings), tab, { ...c, limit, query });
    if (query.trim()) renderSearch();
  }
}

// Nur die Trefferliste neu zeichnen, damit das Suchfeld beim Tippen den Fokus behält
function renderSearch() {
  const feed = root.querySelector(".feed");
  if (!feed || !loaded?.data) return;
  if (!query.trim()) {
    render();
    return;
  }
  const hits = searchStories(loaded.data, query, settings);
  feed.innerHTML = searchResults(hits, query, { ...ctx(), keywords: settings.keywords });
}

function applyTheme() {
  const t = settings.theme;
  if (t === "light" || t === "dark") document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
}

function update(next) {
  if (!next) return false;
  settings = next;
  saveSettings(settings);
  return true;
}

root.addEventListener("click", (e) => {
  const link = e.target.closest("[data-read]");
  if (link) {
    update(markRead(settings, link.dataset.read));
    // Ausgrauen erst nach dem Öffnen, damit der Tab-Wechsel nicht flackert.
    setTimeout(render, 300);
    return;
  }
  const follow = e.target.closest("[data-follow]");
  if (follow) {
    update(addKeyword(settings, follow.dataset.follow));
    renderSearch();
    return;
  }
  if (e.target.closest("[data-more]")) {
    limit += PAGE;
    render();
    return;
  }
  const rm = e.target.closest("[data-remove]");
  if (rm) {
    update(removeFrom(settings, rm.dataset.remove, rm.dataset.value));
    render();
  }
});

root.addEventListener("change", (e) => {
  const t = e.target;
  if (t.matches("[data-toggle-cat]")) update(toggle(settings, "categories", t.value));
  else if (t.matches("[data-hide-cat]")) update(toggle(settings, "hidden", `kat:${t.dataset.hideCat}`));
  else if (t.matches('input[name="theme"]')) {
    update({ ...settings, theme: t.value });
    applyTheme();
  }
});

root.addEventListener("submit", (e) => {
  const form = e.target.closest("[data-add]");
  if (!form) return;
  e.preventDefault();
  const value = form.elements.value.value;
  const isKeyword = form.dataset.add === "keywords";
  const next = isKeyword ? addKeyword(settings, value) : addHidden(settings, value);
  if (isKeyword && next && loaded?.data) {
    const term = value.trim().toLowerCase();
    const listed = (loaded.data.topics || []).some((t) => t.toLowerCase() === term);
    info = { term, hits: searchStories(loaded.data, value, settings).length, listed };
  }
  if (update(next)) {
    render();
    document.getElementById(`in-${form.dataset.add}`)?.focus();
  }
});

root.addEventListener("input", (e) => {
  if (e.target.id === "q") {
    query = e.target.value;
    renderSearch();
  }
});

window.addEventListener("hashchange", () => {
  limit = PAGE;
  info = null;
  if (!location.hash.startsWith("#aktuell")) query = "";
  render();
  window.scrollTo(0, 0);
});
window.addEventListener("online", render);
window.addEventListener("offline", render);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}

if (!location.hash) history.replaceState(null, "", "#aktuell/alle");
applyTheme();
render();
loadData().then((r) => {
  loaded = r;
  render();
});
