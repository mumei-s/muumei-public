"""Check public/member/operator boundaries using disposable synthetic browser data only."""
import json,pathlib,os,re
from playwright.sync_api import sync_playwright,expect
BASE='https://mumei-s.github.io/muumei-public/'
OUT=pathlib.Path('verification');OUT.mkdir(exist_ok=True);checks=[]
def record(name,ok):
 checks.append({'name':name,'passed':bool(ok)});(OUT/'qr-live-result.json').write_text(json.dumps({'sourceRevision':os.environ['SOURCE_REVISION'],'real_registration_tested':False,'checks':checks},ensure_ascii=False,indent=2));print(name,ok,flush=True);assert ok,name
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in [320,390,1280]:
  ctx=browser.new_context(viewport={'width':width,'height':900},device_scale_factor=3 if width==390 else 1,reduced_motion='reduce');page=ctx.new_page()
  ctx.route('https://*.supabase.co/**',lambda r:r.abort())
  for route in ['', 'demo/home/', 'demo/crew/', 'demo/boards/', 'demo/my/', 'review/member/demo/home/']:
   page.goto(BASE+route,wait_until='networkidle');expect(page.locator('#main')).to_be_visible()
   record(f'{width}:{route}:no-operator-QR',page.get_by_alt_text('対面招待のQRコード').count()==0 and page.get_by_role('button',name=re.compile('PASSを発行|対面QRを発行')).count()==0)
   record(f'{width}:{route}:no-management-links',page.locator('a[href*="/meet"],a[href*="/invites"],a[href*="/approvals"],a[href*="/review/owner/"]').count()==0)
   record(f'{width}:{route}:no-overflow',page.evaluate('document.documentElement.scrollWidth-innerWidth')<=2)
   if not route:
    record(f'{width}:no-demo-review-entry-on-community-top',page.locator('a[href*="/demo"],a[href*="/review"]').count()==0)
    record(f'{width}:only-three-member-shortcuts',page.locator('.community-shortcuts>a').count()==3)
   else:
    record(f'{width}:{route}:clear-demo-with-no-logout',page.locator('[data-environment="demo"]').count()==1 and page.locator('.demo-banner').is_visible() and page.get_by_role('button',name='ログアウト',exact=True).count()==0)
  for route in ['app/meet/','demo/meet/','review/member/demo/meet/']:
   page.goto(BASE+route,wait_until='networkidle');expect(page.get_by_role('heading',name='このページは利用できません',exact=True)).to_be_visible();record(f'{width}:{route}:old-QR-route-closed',True)
  for source in ['community','direct']:
   page.goto(BASE+'jobs/?source='+source,wait_until='networkidle');page.locator('[data-action="job-sample"]').click();expect(page.locator('.job-card').first).to_be_visible();record(f'{width}:{source}:sample-available','source='+source in page.url)
   page.get_by_role('link',name='見本を終了して求人ページへ',exact=True).click();expect(page.locator('[data-page="shared-jobs"]')).to_be_visible();record(f'{width}:{source}:explicit-return-to-common-jobs','source='+source in page.url)
  ctx.close()
 context=browser.new_context(viewport={'width':390,'height':900},device_scale_factor=3);page=context.new_page();errors=[];requests=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 context.route('https://*.supabase.co/**',lambda r:(requests.append(r.request.url),r.abort()))
 def issue():
  page.goto(BASE+'review/owner/demo/invites/',wait_until='networkidle');page.get_by_role('button',name='対面QRを発行する',exact=True).click();expect(page.get_by_text('確認用QR・本登録不可',exact=True)).to_be_visible()
  page.get_by_role('button',name='MEET PASSを発行',exact=True).click();expect(page.get_by_alt_text('対面招待のQRコード')).to_be_visible()
  return page.evaluate("JSON.parse(localStorage.getItem('muumei-review-v1')).meet_passes.filter(x=>x.status==='issued').at(-1).token")
 token=issue();page.goto(BASE+'review/member/demo-receive/?source=spotwork#'+token,wait_until='networkidle');expect(page.get_by_role('heading',name='ムーメイへようこそ。')).to_be_visible();record('QR opens community reception',True)
 page.get_by_role('button',name='招待を受け取って登録へ',exact=True).click();page.wait_for_url(lambda u:u.split('?')[0].rstrip('/').endswith('/demo/home'))
 receipt=page.evaluate("JSON.parse(localStorage.getItem('muumei-review-v1-meet'))")
 record('primary action receives and saves before navigating',receipt['version']==1 and receipt['source']=='spotwork' and bool(receipt['claim']))
 record('one-time QR is consumed',page.evaluate("JSON.parse(localStorage.getItem('muumei-review-v1')).meet_passes.filter(x=>x.status==='received').length")>0)
 page.goto(BASE+'review/member/demo-receive/?source=spotwork#'+token,wait_until='networkidle');expect(page.get_by_role('heading',name='招待を受け取りました。')).to_be_visible();record('received QR resumes after reload',True)
 another=issue();page.goto(BASE+'review/member/demo-receive/?source=direct#'+another,wait_until='networkidle');expect(page.get_by_role('heading',name='ムーメイへようこそ。')).to_be_visible();record('new QR does not reuse an unrelated receipt',True)
 page.get_by_role('button',name='あとで登録する（招待だけ受け取る）',exact=True).click();expect(page.get_by_role('heading',name='招待を受け取りました。')).to_be_visible();page.reload(wait_until='networkidle');expect(page.get_by_role('heading',name='招待を受け取りました。')).to_be_visible()
 record('deferred direct receipt survives reload',page.evaluate("JSON.parse(localStorage.getItem('muumei-review-v1-meet')).source")=='direct')
 record('receipt screen fits mobile width',page.evaluate('document.documentElement.scrollWidth-innerWidth')<=2)
 page.goto(BASE+'join/?source=spotwork&via=meet',wait_until='networkidle');expect(page.get_by_text('受け取った招待を確認できません。QRを受け取った同じブラウザで、7日以内に登録してください。',exact=True)).to_be_visible();record('missing real receipt does not silently submit registration',True)
 expect(page.get_by_role('button',name='確認メールを受け取る',exact=True)).to_be_disabled();record('unverified production signup is still closed',True)
 page.goto(BASE+'review/owner/demo/invites/',wait_until='networkidle');page.get_by_role('button',name='対面QRを発行する',exact=True).click();expect(page.get_by_label('招待する入口',exact=True)).to_be_visible()
 record('synthetic operator QR panel defaults to community',page.get_by_label('招待する入口',exact=True).input_value()=='spotwork')
 page.get_by_label('招待する入口',exact=True).select_option('direct');page.get_by_role('button',name='MEET PASSを発行',exact=True).click();expect(page.get_by_alt_text('対面招待のQRコード')).to_be_visible();record('synthetic operator can issue the separate direct QR',True)
 page.get_by_label('招待する入口',exact=True).select_option('spotwork');expect(page.get_by_alt_text('対面招待のQRコード')).to_have_count(0);record('switching QR entry clears the previous displayed code',True)
 page.goto(BASE+'review/',wait_until='networkidle');expect(page.locator('#load-status')).to_contain_text('表示完了',timeout=20000)
 record('review explicitly is not live administration','本番登録・管理はできません' in page.locator('header').inner_text())
 record('review header does not escape to production',page.locator('header a').count()==0)
 page.get_by_role('button',name='確認用管理画面',exact=True).click();expect(page.locator('#load-status')).to_contain_text('確認用管理画面',timeout=20000);page.screenshot(path=str(OUT/'separated-review-390-dpr3.png'),full_page=True)
 record('no unhandled JavaScript errors',not errors);record('no real auth or database requests',not requests)
 browser.close()
print(len(checks),'published boundary and QR checks passed')
