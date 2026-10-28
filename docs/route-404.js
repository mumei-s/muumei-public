/* Pages has one project-level 404; keep each synthetic review in its own app root. */
(() => {
  const roots = ['/muumei-public/review/member/', '/muumei-public/review/owner/', '/muumei-public/'];
  const base = roots.find(root => location.pathname.startsWith(root));
  if (!base) {
    const message = document.querySelector('p');
    if (message) message.textContent = 'このページは見つかりません';
    return;
  }
  const route = location.pathname.slice(base.length) + location.search;
  if (route.length > 8192 || route.includes('\\')) return;
  location.replace(base + '?__muumei_route=' + encodeURIComponent(route) + location.hash);
})();
