"""Test published QR screens without sending real mail or changing production records."""
import json,pathlib,os
from playwright.sync_api import sync_playwright,expect
BASE='https://mumei-s.github.io/muumei-public/'
OUT=pathlib.Path('verification');OUT.mkdir(exist_ok=True);checks=[]
def record(name,ok):
 checks.append({'name':name,'passed':bool(ok)});(OUT/'qr-live-result.json').write_text(json.dumps({'sourceRevision':os.environ['SOURCE_REVISION'],'real_registration_tested':False,'checks':checks},ensure_ascii=False,indent=2));print(name,ok,flush=True);assert ok,name
with sync_playwright() as p:
 browser=p.chromium.launch();context=browser.new_context(viewport={'width':390,'height':900},device_scale_factor=3);page=context.new_page();errors=[];requests=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 context.route('https://*.supabase.co/**',lambda r:(requests.append(r.request.url),r.abort()))
 page.goto(BASE+'demo/meet/',wait_until='networkidle');page.get_by_role('button',name='MEET PASSを発行',exact=True).click();expect(page.get_by_alt_text('対面招待のQRコード')).to_be_visible()
 token=page.evaluate("JSON.parse(localStorage.getItem('muumei-demo-v2')).meet_passes.filter(x=>x.status==='issued').at(-1).token")
 page.goto(BASE+'demo-receive/?source=spotwork#'+token,wait_until='networkidle');expect(page.get_by_role('heading',name='ムーメイへようこそ。')).to_be_visible();record('public QR opens community reception',True)
 page.get_by_role('button',name='招待を受け取って登録へ',exact=True).click();page.wait_for_url(lambda u:u.split('?')[0].rstrip('/').endswith('/demo/home'))
 receipt=page.evaluate("JSON.parse(localStorage.getItem('muumei-demo-v2-meet'))")
 record('primary action receives and saves before navigating',receipt['version']==1 and receipt['source']=='spotwork' and bool(receipt['claim']))
 record('one-time QR is consumed',page.evaluate("JSON.parse(localStorage.getItem('muumei-demo-v2')).meet_passes.filter(x=>x.status==='received').length")>0)
 page.goto(BASE+'demo-receive/?source=spotwork#'+token,wait_until='networkidle');expect(page.get_by_role('heading',name='招待を受け取りました。')).to_be_visible();record('received QR resumes after reload',True)
 page.goto(BASE+'demo/meet/',wait_until='networkidle');page.get_by_role('button',name='MEET PASSを発行',exact=True).click();expect(page.get_by_alt_text('対面招待のQRコード')).to_be_visible()
 another=page.evaluate("JSON.parse(localStorage.getItem('muumei-demo-v2')).meet_passes.filter(x=>x.status==='issued').at(-1).token")
 page.goto(BASE+'demo-receive/?source=direct#'+another,wait_until='networkidle');expect(page.get_by_role('heading',name='ムーメイへようこそ。')).to_be_visible();record('new QR does not reuse an unrelated receipt',True)
 page.get_by_role('button',name='あとで登録する（招待だけ受け取る）',exact=True).click();expect(page.get_by_role('heading',name='招待を受け取りました。')).to_be_visible();page.reload(wait_until='networkidle');expect(page.get_by_role('heading',name='招待を受け取りました。')).to_be_visible()
 record('deferred direct receipt survives reload',page.evaluate("JSON.parse(localStorage.getItem('muumei-demo-v2-meet')).source")=='direct')
 page.screenshot(path=str(OUT/'qr-reception-390-dpr3.png'),full_page=True)
 record('public receipt screen fits mobile width',page.evaluate('document.documentElement.scrollWidth-innerWidth')<=2)
 page.goto(BASE+'join/?source=spotwork&via=meet',wait_until='networkidle');expect(page.get_by_text('受け取った招待を確認できません。QRを受け取った同じブラウザで、7日以内に登録してください。',exact=True)).to_be_visible();record('missing real receipt does not silently submit registration',True)
 expect(page.get_by_role('button',name='確認メールを受け取る',exact=True)).to_be_disabled();record('unverified production signup is still closed',True)
 page.goto(BASE+'review/owner/demo/invites/',wait_until='networkidle')
 page.get_by_role('button',name='対面QRを発行する',exact=True).click()
 expect(page.get_by_label('招待する入口',exact=True)).to_be_visible()
 record('synthetic operator QR panel defaults to community',page.get_by_label('招待する入口',exact=True).input_value()=='spotwork')
 page.get_by_label('招待する入口',exact=True).select_option('direct')
 page.get_by_role('button',name='MEET PASSを発行',exact=True).click();expect(page.get_by_alt_text('対面招待のQRコード')).to_be_visible();record('synthetic operator can issue the separate direct QR',True)
 page.get_by_label('招待する入口',exact=True).select_option('spotwork');expect(page.get_by_alt_text('対面招待のQRコード')).to_have_count(0);record('switching QR entry clears the previous displayed code',True)
 record('no unhandled JavaScript errors',not errors);record('no real auth or database requests',not requests)
 browser.close()
print(len(checks),'published QR checks passed')
