const CACHE_NAME = 'scam-detector-v1';
const STATIC_ASSETS = [
  '/',
  '/static/style.css',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];
 
// Install — cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});
 
// Activate — clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});
 
// Fetch — network first, cache fallback
self.addEventListener('fetch', event => {
  // Skip non-GET and API calls
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/predict') ||
      event.request.url.includes('/chat') ||
      event.request.url.includes('/scan')) return;
 
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Cache fresh responses
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => {
        // Offline fallback from cache
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          // Offline page fallback
          return new Response(`
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>Scam Detector — Offline</title>
            <style>
              body{font-family:sans-serif;background:#0a0f1e;color:#f8fafc;
                   display:flex;align-items:center;justify-content:center;
                   min-height:100vh;text-align:center;margin:0;}
              h2{font-size:24px;margin-bottom:12px;}
              p{color:#64748b;font-size:14px;}
              a{color:#3b82f6;text-decoration:none;}
            </style></head>
            <body>
              <div>
                <div style="font-size:48px;margin-bottom:16px;">🛡️</div>
                <h2>You're Offline</h2>
                <p>Please check your internet connection<br>and try again.</p>
                <br>
                <a href="/">Try Again</a>
              </div>
            </body></html>
          `, { headers: { 'Content-Type': 'text/html' } });
        });
      })
  );
});