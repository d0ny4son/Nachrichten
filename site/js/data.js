// Lädt die vom Sammler erzeugte Datei. Offline liefert der Service Worker
// die zuletzt gespeicherte Fassung und setzt dabei den Header X-From-Cache.
export async function loadData(fetchFn = globalThis.fetch) {
  try {
    const res = await fetchFn("data/stories.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data || !Array.isArray(data.stories)) throw new Error("Ungültige Daten");
    return { data, stale: res.headers?.get?.("X-From-Cache") === "1" };
  } catch {
    return { error: "Keine Verbindung und noch keine gespeicherten Nachrichten." };
  }
}
