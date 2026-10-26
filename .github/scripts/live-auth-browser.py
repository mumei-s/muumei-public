"""Read-only real browser check: configuration loads and an unauthenticated login gate works."""
import json,pathlib,sys
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect
base=sys.argv[1].rstrip('/')+'/'
assert base=='https://mumei-s.github.io/muumei-public/'
endpoint='https://slamzhgsawfnmwlejgqp.supabase.co/functions/v1/public-config'
out=pathlib.Path('verification');out.mkdir(exist_ok=True)
checks=[];network=[]
def record(name,ok,**details):
 checks.append(dict(name=name,ok=ok,**details))
 (out/'live-auth-browser.json').write_text(json.dumps(dict(live=True,production_data_mutated=False,total=len(checks),failures=sum(not x['ok'] for x in checks),checks=checks,network=network),ensure_ascii=False,indent=2))
 print(name,'PASS' if ok else 'FAIL',details,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch();context=browser.new_context(viewport={'width':390,'height':844},service_workers='block')
 # Only the public configuration GET may reach Supabase. No auth, email, RPC or production write is sent.
 context.route('https://*.supabase.co/**',lambda route:route.continue_() if route.request.method=='GET' and route.request.url==endpoint else route.abort())
 page=context.new_page()
 def response(r):
  if r.url==endpoint:network.append(dict(path='/functions/v1/public-config',status=r.status))
 def failed(r):
  if r.url==endpoint:network.append(dict(path='/functions/v1/public-config',failure=r.failure))
 page.on('response',response);page.on('requestfailed',failed)
 try:
  page.goto(base+'app/home/',wait_until='domcontentloaded')
  expect(page.get_by_role('heading',name='ログイン',exact=True)).to_be_visible(timeout=20000)
  expect(page.get_by_role('button',name='確認メールを受け取る',exact=False)).to_be_enabled(timeout=20000)
  record('Real member entry resolves configuration and shows a usable login gate',True)
  assert any(x.get('status')==200 for x in network),'No successful public-config response'
  record('Browser CORS accepts the dedicated public configuration endpoint',True)
  page.reload(wait_until='domcontentloaded')
  expect(page.get_by_role('heading',name='ログイン',exact=True)).to_be_visible(timeout=20000)
  expect(page.get_by_role('button',name='確認メールを受け取る',exact=False)).to_be_enabled(timeout=20000)
  record('Login gate remains usable after refresh',True)
 except Exception as e:
  record('Real anonymous connection',False,error=str(e));page.screenshot(path=str(out/'live-auth-failure-390.png'),full_page=True)
 finally:context.close();browser.close()
assert checks and not any(not x['ok'] for x in checks)
