/**
 * LegalEase Pro - Service Worker
 * Cache-first for static shell, network-first for API.
 */

const CACHE_NAME = "legalease-v15";
const SHELL = [
  "/",
  "/index.html",
  "/css/styles.css",
  "/js/app.js",
  "/js/api.js",
  "/js/state.js",
  "/js/ui.js",
  "/js/voice.js",
  "/js/screens/chat.js",
  "/js/screens/complaint.js",
  "/js/screens/templates.js",
  "/js/screens/history.js",
  "/js/screens/settings.js",
  "/js/screens/laws.js",
  "/js/screens/auth.js",
  "/js/screens/home.js",
  "/js/screens/onboarding.js",
  "/manifest.json",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Bypass non-GET and cross-origin API
  if (req.method !== "GET") return;

  // API requests: network-first
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(req).catch(() =>
        new Response(JSON.stringify({ status: "error", message: "Offline" }), {
          headers: { "Content-Type": "application/json" },
          status: 503,
        })
      )
    );
    return;
  }

  // Static shell: cache-first
  event.respondWith(
    caches.match(req).then(cached => cached || fetch(req).then(resp => {
      // Cache successful navigation responses
      if (resp.ok && url.origin === self.location.origin) {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(c => c.put(req, clone));
      }
      return resp;
    }).catch(() => caches.match("/index.html")))
  );
});
