"""Read public pages and mutate only disposable browser-local demo data."""
import json, os, pathlib, time, urllib.request
from playwright.sync_api import sync_playwright, expect
BASE='https://mumei-s.github.io/muumei-public/'
REV=os.environ['SOURCE_REVISION']
OUT=pathlib.Path('verification');OUT.mkdir(exist_ok=True)
checks=[]
def record(name,ok=True,**details):
 checks.append({'name':name,'ok':bool(ok),**details})
 (OUT/'live-result.json').write_text(json.dumps({'sourceRevision':REV,'real_registration_tested':False,'checks':checks},ensure_ascii=False,indent=2))
 print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
 assert ok,name
for attempt in range(30):
 try:
  with urllib.request.urlopen(BASE+'build-info.json?v='+REV,timeout=15) as response: info=json.load(response)
  if info.get('sourceRevision')==REV: break
 except Exception: pass
 time.sleep(3)
else: raise RuntimeError('Expected published revision is not visible')
record('published-revision',info.get('sourceRevision')==REV)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in [320,390,1280]:
  context=browser.new_context(viewport={'width':width,'height':900},device_scale_factor=3 if width==390 else 1,has_touch=width<641,reduced_motion='reduce')
  context.route('https://*.supabase.co/**',lambda r:r.abort())
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  try:
   for route in ['', 'jobs/?source=direct', 'direct/', 'demo/home/', 'demo/boards/', 'demo/work/']:
    response=page.goto(BASE+route+('&' if '?' in route else '?')+'v='+REV,wait_until='networkidle')
    expect(page.locator('#main')).to_be_visible(timeout=20000)
    record(f'{width}:{route}:layout',response.status==200 and page.evaluate('document.documentElement.scrollWidth-innerWidth')<=2)
    record(f'{width}:{route}:LINE-hidden','LINE' not in page.inner_text('body'))
    record(f'{width}:{route}:images',page.locator('img').evaluate_all('(xs)=>xs.every(x=>x.complete&&x.naturalWidth>0)'))
    if route=='':
     record(f'{width}:community-first',all(x not in page.inner_text('#main') for x in ['求人見本','報酬','準備中','体験する']))
     record(f'{width}:production-entry',page.locator('.community-hero .m-button').get_attribute('href').endswith('/app/home'))
     record(f'{width}:collapsed-explanations',page.locator('details[open]').count()==0 and page.locator('details').count()>=3)
     page.locator('details summary').first.click();expect(page.locator('details').first).to_have_attribute('open','');page.locator('details summary').first.click();record(f'{width}:panel-opens-closes')
     photos=page.locator('.workplace-mosaic img').evaluate_all('(xs)=>xs.map(x=>({url:x.currentSrc,w:x.naturalWidth,h:x.naturalHeight}))')
     record(f'{width}:varied-high-resolution-photos',len({x['url'] for x in photos})==4 and all(x['w']>=1600 for x in photos),photos=photos)
     for method in (['click','tap'] if width<641 else ['click']):
      getattr(page.get_by_role('button',name='メニューを開く'),method)();expect(page.get_by_role('navigation',name='サイトメニュー')).to_be_visible()
      if method=='tap':page.touchscreen.tap(2,880)
      else:page.mouse.click(2,880)
      expect(page.get_by_role('navigation',name='サイトメニュー')).to_be_hidden();record(f'{width}:menu-{method}-outside-close')
     page.get_by_role('button',name='メニューを開く').click();page.keyboard.press('Escape');expect(page.get_by_role('navigation',name='サイトメニュー')).to_be_hidden();record(f'{width}:menu-escape')
     if width==390:page.screenshot(path=str(OUT/'community-390-dpr3.png'),full_page=True)
     page.locator('[data-entry="community-jobs"]').click();expect(page.locator('[data-page="shared-jobs"]')).to_be_visible();record(f'{width}:community-to-common-jobs')
    elif route.startswith(('jobs','direct')):
     if width==390 and route.startswith('direct'):page.screenshot(path=str(OUT/'direct-390-dpr3.png'),full_page=True)
     page.locator('[data-action="job-sample"]').click();expect(page.locator('.job-card').first).to_be_visible();record(f'{width}:{route}:sample-accessible')
     page.locator('a.job-card').first.click();expect(page.locator('#main')).to_be_visible();page.reload(wait_until='networkidle');expect(page.locator('#main')).to_be_visible();record(f'{width}:{route}:sample-detail-reload')
   record(f'{width}:no-js-errors',not errors,errors=errors)
  except Exception as exc:
   page.screenshot(path=str(OUT/f'failure-{width}.png'),full_page=True);record(f'{width}:exception',False,error=str(exc),url=page.url)
  finally:context.close()
 context=browser.new_context(viewport={'width':390,'height':900},device_scale_factor=3,reduced_motion='reduce');page=context.new_page();calls=[]
 context.on('request',lambda req:calls.append(req.url) if '.supabase.co/' in req.url else None)
 try:
  for entry in ['demo','review/member/demo']:
   page.goto(BASE+entry+'/boards/',wait_until='networkidle');page.locator('a.card').first.click();expect(page.locator('textarea')).to_be_visible()
   marker='削除確認-'+entry;page.locator('textarea').fill(marker);page.get_by_role('button',name='投稿する',exact=True).click()
   post=page.locator('article.card').filter(has_text=marker);expect(post).to_be_visible();record(entry+':comment-created')
   post.get_by_role('button',name='削除',exact=True).click();post.get_by_role('button',name='キャンセル',exact=True).click();expect(post).to_be_visible();record(entry+':cancel-preserves-comment')
   post.get_by_role('button',name='削除',exact=True).click();post.get_by_role('button',name='削除する',exact=True).click();expect(post).to_have_count(0);page.reload(wait_until='networkidle');expect(page.locator('article.card').filter(has_text=marker)).to_have_count(0);record(entry+':deletion-survives-reload')
  page.goto(BASE+'review/owner/demo/boards/',wait_until='networkidle');expect(page.locator('#main')).to_be_visible();record('review:owner-LINE-hidden','LINE' not in page.inner_text('body'))
  delete=page.get_by_role('button',name='削除',exact=True).first;expect(delete).to_be_visible();delete.click();page.get_by_role('button',name='削除する',exact=True).first.click();record('review:owner-can-delete')
  page.goto(BASE+'review/',wait_until='networkidle');expect(page.locator('#load-status')).to_contain_text('表示完了',timeout=20000);record('review:visible-load-completion')
  page.get_by_role('button',name='確認用管理画面',exact=True).click();expect(page.locator('iframe')).to_have_attribute('src','owner/demo/dashboard/');expect(page.locator('#load-status')).to_contain_text('確認用管理画面',timeout=20000);record('review:member-owner-switch')
  page.get_by_role('button',name='不具合をメモ',exact=True).click();page.locator('#description').fill('実公開画面の動作確認');page.reload(wait_until='networkidle');page.get_by_role('button',name='不具合をメモ',exact=True).click();expect(page.locator('#description')).to_have_value('実公開画面の動作確認');record('review:note-persistence')
  page.screenshot(path=str(OUT/'review-390-dpr3.png'),full_page=True)
  page.evaluate("localStorage.setItem('muumei-app','preserve');localStorage.setItem('note-insight-sentinel','preserve');localStorage.setItem('muumei-review-v1-meet','receipt');localStorage.setItem('muumei-review-v1-draft-test','draft')")
  page.on('dialog',lambda d:d.accept());page.get_by_role('button',name='確認データをリセット').click();page.wait_for_timeout(800)
  record('review:reset-keeps-production-and-other-tools',page.evaluate("localStorage.getItem('muumei-app')==='preserve'&&localStorage.getItem('note-insight-sentinel')==='preserve'"))
  record('review:reset-only-review-receipts-drafts',page.evaluate("!localStorage.getItem('muumei-review-v1-meet')&&!localStorage.getItem('muumei-review-v1-draft-test')"))
  record('demo:no-production-network',not calls,calls=calls)
  for part in ['member','owner']:
   config=context.request.get(BASE+'review/'+part+'/muumei-config.json').json();record('review:'+part+':no-live-config',not config['url'] and not config['key'] and config['ready'] is False)
 except Exception as exc:
  page.screenshot(path=str(OUT/'review-failure.png'),full_page=True);record('review:exception',False,error=str(exc),url=page.url)
 finally:context.close();browser.close()
print(str(len(checks))+' live checks passed')
