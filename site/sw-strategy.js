// Entscheidet, wie der Service Worker eine Anfrage behandelt.
// Klassisches Skript (kein Modul), damit sw.js es per importScripts laden kann.
function strategyFor(url, scope) {
  const u = new URL(url);
  const s = new URL(scope);
  if (u.origin !== s.origin || !u.pathname.startsWith(s.pathname)) return "network";
  const rel = u.pathname.slice(s.pathname.length);
  if (rel === "data/stories.json") return "network-first";
  if (rel.startsWith("data/")) return "network";
  return "cache-first";
}

// Wartet höchstens ms Millisekunden, sonst Fehler (z. B. Funkloch im Zug).
function withTimeout(promise, ms) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error("Zeitüberschreitung")), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}
