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
CONTRAST_JS = "(element, options = {}) => {\n  const parse = value => {\n    if (value === 'transparent') return [0, 0, 0, 0];\n    const rgb = value.match(/^rgba?\\((.*)\\)$/);\n    if (rgb) {\n      const values = rgb[1].replace(/,/g, ' ').replace(/\\//g, ' ').trim().split(/\\s+/);\n      return values.map((v, i) => v.endsWith('%') ? parseFloat(v) * (i < 3 ? 2.55 : .01) : parseFloat(v)).concat([1]).slice(0, 4);\n    }\n    const srgb = value.match(/^color\\(srgb\\s+([^)]*)\\)$/);\n    if (srgb) {\n      const values = srgb[1].replace(/\\//g, ' ').trim().split(/\\s+/).map(Number);\n      return [values[0] * 255, values[1] * 255, values[2] * 255, values[3] ?? 1];\n    }\n    throw Error('Unsupported computed color: ' + value);\n  };\n  const over = (front, back) => {\n    const alpha = front[3] + back[3] * (1 - front[3]);\n    return [...front.slice(0, 3).map((v, i) => alpha ? (v * front[3] + back[i] * back[3] * (1 - front[3])) / alpha : 0), alpha];\n  };\n  const luminance = color => color.slice(0, 3).map(v => {\n    const s = v / 255;\n    return s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4;\n  }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);\n  const chain = [];\n  for (let node = element; node; node = node.parentElement) chain.push(getComputedStyle(node));\n  const scheme = getComputedStyle(document.documentElement).colorScheme;\n  let background = scheme === 'dark' ? [0, 0, 0, 1] : [255, 255, 255, 1];\n  let imageBacked = false;\n  for (const style of chain.reverse()) {\n    const color = parse(style.backgroundColor);\n    if (color[3] >= .999) imageBacked = false;\n    background = over(color, background);\n    if (style.backgroundImage !== 'none') imageBacked = true;\n  }\n  const style = getComputedStyle(element, options.pseudo || null);\n  const foreground = parse(style.color);\n  // Parent opacity also affects the final painted text. Current controls use\n  // explicit disabled colors rather than reducing the entire control opacity.\n  const opacity = chain.reduce((value, s) => value * Number(s.opacity || 1), 1);\n  foreground[3] *= opacity;\n  const painted = over(foreground, background);\n  const a = luminance(painted), b = luminance(background);\n  const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);\n  const size = parseFloat(style.fontSize), weight = parseInt(style.fontWeight, 10) || 400;\n  const large = size >= 24 || (size >= 18.666 && weight >= 700);\n  const rect = element.getBoundingClientRect();\n  return {ratio, required: large ? 3 : 4.5, foreground: style.color, background: background.map(v => Math.round(v * 100) / 100), fontSize: size, fontWeight: weight, imageBacked, visible: rect.width > 0 && rect.height > 0};\n}"

def assert_contrast(locator):
 expect(locator).to_be_visible()
 value=locator.evaluate(CONTRAST_JS,{})
 assert not value['imageBacked'],value
 assert value['ratio']+.01>=value['required'],value
 return value

checks=[]
def record(name,ok,**kw):
 checks.append(dict(name=name,ok=bool(ok),**kw));(out/'social-browser.json').write_text(json.dumps(dict(live=target.startswith('https://'),production_data_mutated=False,checks=checks,total=len(checks),failures=sum(not x['ok'] for x in checks)),ensure_ascii=False,indent=2));print(name,'PASS' if ok else 'FAIL',kw,flush=True)
