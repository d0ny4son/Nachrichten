// Reine Funktionen, die HTML-Strings erzeugen. Alle Fremdtexte laufen durch escapeHtml().
import { CATEGORY_LABELS, MEDIA_LABELS, relativeTime } from "./format.js";
import { itemsByMediaType } from "./filters.js";

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);

const safeUrl = (u) => (/^https?:\/\//i.test(String(u || "")) ? escapeHtml(u) : "#");

const ICONS = {
  aktuell: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h10M7 13h10M7 17h6"/>',
  fuerdich: '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z"/>',
  interessen: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  back: '<path d="M15 5l-7 7 7 7"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  glasses: '<circle cx="6.5" cy="14" r="3.5"/><circle cx="17.5" cy="14" r="3.5"/><path d="M10 14c1.2-1 2.8-1 4 0M3 14l1.5-6h2M21 14l-1.5-6h-2"/>',
};
const MAX_STRIP = 8; // höchstens so viele weitere Quellen in der Wischleiste

const readMark = () =>
  `<span class="readmark" title="Gelesen"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Gelesen">${ICONS.glasses}</svg></span>`;
const icon = (name, size = 22) =>
  `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;

function initials(name) {
  const parts = String(name).split(/\s+/).filter(Boolean);
  const raw = parts.length > 1 ? parts.map((p) => p[0]).join("").slice(0, 3) : String(name).slice(0, 2);
  return escapeHtml(raw);
}

// Symbol der Quelle direkt von deren Website; lädt es nicht, bleiben die Buchstaben sichtbar.
function sourceIcon(item, name) {
  let icon = "";
  try {
    const u = new URL(item.site || item.link);
    if (u.protocol === "https:" || u.protocol === "http:") {
      icon = `<img class="favicon" src="${escapeHtml(u.origin)}/favicon.ico" alt="" referrerpolicy="no-referrer" onload="this.classList.add('ok')" onerror="this.remove()">`;
    }
  } catch {
    icon = "";
  }
  return `<span class="logo" aria-hidden="true">${initials(name)}${icon}</span>`;
}

function srcRow(item, sources, now, extra = "") {
  const name = item.publisher || sources[item.source]?.name || item.source;
  return `<div class="src">${sourceIcon(item, name)}<span class="srcname">${escapeHtml(name)}</span>${
    item.plus ? '<span class="plus">Plus</span>' : ""
  }<span class="time">· ${relativeTime(item.published, now)}</span>${extra}</div>`;
}

const articleLink = (item, storyId, cls) =>
  `<a class="${cls}" href="${safeUrl(item.link)}" target="_blank" rel="noopener" data-read="${escapeHtml(storyId)}">${escapeHtml(item.title)}</a>`;

const distinctSources = (story) => new Set(story.items.map((i) => i.source)).size;

export function storyCard(story, sources, ctx, reason = null) {
  const lead = story.items.find((i) => i.id === story.lead) || story.items[0];
  const others = story.items.filter((i) => i !== lead).slice(0, MAX_STRIP);
  const read = (ctx.read || []).includes(story.id);
  const n = distinctSources(story);
  const thumb = lead.image ? `<img class="thumb" src="${safeUrl(lead.image)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : "";
  const strip = others.length
    ? `<div class="strip" role="list" aria-label="Weitere Quellen">${others
        .map((it) => `<div class="relcard" role="listitem">${srcRow(it, sources, ctx.now)}${articleLink(it, story.id, "relhl")}</div>`)
        .join("")}</div>`
    : "";
  return `<article class="card">${reason ? `<p class="why">${escapeHtml(reason)}</p>` : ""}
<div class="lead"><div class="leadtxt">${srcRow(lead, sources, ctx.now, read ? readMark() : "")}${articleLink(lead, story.id, "hl")}</div>${thumb}</div>${strip}${
    n > 1
      ? `<a class="more" href="#story/${escapeHtml(story.id)}">Komplette Berichterstattung · ${n} Quellen <span aria-hidden="true">›</span></a>`
      : ""
  }</article>`;
}

