import sys,json,pathlib,threading,http.server,functools,time,os
from playwright.sync_api import sync_playwright,expect
target=sys.argv[1] if len(sys.argv)>1 else 'release/app'
out=pathlib.Path('verification');out.mkdir(exist_ok=True)
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
   p=root/local
   if not p.resolve().is_relative_to(root):return str(root/'404.html')
   return str(p if p.exists() else root/'404.html')
 server=http.server.ThreadingHTTPServer(('127.0.0.1',4188),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:4188/muumei-public/'
checks=[]
def record(name,ok,**kw):
 checks.append(dict(name=name,ok=bool(ok),**kw));(out/'social-browser.json').write_text(json.dumps(dict(live=target.startswith('https://'),production_data_mutated=False,checks=checks,total=len(checks),failures=sum(not x['ok'] for x in checks)),ensure_ascii=False,indent=2));print(name,'PASS' if ok else 'FAIL',kw,flush=True)
routes=['','login','receive','invite','jobs?source=direct','direct','review/member/demo/home','review/member/demo/moments','review/member/demo/next','review/member/demo/people','review/member/demo/pass','review/member/demo/join','review/member/demo/messages','review/member/demo/install','review/member/demo/notifications','review/member/demo/my','review/owner/demo/moments','review/owner/demo/referrals','review/owner/demo/audit','review/owner/demo/invites','review/owner/demo/approvals','review/owner/demo/next']
try:
 with sync_playwright() as p:
  for engine in os.environ.get('MUUMEI_BROWSER_ENGINES','chromium,firefox,webkit').split(','):
   browser=getattr(p,engine).launch()
   for width in [360,390,430,768,820,1024,1280,1440]:
    context=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce',service_workers='block');context.route('https://*.supabase.co/**',lambda r:r.abort())
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    for route in routes:
     name=f'{engine}:{width}:{route or "top"}'
     try:
      response=page.goto(base+route,wait_until='networkidle');expect(page.locator('#main')).to_be_visible(timeout=20000)
      state=page.evaluate('''() => ({overflow:document.documentElement.scrollWidth-innerWidth,broken:[...document.images].filter(i=>i.getBoundingClientRect().top<innerHeight&&i.getBoundingClientRect().bottom>0&&(!i.complete||!i.naturalWidth)).map(i=>i.getAttribute('src')),text:document.querySelector('#main').innerText})''')
      assert response.status==200,f'HTTP {response.status}'
      assert state['overflow']<=2,f'overflow {state["overflow"]}'
      assert not state['broken'],f'broken images {state["broken"]}'
      assert not errors,f'JS errors {errors}'
      assert 'このページは見つかりません' not in state['text']
      if route=='review/member/demo/home':
       h=page.locator('.home-feature-copy h2');metrics=h.evaluate('(e)=>({height:e.getBoundingClientRect().height,line:parseFloat(getComputedStyle(e).lineHeight)})');assert metrics['height']<=metrics['line']*2+3,'Home copy wraps inside a phrase'
      if route=='':
       assert not any(t in state['text'] for t in ['タイミー','QR発行','OWNER管理','DEMO','操作確認'])
       page.get_by_role('button',name='メニューを開く',exact=True).click();expect(page.get_by_role('navigation',name='サイトメニュー')).to_be_visible();page.keyboard.press('Escape');expect(page.get_by_role('navigation',name='サイトメニュー')).to_be_hidden()
      record(name,True)
      if width==390 and route in ['', 'review/member/demo/home','review/member/demo/moments','review/member/demo/next','review/member/demo/pass','receive']:
       page.screenshot(path=str(out/(engine+'-'+(route.replace('/','-') or 'top')+'-390.png')),full_page=True)
     except Exception as e:
      record(name,False,error=str(e));page.screenshot(path=str(out/(engine+'-failure-'+str(width)+'.png')),full_page=True)
     errors.clear()
    if width==390:
     try:
      page.goto(base+'review/member/demo/moments',wait_until='networkidle');page.get_by_role('textbox',name='今日のひとこと').fill('ブラウザ試験のひとこと');page.get_by_role('button',name='投稿する',exact=True).click();expect(page.get_by_text('ブラウザ試験のひとこと',exact=True)).to_be_visible();page.reload(wait_until='networkidle');expect(page.get_by_text('ブラウザ試験のひとこと',exact=True)).to_be_visible()
      post=page.locator('article.moment').filter(has=page.get_by_text('ブラウザ試験のひとこと',exact=True));post.get_by_role('button',name='スキ',exact=True).click();expect(post.get_by_role('button',name='スキ',exact=True)).to_have_attribute('aria-pressed','true');post.get_by_role('button').filter(has=page.locator('svg.lucide-message-circle')).click()
      post.get_by_role('textbox',name='コメント',exact=True).fill('自分のコメント');post.get_by_role('button',name='コメントを送信').click();expect(post.get_by_text('自分のコメント',exact=True)).to_be_visible();post.get_by_role('button',name='自分のコメントを削除').click();page.get_by_role('button',name='削除する',exact=True).click();expect(post.get_by_text('自分のコメント',exact=True)).to_have_count(0)
      post.get_by_role('button',name='自分の投稿を削除').click();page.get_by_role('button',name='削除する',exact=True).click();expect(page.get_by_text('ブラウザ試験のひとこと',exact=True)).to_have_count(0)
      record(engine+':post-like-comment-delete-reload',True)
     except Exception as e:record(engine+':post-like-comment-delete-reload',False,error=str(e));page.screenshot(path=str(out/(engine+'-flow-failure.png')),full_page=True)
     try:
      page.goto(base+'review/member/demo/next',wait_until='networkidle');item=page.locator('.next-item').first;item.get_by_role('button',name='気になる',exact=False).click();expect(item.get_by_role('button',name='気になる',exact=False)).to_have_attribute('aria-pressed','true');item.get_by_role('button',name='詳細',exact=False).click();item.get_by_role('button',name='参加したい',exact=True).click();expect(item.get_by_role('button',name='参加希望を取り消す')).to_be_visible();page.reload(wait_until='networkidle');expect(page.locator('.next-item').first.get_by_role('button',name='気になる',exact=False)).to_have_attribute('aria-pressed','true');record(engine+':next-reactions-persist',True)
     except Exception as e:record(engine+':next-reactions-persist',False,error=str(e))
     try:
      page.goto(base+'review/member/demo/messages',wait_until='networkidle');page.locator('.thread-list a.person-row').first.click();expect(page.get_by_role('textbox',name='メッセージ',exact=True)).to_be_visible();page.get_by_role('textbox',name='メッセージ',exact=True).fill('チャットの保存試験');page.get_by_role('button',name='送信',exact=True).click();expect(page.get_by_text('チャットの保存試験',exact=True)).to_be_visible();page.reload(wait_until='networkidle');expect(page.get_by_text('チャットの保存試験',exact=True)).to_be_visible();record(engine+':owner-chat-send-history-reload',True)
     except Exception as e:record(engine+':owner-chat-send-history-reload',False,error=str(e))
     try:
      page.goto(base+'review/member/demo/pass',wait_until='networkidle');page.get_by_role('button',name='ロゼ',exact=True).click();page.reload(wait_until='networkidle');expect(page.locator('.member-pass')).to_have_class('member-pass skin-rose');record(engine+':pass-skin-persists',True)
      page.goto(base+'jobs?source=direct',wait_until='networkidle');page.locator('[data-action="job-sample"]').click();expect(page.locator('a.job-card').first).to_be_visible();job=page.locator('a.job-card').first;title=job.locator('h3').inner_text();job.click();expect(page.locator('.detail-hero h1')).to_have_text(title);page.reload(wait_until='networkidle');expect(page.locator('.detail-hero h1')).to_have_text(title);record(engine+':shared-jobs-detail-refresh',True)
     except Exception as e:record(engine+':pass-jobs-flow',False,error=str(e))
     try:
      page.goto(base+'review/',wait_until='networkidle');view=page.frame_locator('#view');expect(view.locator('.home-feature-copy')).to_be_visible();expect(page.locator('#load-status')).to_contain_text('表示完了')
      view.get_by_role('link',name='Moments',exact=True).first.click();expect(view.get_by_role('textbox',name='今日のひとこと')).to_be_visible();expect(page.locator('#load-status')).to_contain_text('表示完了')
      page.get_by_role('button',name='確認用管理画面',exact=True).click();view.get_by_role('button',name='Toggle Sidebar',exact=True).click();expect(view.get_by_role('link',name='招待',exact=True)).to_be_visible();view.get_by_role('link',name='招待',exact=True).click();expect(view.get_by_role('textbox',name='招待先のメールアドレス',exact=False)).to_be_visible();expect(page.locator('#load-status')).to_contain_text('表示完了')
      color=view.locator('.heading').first.evaluate('(e)=>({color:getComputedStyle(e).color,background:getComputedStyle(e).backgroundColor})');assert color['color']=='rgb(28, 33, 27)' and color['background']=='rgba(0, 0, 0, 0)',color
      record(engine+':review-iframe-navigation-status-and-heading-contrast',True)
     except Exception as e:record(engine+':review-iframe-navigation-status-and-heading-contrast',False,error=str(e));page.screenshot(path=str(out/(engine+'-review-shell-failure.png')),full_page=True)
    context.close()
   browser.close()
finally:
 if server:server.shutdown()
assert checks and all(x['ok'] for x in checks),f'{sum(not x["ok"] for x in checks)} browser checks failed'
