// Service Worker: App-Hülle offline verfügbar, Nachrichten mit Rückfall auf den letzten Stand.
importScripts("sw-strategy.js");

const CACHE = "app-v4";
const NETWORK_TIMEOUT_MS = 4000;
const SHELL = [
  "./",
  "index.html",
  "app.css",
  "icon.svg",
  "icon-180.png",
  "manifest.webmanifest",
  "sw-strategy.js",
  "js/app.js",
  "js/data.js",
  "js/filters.js",
  "js/format.js",
  "js/settings.js",
  "js/views.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request, { ignoreSearch: true });
  // Im Hintergrund auffrischen, damit neue App-Versionen beim nächsten Start ankommen.
  const refresh = fetch(request)
    .then((res) => {
      if (res.ok) cache.put(request, res.clone());
      return res;
    })
    .catch(() => null);
  return cached || (await refresh) || new Response("Offline", { status: 503 });
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const res = await withTimeout(fetch(request), NETWORK_TIMEOUT_MS);
    if (res.ok) cache.put(request, res.clone());
    return res;
  } catch {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (!cached) throw new Error("offline und nichts gespeichert");
    const headers = new Headers(cached.headers);
    headers.set("X-From-Cache", "1");
    return new Response(await cached.blob(), { status: 200, headers });
  }
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const strategy = strategyFor(req.url, self.registration.scope);
  if (strategy === "cache-first") event.respondWith(cacheFirst(req));
  else if (strategy === "network-first") event.respondWith(networkFirst(req));
});
