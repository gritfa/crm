/*
 * Service Worker：只让「加到主屏」后的外壳能离线打开，业务数据一律不缓存。
 *
 * CRM 页面里有客户、合同、收款这些敏感数据，而且和登录态强相关，缓存到磁盘
 * 既可能泄露也可能读到过期内容。所以这里只缓存静态资源（样式、图标、离线提示页），
 * 所有页面和接口请求都直接走网络。
 */

const CACHE_NAME = 'crm-shell-v1';
const SHELL_ASSETS = [
  '/static/styles.css',
  '/static/offline.html',
  '/static/icons/icon.svg',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // 非 GET（登录、新增、删除等）永远走网络，不做任何拦截
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // 静态资源：缓存优先，后台顺带更新
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request)
          .then((response) => {
            if (response && response.ok) {
              const copy = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
            }
            return response;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
    return;
  }

  // 页面请求：只走网络；断网时给一个离线提示页，不返回任何业务数据
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match('/static/offline.html')));
  }
});
