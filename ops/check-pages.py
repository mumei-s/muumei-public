import functools, http.server, json, pathlib, sys, threading, urllib.parse
from playwright.sync_api import sync_playwright

root=pathlib.Path(sys.argv[1]).resolve()
out=pathlib.Path('verification');out.mkdir(exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def send_error(self,code,message=None,explain=None):
        if code==404 and '.' not in urllib.parse.urlsplit(self.path).path.rsplit('/',1)[-1]:
            data=(pathlib.Path(self.directory)/'404.html').read_bytes()
            self.send_response(404);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(data)
        else: super().send_error(code,message,explain)

http_root=out/'http';http_root.mkdir(exist_ok=True)
(http_root/'muumei-public').symlink_to(root/'app',target_is_directory=True)
(http_root/'404.html').symlink_to(root/'app/404.html')
servers=[]
for port,directory in [(4173,http_root),(4174,root/'owner')]:
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),functools.partial(Handler,directory=str(directory)))
    threading.Thread(target=server.serve_forever,daemon=True).start();servers.append(server)

report={'checks':[],'errors':[],'authenticated_e2e':False}
with sync_playwright() as p:
    browser=p.chromium.launch()
    for surface,origin,base,routes in [
        ('app','http://127.0.0.1:4173','/muumei-public/', ['', 'login','about','demo/home','demo/work','demo/boards','demo/messages','demo/install']),
        ('owner','http://127.0.0.1:4174','/', ['', 'demo/dashboard','demo/jobs','demo/jobs/new','demo/members','demo/messages','demo/settings'])
    ]:
        context=browser.new_context(service_workers='allow',reduced_motion='reduce')
        context.route('https://*.supabase.co/**',lambda route:route.abort())
        page=context.new_page()
        js_errors=[];page.on('pageerror',lambda error:js_errors.append(str(error)))
        for width in [360,390,1280]:
            page.set_viewport_size({'width':width,'height':900})
            for route in routes:
                url=origin+base+route
                response=page.goto(url,wait_until='domcontentloaded')
                page.wait_for_function("document.querySelector('#root')?.textContent?.trim().length > 30",timeout=30000)
                page.wait_for_timeout(700)
                state=page.evaluate('''() => ({
                    overflow:document.documentElement.scrollWidth-innerWidth,
                    text:document.querySelector('#root').textContent,
                    photos:getComputedStyle(document.body).backgroundImage.includes('url('),
                    brokenImages:[...document.images].filter(i=>i.getBoundingClientRect().top<innerHeight&&i.getBoundingClientRect().bottom>0&&(!i.complete||!i.naturalWidth)).map(i=>i.getAttribute('src')),
                    badLinks:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(h=>h.startsWith('/')&&!h.startsWith('//')&&!h.startsWith(location.port==='4173'?'/muumei-public/':'/'))
                })''')
                errors=[]
                if response.status!=200:errors.append('HTTP '+str(response.status))
                if state['overflow']>2:errors.append('horizontal overflow '+str(state['overflow']))
                if not state['photos']:errors.append('missing photographic background')
                if state['brokenImages']:errors.append('broken images '+str(state['brokenImages']))
                if state['badLinks']:errors.append('unscoped links '+str(state['badLinks']))
                if 'このページは見つかりません' in state['text']:errors.append('unexpected route failure')
                if js_errors:errors+=js_errors;js_errors.clear()
                label=surface+'-'+str(width)+'-'+(route.replace('/','-') or 'home')
                report['checks'].append({'name':label,'ok':not errors,'errors':errors})
                if width==390 and route in ['', 'demo/home','demo/jobs/new','demo/settings']:
                    page.screenshot(path=str(out/(label+'.png')),full_page=True)
        # Verify that the app worker cannot delete caches belonging to another app.
        page.goto(origin+base+('demo/home' if surface=='app' else 'demo/dashboard'),wait_until='networkidle')
        page.evaluate("caches.open('note-insight-test-sentinel')")
        worker=page.evaluate("async()=>{await navigator.serviceWorker.ready;return {scopes:(await navigator.serviceWorker.getRegistrations()).map(r=>r.scope),cachePreserved:(await caches.keys()).includes('note-insight-test-sentinel')}}")
        report['checks'].append({'name':surface+'-worker-scope','ok':all(s==origin+base for s in worker['scopes']) and worker['cachePreserved'],'details':worker})
        if surface=='app':
            page.goto(origin+base,wait_until='networkidle')
            ratios=page.evaluate('''() => {
                function lum(s){const a=(s.match(/[\\d.]+/g)||[]).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return .2126*a[0]+.7152*a[1]+.0722*a[2]}
                return [...document.querySelectorAll('.m-button,.m-footer .m-underlink')].map(e=>{const s=getComputedStyle(e),a=lum(s.color),b=lum(s.backgroundColor);return {text:e.textContent,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)}})
            }''')
            report['checks'].append({'name':'primary-and-footer-contrast','ok':bool(ratios) and all(x['ratio']>=4.5 for x in ratios),'details':ratios})
            page.goto(origin+base+'demo/work',wait_until='networkidle')
            job=page.locator('a.job-card').first
            if job.count():
                target=job.get_attribute('href');job.click();page.wait_for_timeout(900)
                report['checks'].append({'name':'job-detail-click','ok':page.url.startswith(origin+base) and 'このページは見つかりません' not in page.inner_text('#root'),'url':page.url})
                page.reload(wait_until='networkidle')
                report['checks'].append({'name':'job-detail-reload','ok':page.url.startswith(origin+base) and 'このページは見つかりません' not in page.inner_text('#root'),'url':page.url})
        context.close()
    browser.close()
for server in servers:server.shutdown()
report['errors']=[c for c in report['checks'] if not c['ok']]
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'checks':len(report['checks']),'failed':len(report['errors']),'errors':report['errors']},ensure_ascii=False))
if report['errors']:sys.exit(1)
