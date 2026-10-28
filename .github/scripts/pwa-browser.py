"""Verify the published PWA without authentication or production data writes."""
import json,pathlib,sys,os,http.server,threading
from urllib.parse import urljoin,urlsplit
from playwright.sync_api import sync_playwright,expect
# Required by the pinned Playwright 1.55 worker network implementation.
os.environ.setdefault('PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS','1')
target=sys.argv[1]
server=None
if target.startswith('https://'):
 base=target.rstrip('/')+'/'
else:
 root=pathlib.Path(target).resolve()
 class Handler(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
  def translate_path(self,path):
   from urllib.parse import unquote,urlsplit
   local=unquote(urlsplit(path).path).removeprefix('/muumei-public/')
   p=(root/local).resolve()
   return str(p if p.is_relative_to(root) and p.exists() else root/'404.html')
 server=http.server.ThreadingHTTPServer(('127.0.0.1',4190),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base='http://127.0.0.1:4190/muumei-public/'
out=pathlib.Path('verification');out.mkdir(exist_ok=True)
checks=[]
def record(name,ok,**details):
 checks.append(dict(name=name,ok=ok,**details))
 (out/'pwa-browser.json').write_text(json.dumps(dict(live=target.startswith('https://'),production_data_mutated=False,total=sum(x['ok'] is not None for x in checks),skipped=sum(x['ok'] is None for x in checks),failures=sum(x['ok'] is False for x in checks),checks=checks),ensure_ascii=False,indent=2))
 print(name,'SKIP' if ok is None else 'PASS' if ok else 'FAIL',details,flush=True)
with sync_playwright() as p:
 for engine in os.environ.get('MUUMEI_BROWSER_ENGINES','chromium,firefox,webkit').split(','):
  browser=getattr(p,engine).launch()
  context=browser.new_context(viewport={'width':390,'height':844},service_workers='allow',reduced_motion='reduce')
  context.route('https://*.supabase.co/**',lambda route:route.abort())
  page=context.new_page()
  try:
   page.goto(base,wait_until='networkidle');expect(page.locator('#main')).to_be_visible()
   path=page.locator('link[rel="manifest"]').get_attribute('href');response=context.request.get(urljoin(base,path));assert response.status==200
   manifest=response.json();scope=urljoin(base,manifest['scope']);assert scope==base and urljoin(base,manifest['id'])==base
   assert manifest['display']=='standalone' and urljoin(base,manifest['start_url']).startswith(base)
   for icon in manifest['icons']:
    image=context.request.get(urljoin(base,icon['src']));assert image.status==200 and image.headers.get('content-type','').startswith('image/')
   record(engine+':manifest-and-icons',True)
   if engine!='chromium':
    record(engine+':service-worker-offline-automation',None,reason='Playwright service-worker control is supported only on Chromium; verify offline on real Safari/Firefox separately')
    continue
   registration=page.evaluate('''async () => {const r=await Promise.race([navigator.serviceWorker.ready,new Promise((_,reject)=>setTimeout(()=>reject(Error('Service worker registration timed out')),15000))]);return {scope:r.scope,script:r.active?.scriptURL}}''')
   assert registration['scope']==base and registration['script']==urljoin(base,'sw.js')
   record(engine+':service-worker-scope',True)
   page.wait_for_function("navigator.serviceWorker.controller?.state==='activated'",timeout=15000)
   page.reload(wait_until='networkidle')
   page.wait_for_function("navigator.serviceWorker.controller?.state==='activated'",timeout=15000)
   cached=page.evaluate("async () => {const r=await caches.match(new URL('offline.html',location.href).href);return r?await r.text():''}");assert 'ネットワークに接続できません' in cached
   record(engine+':offline-cache-and-control',True)
   context.set_offline(True)
   offline_response=page.goto(base+'?offline-check=1',wait_until='domcontentloaded')
   assert offline_response.from_service_worker,'Offline navigation bypassed the service worker'
   expect(page.get_by_text('いまはネットワークに接続できません。',exact=False)).to_be_visible()
   expect(page.get_by_role('button',name='もう一度試す',exact=True)).to_be_visible()
   record(engine+':offline-fallback',True)
   page.screenshot(path=str(out/(engine+'-offline-390.png')),full_page=True)
   context.set_offline(False)
   page.get_by_role('button',name='もう一度試す',exact=True).click()
   expect(page.locator('#main')).to_be_visible()
   expect(page.locator('#sns-title')).to_contain_text('「またね」の続きが、')
   expect(page.locator('.sns-hero-label')).to_have_text('招待制プライベートSNS')
   expect(page.locator('.sns-entry-card')).to_have_count(3)
   record(engine+':reconnect-and-retry',True)
  except Exception as e:
   record(engine+':pwa-flow',False,error=str(e));page.screenshot(path=str(out/(engine+'-pwa-failure.png')),full_page=True)
  finally:context.close();browser.close()
if server:server.shutdown()
assert checks and not any(x['ok'] is False for x in checks)
