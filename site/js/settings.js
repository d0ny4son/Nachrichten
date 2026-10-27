// Einstellungen: bleiben nur auf diesem Gerät (localStorage).
const KEY = "nachrichten.settings";
const MAX_READ = 500;

export const THEMES = ["system", "light", "dark"];
export const DEFAULTS = Object.freeze({ categories: [], keywords: [], hidden: [], read: [], theme: "system" });

const strings = (v) => (Array.isArray(v) ? v.filter((x) => typeof x === "string") : []);

// localStorage erst im try ansehen: Bei gesperrten Website-Daten wirft schon der Zugriff.
const storageOf = (args) => (args.length ? args[0] : globalThis.localStorage);

export function loadSettings(...args) {
  try {
    const raw = storageOf(args).getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    const s = JSON.parse(raw);
    return {
      categories: strings(s.categories),
      keywords: strings(s.keywords),
      hidden: strings(s.hidden),
      read: strings(s.read).slice(-MAX_READ),
      theme: THEMES.includes(s.theme) ? s.theme : "system",
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveSettings(settings, ...args) {
  try {
    storageOf(args).setItem(KEY, JSON.stringify(settings));
    return true;
  } catch {
    return false;
  }
}

function addTo(settings, field, text) {
  const value = String(text ?? "").trim().toLowerCase();
  if (!value || settings[field].includes(value)) return null;
  return { ...settings, [field]: [...settings[field], value] };
}

export const addKeyword = (s, text) => addTo(s, "keywords", text);
export const addHidden = (s, text) => addTo(s, "hidden", text);

export function removeFrom(settings, field, value) {
  return { ...settings, [field]: settings[field].filter((v) => v !== value) };
}

export function toggle(settings, field, value) {
  return settings[field].includes(value)
    ? removeFrom(settings, field, value)
    : { ...settings, [field]: [...settings[field], value] };
}

export function markRead(settings, storyId) {
  const read = settings.read.filter((id) => id !== storyId);
  read.push(storyId);
  return { ...settings, read: read.slice(-MAX_READ) };
}
