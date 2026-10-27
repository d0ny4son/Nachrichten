import { CATEGORY_LABELS } from "./format.js";

const WORD = /[0-9a-zäöüß]+/g;

function words(item) {
  const fromTitle = String(item.title || "").toLowerCase().match(WORD) || [];
  return [...(item.keywords || []), ...fromTitle];
}

// Jeder Teil des Begriffs („Olaf Scholz“, „E-Auto“) muss als Wortanfang vorkommen.
export function matchesTerm(item, term) {
  const parts = String(term || "").toLowerCase().match(WORD) || [];
  if (!parts.length) return false;
  const ws = words(item);
  return parts.every((p) => ws.some((w) => w.startsWith(p)));
}

export function isHidden(story, hidden) {
  return hidden.some((h) =>
    h.startsWith("kat:")
      ? (story.categories || []).includes(h.slice(4))
      : story.items.some((it) => matchesTerm(it, h)),
  );
}

export function byRegion(stories, tab) {
  return tab === "alle" ? stories : stories.filter((s) => s.region === tab);
}

export function aktuell(data, tab, settings) {
  return byRegion(data.stories, tab).filter((s) => !isHidden(s, settings.hidden));
}

export function fuerDich(data, settings) {
  const out = [];
  for (const story of data.stories) {
    if (isHidden(story, settings.hidden)) continue;
    const kw = settings.keywords.find((k) => story.items.some((it) => matchesTerm(it, k)));
    let reason = kw ? `Stichwort: ${kw}` : null;
    if (!reason) {
      const cat = settings.categories.find((c) => (story.categories || []).includes(c));
      if (cat) reason = CATEGORY_LABELS[cat] || cat;
    }
    if (reason) out.push({ story, reason });
  }
  return out.sort((a, b) => (a.story.latest < b.story.latest ? 1 : a.story.latest > b.story.latest ? -1 : 0));
}

export function itemsByMediaType(story, sources, type) {
  if (type === "alle") return story.items;
  return story.items.filter((it) => sources[it.source]?.media_type === type);
}
