// Service worker: makes the whole app work with no network at all.
//
// The models were already cached by Transformers.js, but the PAGE was not --
// with no internet the browser could not fetch index.html, so nothing ran and
// Chrome showed its offline page instead. Everything the app needs now goes
// through here: the shell, the library from the CDN, the ONNX runtime WASM,
// and the model weights.
const CACHE = "microtranslate-v1";
const SHELL = ["./", "./index.html", "./neutro.js", "./manifest.webmanifest"];

// The library and the ONNX runtime WASM. Model weights are deliberately NOT
// here: Transformers.js already caches those itself, and duplicating 370MB in
// a second store helps nobody.
const KEEP = /(^|\.)jsdelivr\.net$|(^|\.)unpkg\.com$/;

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // addAll fails the whole install if any single file 404s, so do them singly
    await Promise.all(SHELL.map((u) => c.add(u).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((n) => n !== CACHE).map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const ours = url.origin === self.location.origin;
  if (!ours && !KEEP.test(url.hostname)) return;   // leave anything else alone

  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // These are all immutable (versioned library, content-addressed weights),
    // so a cache hit is always safe and avoids a network round trip.
    const hit = await cache.match(req, { ignoreSearch: ours });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      // Range requests come back 206 and cannot be stored; everything else can.
      if (res && res.status === 200) cache.put(req, res.clone()).catch(() => {});
      return res;
    } catch (err) {
      // Offline and not cached. For a navigation, hand back the app shell so
      // the page still opens rather than showing the browser's offline page.
      if (req.mode === "navigate") {
        return (await cache.match("./index.html")) ||
               (await cache.match("./")) ||
               Response.error();
      }
      throw err;
    }
  })());
});

// The page asks how much is cached so it can say when it is safe to disconnect.
self.addEventListener("message", (e) => {
  if (e.data && e.data.type === "cacheStatus") {
    (async () => {
      const cache = await caches.open(CACHE);
      const keys = await cache.keys();
      const hosts = {};
      for (const k of keys) {
        const h = new URL(k.url).hostname || "local";
        hosts[h] = (hosts[h] || 0) + 1;
      }
      let bytes = 0;
      try { bytes = (await navigator.storage.estimate()).usage || 0; } catch {}
      e.source && e.source.postMessage({ type: "cacheStatus", count: keys.length, hosts, bytes });
    })();
  }
});
