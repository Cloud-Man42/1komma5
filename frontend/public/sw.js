/* EMIC PWA service worker — static assets only; never cache API/auth or intercept navigation. */
const CACHE_VERSION = "emic-shell-v4";
const STATIC_URLS = [
  "/manifest.webmanifest",
  "/icons/emic-icon-192.png",
  "/icons/emic-icon-512.png",
  "/icons/emic-logo.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => Promise.allSettled(STATIC_URLS.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") return;
  if (url.pathname.startsWith("/api/")) return;
  if (url.pathname.startsWith("/_next/")) return;

  if (url.pathname.startsWith("/icons/") || url.pathname.endsWith(".webmanifest")) {
    event.respondWith(
      caches.open(CACHE_VERSION).then((cache) =>
        cache.match(request).then((cached) => cached || fetch(request).then((res) => {
          cache.put(request, res.clone());
          return res;
        })),
      ),
    );
  }
});
