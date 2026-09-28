import functools, http.server, json, pathlib, re, sys, threading, urllib.parse
from playwright.sync_api import sync_playwright, expect

root = pathlib.Path(sys.argv[1]).resolve()
out = pathlib.Path('verification')
out.mkdir(exist_ok=True)
report = {'checks': [], 'errors': [], 'authenticated_e2e': False}

def save_report():
    report['errors'] = [c for c in report['checks'] if not c['ok']]
    (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

def record(name, ok, **details):
    report['checks'].append({'name': name, 'ok': bool(ok), **details})
    save_report()
    print(json.dumps(report['checks'][-1], ensure_ascii=False), flush=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def send_error(self, code, message=None, explain=None):
        if code == 404 and '.' not in urllib.parse.urlsplit(self.path).path.rsplit('/', 1)[-1]:
            data = (pathlib.Path(self.directory) / '404.html').read_bytes()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)
        else:
            super().send_error(code, message, explain)

http_root = out / 'http'
http_root.mkdir(exist_ok=True)
for link, target in [(http_root / 'muumei-public', root / 'app'), (http_root / '404.html', root / 'app/404.html')]:
    if link.is_symlink():
        link.unlink()
    link.symlink_to(target, target_is_directory=target.is_dir())
servers = []
for port, directory in [(4173, http_root), (4174, root / 'owner')]:
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Handler, directory=str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    servers.append(server)

def ready(page):
    # Locator assertions do not call eval inside the protected page.
    # Keep production CSP active: no unsafe-eval or bypass_csp.
    expect(page.locator('#root')).to_have_text(re.compile(r'\S[\s\S]{30,}'), timeout=15000)

def screenshot(page, label):
    try:
        page.screenshot(path=str(out / (label + '.png')), full_page=True, timeout=10000)
    except Exception as error:
        print('Screenshot failed: ' + str(error), flush=True)

page = None
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for surface, origin, base, routes in [
            ('app', 'http://127.0.0.1:4173', '/muumei-public/', ['', 'login', 'about', 'demo/home', 'demo/work', 'demo/boards', 'demo/messages', 'demo/install']),
            ('owner', 'http://127.0.0.1:4174', '/', ['', 'demo/dashboard', 'demo/jobs', 'demo/jobs/new', 'demo/members', 'demo/messages', 'demo/settings'])
        ]:
            context = browser.new_context(service_workers='allow', reduced_motion='reduce')
            context.route('https://*.supabase.co/**', lambda route: route.abort())
            page = context.new_page()
            page.set_default_timeout(15000)
            js_errors = []
            page.on('pageerror', lambda error: js_errors.append(str(error)))
            for width in [360, 390, 1280]:
                page.set_viewport_size({'width': width, 'height': 900})
                for route in routes:
                    label = surface + '-' + str(width) + '-' + (route.replace('/', '-') or 'home')
                    errors = []
                    try:
                        response = page.goto(origin + base + route, wait_until='domcontentloaded')
                        ready(page)
                        page.wait_for_timeout(700)
                        state = page.evaluate('''() => ({
                            overflow: document.documentElement.scrollWidth - innerWidth,
                            text: document.querySelector('#root').textContent,
                            photos: getComputedStyle(document.body).backgroundImage.includes('url('),
                            brokenImages: [...document.images].filter(i => i.getBoundingClientRect().top < innerHeight && i.getBoundingClientRect().bottom > 0 && (!i.complete || !i.naturalWidth)).map(i => i.getAttribute('src')),
                            badLinks: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => h.startsWith('/') && !h.startsWith('//') && !h.startsWith(location.port === '4173' ? '/muumei-public/' : '/'))
                        })''')
                        if not response or response.status != 200:
                            errors.append('HTTP ' + str(response.status if response else 'no response'))
                        if state['overflow'] > 2:
                            errors.append('horizontal overflow ' + str(state['overflow']))
                        if not state['photos']:
                            errors.append('missing photographic background')
                        if state['brokenImages']:
                            errors.append('broken images ' + str(state['brokenImages']))
                        if state['badLinks']:
                            errors.append('unscoped links ' + str(state['badLinks']))
                        if 'このページは見つかりません' in state['text']:
                            errors.append('unexpected route failure')
                    except Exception as error:
                        errors.append(str(error))
                    errors.extend(js_errors)
                    js_errors.clear()
                    record(label, not errors, errors=errors, url=page.url)
                    if errors or (width == 390 and route in ['', 'demo/home', 'demo/jobs/new', 'demo/settings']):
                        screenshot(page, label)
            try:
                page.goto(origin + base + ('demo/home' if surface == 'app' else 'demo/dashboard'), wait_until='networkidle')
                ready(page)
                page.evaluate("() => caches.open('note-insight-test-sentinel')")
                worker = page.evaluate('''async () => {
                    await Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => setTimeout(() => reject(new Error('Service worker readiness timed out')), 10000))]);
                    return {scopes: (await navigator.serviceWorker.getRegistrations()).map(r => r.scope), cachePreserved: (await caches.keys()).includes('note-insight-test-sentinel')};
                }''')
                record(surface + '-worker-scope', bool(worker['scopes']) and all(s == origin + base for s in worker['scopes']) and worker['cachePreserved'], details=worker)
            except Exception as error:
                record(surface + '-worker-scope', False, errors=[str(error)])
                screenshot(page, surface + '-worker-failure')
            if surface == 'app':
                try:
                    page.goto(origin + base, wait_until='networkidle')
                    ready(page)
                    ratios = page.evaluate(r'''() => {
                        function lum(s) { const a = (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4 }); return .2126 * a[0] + .7152 * a[1] + .0722 * a[2] }
                        return [...document.querySelectorAll('.m-button,.m-footer .m-underlink')].map(e => { const s = getComputedStyle(e), a = lum(s.color), b = lum(s.backgroundColor); return {text: e.textContent, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05)} });
                    }''')
                    record('primary-and-footer-contrast', bool(ratios) and all(x['ratio'] is not None and x['ratio'] >= 4.5 for x in ratios), details=ratios)
                except Exception as error:
                    record('primary-and-footer-contrast', False, errors=[str(error)])
                try:
                    page.goto(origin + base + 'demo/work', wait_until='networkidle')
                    ready(page)
                    job = page.locator('a.job-card').first
                    expect(job).to_be_visible()
                    job.click()
                    ready(page)
                    record('job-detail-click', page.url.startswith(origin + base) and 'このページは見つかりません' not in page.inner_text('#root'), url=page.url)
                    page.reload(wait_until='networkidle')
                    ready(page)
                    record('job-detail-reload', page.url.startswith(origin + base) and 'このページは見つかりません' not in page.inner_text('#root'), url=page.url)
                except Exception as error:
                    record('job-detail-navigation', False, errors=[str(error)], url=page.url)
                    screenshot(page, 'job-detail-failure')
            if js_errors:
                record(surface + '-remaining-js-errors', False, errors=list(js_errors))
            context.close()
            page = None
        browser.close()
except Exception as error:
    record('verification-harness', False, errors=[str(error)])
    if page is not None:
        screenshot(page, 'verification-harness-failure')
finally:
    for server in servers:
        server.shutdown()
    save_report()

print(json.dumps({'checks': len(report['checks']), 'failed': len(report['errors']), 'errors': report['errors']}, ensure_ascii=False))
if report['errors']:
    sys.exit(1)