export function bottomNav(active) {
  const item = (key, label, href) =>
    `<a class="navi${active === key ? " on" : ""}" href="${href}"${active === key ? ' aria-current="page"' : ""}><span class="pill">${icon(key)}</span>${label}</a>`;
  return `<nav class="nav" aria-label="Hauptmenü">${item("aktuell", "Aktuell", "#aktuell/alle")}${item("fuerdich", "Für dich", "#fuerdich")}${item(
    "interessen",
    "Interessen",
    "#interessen",
  )}</nav>`;
}

function header(title, ctx) {
  const stand = ctx.generatedAt ? `<p class="stand">Stand: ${relativeTime(ctx.generatedAt, ctx.now)}${ctx.hangs ? " – Aktualisierung hängt, siehe Anleitung" : ""}</p>` : "";
  const banner = ctx.offline ? '<p class="banner" role="status">Offline – du siehst den zuletzt geladenen Stand.</p>' : "";
  return `<header class="top"><h1 class="brand">${escapeHtml(title)}</h1></header>${stand}${banner}`;
}

export function aktuellView(stories, tab, ctx) {
  const tabs = [
    ["alle", "Alle"],
    ["inland", "Inland"],
    ["ausland", "Ausland"],
  ]
    .map(([k, l]) =>
      k === tab ? `<a class="tab on" href="#aktuell/${k}" aria-current="page">${l}</a>` : `<a class="tab" href="#aktuell/${k}">${l}</a>`,
    )
    .join("");
  const limit = ctx.limit ?? stories.length;
  const shown = stories.slice(0, limit);
  const cards = shown.length
    ? shown.map((s) => storyCard(s, ctx.sources, ctx)).join("")
    : '<p class="empty">Gerade keine Meldungen in diesem Bereich.</p>';
  const more = stories.length > limit ? '<button class="more-btn" data-more>Weitere Meldungen</button>' : "";
  const search = `<form class="search" role="search" onsubmit="return false"><label class="sr" for="q">Suchen</label><input id="q" class="field" type="search" inputmode="search" autocomplete="off" placeholder="Suchen, z. B. Klima" value="${escapeHtml(ctx.query || "")}"></form>`;
  return `${header("Nachrichten", ctx)}${search}<nav class="tabs" aria-label="Region">${tabs}</nav><main class="feed">${cards}${more}</main>${bottomNav("aktuell")}`;
}

const TOPIC_HINT =
  "Für eine Suche über die 11 Medien hinaus muss das Thema in die Themen-Liste: im Projekt config/sources.yaml unter „themen:“ eintragen – oder Claude Bescheid geben.";

export function searchResults(stories, query, ctx) {
  const q = String(query).trim();
  const term = q.toLowerCase();
  if (!stories.length) {
    return `<p class="hits">Keine Treffer für „${escapeHtml(q)}“ in den letzten 48 Stunden.</p><p class="hint">${TOPIC_HINT}</p>`;
  }
  const follow = (ctx.keywords || []).includes(term) ? "" : `<button class="follow" data-follow="${escapeHtml(term)}">Thema folgen</button>`;
  const cards = stories.slice(0, 50).map((s) => storyCard(s, ctx.sources, ctx)).join("");
  return `<div class="hits"><span>${stories.length} Treffer für „${escapeHtml(q)}“</span>${follow}</div>${cards}`;
}

export function storyView(story, sources, mediaType, ctx) {
  const lead = story.items.find((i) => i.id === story.lead) || story.items[0];
  const chips = Object.entries(MEDIA_LABELS)
    .map(([k, l]) => `<a class="chip${k === mediaType ? " on" : ""}" href="#story/${escapeHtml(story.id)}/${k}"${k === mediaType ? ' aria-current="true"' : ""}>${l}</a>`)
    .join("");
  const items = itemsByMediaType(story, sources, mediaType);
  const list = items.length
    ? items.map((it) => `<div class="item">${srcRow(it, sources, ctx.now)}${articleLink(it, story.id, "ihl")}</div>`).join("")
    : '<p class="empty">Keine Meldung dieses Medientyps.</p>';
  return `<div class="bar"><a class="back" href="#aktuell/alle" aria-label="Zurück">${icon("back")}</a><p class="barlabel">Komplette Berichterstattung</p></div>
<header class="head"><h1 class="title">${escapeHtml(lead.title)}</h1><p class="meta">${distinctSources(story)} Quellen · zuletzt aktualisiert ${relativeTime(
    story.latest,
    ctx.now,
  )}</p></header><nav class="chips" aria-label="Quellen filtern">${chips}</nav><main class="list">${list}</main>`;
}

