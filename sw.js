// Service worker: makes the whole app work with no network at all.
//
// The models were already cached by Transformers.js, but the PAGE was not --
// with no internet the browser could not fetch index.html, so nothing ran and
// Chrome showed its offline page instead. Everything the app needs now goes
// through here: the shell, the library from the CDN, the ONNX runtime WASM,
// and the model weights.
const CACHE = "microtranslate-v7";
const LIB = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.6";
const SHELL = ["./", "./index.html", "./neutro.js", "./worker.js",
               "./manifest.webmanifest", "./icon.svg", "./icon-192.png",
               "./icon-512.png", "./icon-maskable-512.png",
               "./apple-touch-icon.png",
               // The worker imports this at its top level. Verifying offline
               // showed it was not ending up in the cache on its own, and
               // without it nothing runs, so fetch it up front.
               LIB];

// The library, the ONNX runtime WASM, and the model weights. Transformers.js
// has its own store, but it cached the speech model and not the translation
// model, so weights now go here where they can actually be verified.
const KEEP = /(^|\.)jsdelivr\.net$|(^|\.)unpkg\.com$|(^|\.)huggingface\.co$|(^|\.)hf\.co$/;


// HuggingFace serves large weights by redirecting to a signed CDN URL that is
// different on every request. Cache.put() refuses a redirected response, so
// the canonical URL was never stored and each visit re-downloaded everything.
// Rebuild the body as a plain response and store it under the URL we asked for.
async function store(cache, req, res) {
  try {
    if (res.redirected) {
      const body = await res.clone().blob();
      const headers = new Headers();
      for (const h of ["content-type", "content-length"]) {
        const v = res.headers.get(h);
        if (v) headers.set(h, v);
      }
      await cache.put(req, new Response(body, { status: 200, headers }));
    } else {
      await cache.put(req, res.clone());
    }
  } catch (err) { /* quota or an uncacheable response: nothing to do */ }
}

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // cache:"reload" bypasses the HTTP cache. Without it, install stores
    // whatever stale copy the browser already had, which is how a fixed
    // neutro.js shipped but never reached the page.
    await Promise.all(SHELL.map((u) =>
      c.add(new Request(u, { cache: "reload" })).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const names = await caches.keys();
    // also drops the library's old store, now redundant
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

    // The library and the WASM are versioned in their URL and never change, so
    // cache-first is both safe and the whole point.
    if (!ours) {
      const hit = await cache.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res && res.status === 200) await store(cache, req, res);
      return res;
    }

    // Our own files DO change. Cache-first here would freeze every user on the
    // version they first loaded, with no way to ever ship them a fix, so go to
    // the network first and keep the cache only as the offline fallback.
    try {
      // revalidate rather than trusting the HTTP cache, for the same reason
      let res;
      try { res = await fetch(req.url, { cache: "no-cache" }); }
      catch { res = await fetch(req); }
      if (res && res.status === 200) await store(cache, req, res);
      return res;
    } catch (err) {
      const hit = await cache.match(req, { ignoreSearch: true });
      if (hit) return hit;
      if (req.mode === "navigate") {
        return (await cache.match("./index.html")) ||
               (await cache.match("./")) || Response.error();
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
