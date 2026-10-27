export const CATEGORY_LABELS = {
  wissenschaft: "Wissenschaft",
  technik: "Technik",
  wirtschaft: "Wirtschaft",
  kultur: "Kultur",
  sport: "Sport",
};

export const MEDIA_LABELS = {
  alle: "Alle",
  "oeffentlich-rechtlich": "Öffentlich-rechtlich",
  zeitung: "Zeitungen",
  international: "International",
};

export function relativeTime(iso, now = new Date()) {
  const sec = Math.floor((now.getTime() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return "gerade eben";
  const min = Math.floor(sec / 60);
  if (min < 60) return `vor ${min} Min.`;
  const h = Math.floor(min / 60);
  if (h < 24) return `vor ${h} Std.`;
  if (h < 48) return "gestern";
  return `vor ${Math.floor(h / 24)} Tagen`;
}