routes=['','entry/qr/','entry/invite/','entry/member/','install/','login','receive','invite','jobs?source=direct','direct','review/member/demo/home','review/member/demo/moments','review/member/demo/next','review/member/demo/people','review/member/demo/pass','review/member/demo/join','review/member/demo/messages','review/member/demo/install','review/member/demo/notifications','review/member/demo/my','review/owner/demo/moments','review/owner/demo/referrals','review/owner/demo/audit','review/owner/demo/invites','review/owner/demo/approvals','review/owner/demo/next']
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
      if route=='login':
       expect(page.get_by_role('alert')).to_contain_text('通信状態を確認',timeout=15000)
       expect(page.get_by_role('button',name='再読み込み',exact=True)).to_be_visible()
       expect(page.get_by_role('button',name='確認メールを受け取る',exact=False)).to_be_disabled()
      if route=='review/member/demo/home':
       h=page.locator('.home-feature-copy h2');metrics=h.evaluate('(e)=>({height:e.getBoundingClientRect().height,line:parseFloat(getComputedStyle(e).lineHeight)})');assert metrics['height']<=metrics['line']*2+3,'Home copy wraps inside a phrase'
      if route=='':
       assert not any(t in state['text'] for t in ['タイミー','QR発行','OWNER管理'])
       expect(page.locator('.sns-hero-label')).to_have_text('招待制プライベートSNS')
       expect(page.get_by_role('link',name='あなたの入口を選ぶ',exact=True)).to_be_visible()
       expect(page.locator('.sns-entry-card')).to_have_count(3)
       expect(page.locator('.public-footer > .sample-entry-panel:last-child')).to_be_visible()
       assert page.locator('.public-footer .sample-entry-panel').evaluate('(e)=>e.getBoundingClientRect().top')>page.locator('.sns-entry-grid').evaluate('(e)=>e.getBoundingClientRect().bottom')
       expect(page.get_by_role('button',name='ホーム画面に追加',exact=True)).to_be_enabled()
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
      page.goto(base+'review/member/demo/messages',wait_until='networkidle');page.locator('.thread-list a.person-row').first.click();expect(page.get_by_role('textbox',name='メッセージ',exact=True)).to_be_visible();page.get_by_role('textbox',name='メッセージ',exact=True).fill('チャットの保存試験');page.get_by_role('button',name='送信',exact=True).click();expect(page.get_by_text('チャットの保存試験',exact=True)).to_be_visible();page.reload(wait_until='networkidle');expect(page.get_by_text('チャットの保存試験',exact=True)).to_be_visible()
      bubble=page.locator('.bubble.mine').filter(has=page.get_by_text('チャットの保存試験',exact=True));tombstones=page.locator('.bubble.deleted').count()
      bubble.get_by_role('button',name='送信を取り消す',exact=True).click();dialog=page.get_by_role('dialog');expect(dialog).to_be_visible();dialog.get_by_role('button',name='やめる',exact=True).click();expect(dialog).to_be_hidden();expect(bubble.get_by_text('チャットの保存試験',exact=True)).to_be_visible()
      bubble.get_by_role('button',name='送信を取り消す',exact=True).click();dialog.get_by_role('button',name='取り消す',exact=True).click();expect(dialog).to_be_hidden();expect(page.get_by_text('チャットの保存試験',exact=True)).to_have_count(0);expect(page.locator('.bubble.deleted')).to_have_count(tombstones+1)
      page.reload(wait_until='networkidle');expect(page.get_by_text('チャットの保存試験',exact=True)).to_have_count(0);expect(page.locator('.bubble.deleted')).to_have_count(tombstones+1);expect(page.locator('.bubble.deleted').last).to_contain_text('メッセージの送信が取り消されました');record(engine+':owner-chat-send-cancel-unsend-history-reload',True)
     except Exception as e:record(engine+':owner-chat-send-cancel-unsend-history-reload',False,error=str(e))
     try:
      page.goto(base+'review/member/demo/pass',wait_until='networkidle');page.get_by_role('button',name='ロゼ',exact=True).click();page.reload(wait_until='networkidle');expect(page.locator('.member-pass')).to_have_class('member-pass skin-rose');record(engine+':pass-skin-persists',True)
      page.goto(base+'jobs?source=direct',wait_until='networkidle');page.locator('[data-action="job-sample"]').click();expect(page.locator('a.job-card').first).to_be_visible();job=page.locator('a.job-card').first;title=job.locator('h3').inner_text();job.click();expect(page.locator('.detail-hero h1')).to_have_text(title);page.reload(wait_until='networkidle');expect(page.locator('.detail-hero h1')).to_have_text(title);record(engine+':shared-jobs-detail-refresh',True)
     except Exception as e:record(engine+':pass-jobs-flow',False,error=str(e))
     try:
      page.goto(base+'review/',wait_until='networkidle');view=page.frame_locator('#view');expect(view.locator('.home-feature-copy')).to_be_visible();expect(page.locator('#load-status')).to_contain_text('表示完了')
      view.get_by_role('link',name='Moments',exact=True).first.click();expect(view.get_by_role('textbox',name='今日のひとこと')).to_be_visible();expect(page.locator('#load-status')).to_contain_text('表示完了')
      page.get_by_role('button',name='確認用管理画面',exact=True).click();view.get_by_role('button',name='Toggle Sidebar',exact=True).click();expect(view.get_by_role('link',name='招待',exact=True)).to_be_visible();view.get_by_role('link',name='招待',exact=True).click();expect(view.get_by_role('textbox',name='招待先のメールアドレス',exact=False)).to_be_visible();expect(page.locator('#load-status')).to_contain_text('表示完了')
      assert_contrast(view.locator('.heading h1').first)
      record(engine+':review-iframe-navigation-status-and-heading-contrast',True)
     except Exception as e:record(engine+':review-iframe-navigation-status-and-heading-contrast',False,error=str(e));page.screenshot(path=str(out/(engine+'-review-shell-failure.png')),full_page=True)
    context.close()
   browser.close()
finally:
 if server:server.shutdown()
assert checks and all(x['ok'] for x in checks),f'{sum(not x["ok"] for x in checks)} browser checks failed'
