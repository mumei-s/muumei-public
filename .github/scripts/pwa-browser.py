"""Verify the published PWA without authentication or production data writes."""
import json,pathlib,sys,os
from urllib.parse import urljoin,urlsplit
from playwright.sync_api import sync_playwright,expect
base=sys.argv[1].rstrip('/')+'/'
out=pathlib.Path('verification');out.mkdir(exist_ok=True)
checks=[]
def record(name,ok,**details):
 checks.append(dict(name=name,ok=bool(ok),**details))
 (out/'pwa-browser.json').write_text(json.dumps(dict(live=True,production_data_mutated=False,total=len(checks),failures=sum(not x['ok'] for x in checks),checks=checks),ensure_ascii=False,indent=2))
 print(name,'PASS' if ok else 'FAIL',details,flush=True)
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
   registration=page.evaluate('''async () => {const r=await Promise.race([navigator.serviceWorker.ready,new Promise((_,reject)=>setTimeout(()=>reject(Error('Service worker registration timed out')),15000))]);return {scope:r.scope,script:r.active?.scriptURL}}''')
   assert registration['scope']==base and registration['script']==urljoin(base,'sw.js')
   record(engine+':service-worker-scope',True)
   page.reload(wait_until='networkidle')
   context.set_offline(True)
   page.goto(base+'?offline-check=1',wait_until='domcontentloaded')
   expect(page.get_by_text('いまはネットワークに接続できません。',exact=False)).to_be_visible()
   expect(page.get_by_role('button',name='もう一度試す',exact=True)).to_be_visible()
   record(engine+':offline-fallback',True)
   page.screenshot(path=str(out/(engine+'-offline-390.png')),full_page=True)
   context.set_offline(False)
   page.get_by_role('button',name='もう一度試す',exact=True).click()
   expect(page.locator('#main')).to_be_visible()
   expect(page.get_by_role('heading',level=1)).to_contain_text('招待された')
   record(engine+':reconnect-and-retry',True)
  except Exception as e:
   record(engine+':pwa-flow',False,error=str(e));page.screenshot(path=str(out/(engine+'-pwa-failure.png')),full_page=True)
  finally:context.close();browser.close()
assert checks and all(x['ok'] for x in checks)