export function fuerDichView(entries, ctx) {
  const body = entries.length
    ? entries.map((e) => storyCard(e.story, ctx.sources, ctx, e.reason)).join("")
    : '<p class="empty">Wähle unter Interessen Kategorien oder Stichworte.</p>';
  return `${header("Für dich", ctx)}<main class="feed">${body}</main>${bottomNav("fuerdich")}`;
}

function chipList(values, field) {
  return values
    .map(
      (v) =>
        `<span class="kwchip">${escapeHtml(v)}<button class="x" data-remove="${field}" data-value="${escapeHtml(v)}" aria-label="${escapeHtml(v)} entfernen">${icon("x", 14)}</button></span>`,
    )
    .join("");
}

export function interessenView(settings, info = null) {
  const feedback = info
    ? `<p class="feedback" role="status">${
        info.hits
          ? `„${escapeHtml(info.term)}“: gerade ${info.hits} Meldung${info.hits === 1 ? "" : "en"} – siehe „Für dich“.`
          : info.listed
            ? `„${escapeHtml(info.term)}“ steht schon in der Themen-Liste, gerade gibt es aber keine Meldung dazu.`
            : `„${escapeHtml(info.term)}“: gerade keine Meldung. ${TOPIC_HINT}`
      }</p>`
    : "";
  const cats = Object.entries(CATEGORY_LABELS)
    .map(
      ([k, l]) =>
        `<label class="row">${l}<input type="checkbox" data-toggle-cat value="${k}"${settings.categories.includes(k) ? " checked" : ""}></label>`,
    )
    .join("");
  const hideCats = Object.entries(CATEGORY_LABELS)
    .map(
      ([k, l]) =>
        `<label class="row">${l} ausblenden<input type="checkbox" data-hide-cat="${k}"${settings.hidden.includes(`kat:${k}`) ? " checked" : ""}></label>`,
    )
    .join("");
  const textHidden = settings.hidden.filter((h) => !h.startsWith("kat:"));
  const form = (field, label, placeholder, button) =>
    `<form class="add" data-add="${field}"><label class="sr" for="in-${field}">${label}</label><input id="in-${field}" class="field" name="value" type="text" autocomplete="off" placeholder="${placeholder}"><button class="btn" type="submit">${button}</button></form>`;
  const themes = [
    ["system", "Wie Handy"],
    ["light", "Hell"],
    ["dark", "Dunkel"],
  ]
    .map(
      ([k, l]) =>
        `<label class="seg"><input type="radio" name="theme" value="${k}"${settings.theme === k ? " checked" : ""}><span>${l}</span></label>`,
    )
    .join("");
  return `<header class="top"><h1 class="brand">Interessen</h1></header><main class="body">
<h2 class="sec">Darstellung</h2><div class="segs" role="radiogroup" aria-label="Darstellung">${themes}</div>
<h2 class="sec">Kategorien</h2><div class="panel">${cats}</div>
<h2 class="sec">Stichworte</h2>${feedback}<div class="panel">${form("keywords", "Neues Stichwort", "Neues Stichwort, z. B. Klima", "Folgen")}<div class="kws">${chipList(settings.keywords, "keywords")}</div></div>
<p class="hint">Stichworte werden in Überschriften und wichtigen Wörtern aller Meldungen gesucht, auch als Wortanfang.</p>
<h2 class="sec">Themen ausblenden</h2><div class="panel">${form("hidden", "Thema ausblenden", "Thema, z. B. Fußball", "Ausblenden")}<div class="kws">${chipList(textHidden, "hidden")}</div>${hideCats}</div>
<p class="hint">Ausgeblendetes verschwindet überall, auch unter Aktuell. Gespeichert wird nur auf diesem Gerät.</p>
</main>${bottomNav("interessen")}`;
}
