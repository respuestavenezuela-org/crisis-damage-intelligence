// Service worker for Respuesta Venezuela.
const CACHE = "rv-shell-v3";
const OFFLINE = "rv-offline";
const APP_SHELL = ["/offline"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("message", (event) => {
  const data = event.data;
  if (data === "SKIP_WAITING") {
    self.skipWaiting();
    return;
  }
  if (data && data.type === "CACHE_SHELL" && Array.isArray(data.urls)) {
    event.waitUntil(
      caches.open(CACHE).then((cache) => cache.addAll(data.urls).catch(() => {})),
    );
  }
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE && key !== OFFLINE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const path = url.pathname;
  if (/\.(tif|tiff|cog)$/i.test(path)) return;

  if (path.startsWith("/data/tiles/") || path.startsWith("/data/chips/")) {
    event.respondWith(
      caches
        .open(OFFLINE)
        .then((cache) => cache.match(request))
        .then((hit) => hit || fetch(request)),
    );
    return;
  }

  if (path.startsWith("/data/")) {
    event.respondWith(networkFirstWithTimeout(request, CACHE, 3500));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigate(request));
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});

async function networkFirstWithTimeout(request, cacheName, timeoutMs) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  let timeout;
  const network = fetch(request)
    .then((response) => {
      if (response && response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);

  const timedFallback = new Promise((resolve) => {
    timeout = setTimeout(() => resolve(cached), timeoutMs);
  });

  const response = await Promise.race([network, timedFallback]);
  if (timeout) clearTimeout(timeout);
  return response || cached || network;
}

async function networkFirstNavigate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  try {
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    return cached || (await cache.match("/")) || (await caches.match("/offline"));
  }
}
