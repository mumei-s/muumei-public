"""Exercise the public/member-sample separation without real writes or sign-in.

Run in the official Playwright CI image. The deployment consists of the ordinary
public introduction, retained real member/auth routes and one member-only sample.
Every request other than same-origin GET/HEAD is blocked. Protected personal terms
are represented only by length and digest, so this verifier can be public safely.
"""
import hashlib
import http.server
import json
import os
import pathlib
import re
import sys
import threading
import traceback
import unicodedata
from urllib.parse import unquote, urlsplit

WIDTHS = [344, 360, 390, 430, 768, 820, 1024, 1280, 1440]
SCHEMES = ['light', 'dark']


def evidence_storage(directory):
    """Capacity only: never include page content, user values or credentials."""
    path = pathlib.Path(directory).resolve()
    while not path.exists() and path != path.parent:
        path = path.parent
    try:
        value = os.statvfs(path)
        return dict(available_bytes=value.f_bavail * value.f_frsize,
                    capacity_bytes=value.f_blocks * value.f_frsize,
                    available_inodes=value.f_favail, capacity_inodes=value.f_files)
    except OSError as error:
        return dict(storage_diagnostic_errno=error.errno)


class EvidenceError(RuntimeError):
    """A persistence failure is infrastructure failure, never an app result."""


class EvidenceRecorder:
    """Append small durable case records; write the full network report once."""

    def __init__(self, directory):
        self.directory = pathlib.Path(directory)
        self.journal = self.directory / 'public-experience-browser.jsonl'
        self.output = self.directory / 'public-experience-browser.json'
        self.checks, self.infrastructure_errors, self.unpersisted_checks = [], [], []
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            # Do not silently overwrite a prior run's journal or its failures.
            with self.journal.open('x', encoding='utf-8'):
                pass
        except OSError as error:
            self.fail('initialize', error)

    def fail(self, operation, error, case=None):
        diagnostic = dict(operation=operation, errno=error.errno,
                          storage=evidence_storage(self.directory))
        if case is not None:
            diagnostic['case'] = case
        self.infrastructure_errors.append(diagnostic)
        print('evidence-infrastructure-error', json.dumps(diagnostic), file=sys.stderr, flush=True)
        raise EvidenceError(json.dumps(diagnostic)) from error

    def _append(self, serialized):
        with self.journal.open('a', encoding='utf-8') as stream:
            stream.write(serialized + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def record(self, name, ok, **details):
        row = dict(name=name, ok=bool(ok), **details)
        try:
            self._append(json.dumps(row, ensure_ascii=False, separators=(',', ':')))
        except OSError as error:
            # Retain the attempted case in the final infrastructure report,
            # without appending an unjournalled PASS or a duplicate FAIL.
            self.unpersisted_checks.append(row)
            self.fail('append-case', error, case=name)
        self.checks.append(row)

    def _write_final(self, result):
        temporary = self.output.with_suffix('.json.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.output)

    def finalize(self, result):
        if self.infrastructure_errors:
            result = dict(result, infrastructure_failures=len(self.infrastructure_errors),
                          infrastructure_errors=self.infrastructure_errors,
                          unpersisted_checks=self.unpersisted_checks)
        try:
            self._write_final(result)
        except OSError as error:
            self.fail('finalize', error)


PROTECTED_DIGESTS = [
    (2, '6eb83dbe86f7b95e59a9f34ad22223bdf0447dccd5efdf14c0f93a4f5b42dc7e'),
    (3, '7bb283a4ef4da4990d3c9e9a952f3407f6a7e88fa688081c65672907c82912a1'),
    (4, '6303b6201cd174398e1653b126e885ee039cc317b38db6c15560ea3ecf427012'),
    (3, '9b9eb8763cf388b70eac221cb7c91c97bc9d32cac4eec80e6fdb664621805364'),
    (2, '88768434fd076e997e45a2bd1bc77edf63f5ca30f174cc59be78a85a0f5043f0'),
    (2, 'bef8fe19e6dbc4ea590d329594f8b89e0a26fe93ca1fbc8c47b033af4e8f2953'),
    (4, 'c6ce6757c244d656cb2681e0570214c5cd34c727da5d6b9d135b75bb4e626c1c'),
    (5, '3ef995cca26f4ef2cfcc6e65e0aef7dda47075bd8884e22e169cfb181a58fab3'),
    (7, 'ecb97ce51ed9deb2289a76ccc4f5d276dbde624c7bf55c6fb52ed8f5c044f3bd'),
    (6, 'bd0a742cab72488466eaae3da4194b0798cb1c5d565b894436cbc4085b1bbcba'),
]

# Enlarge actual rendered text, including px-based styles, rather than changing
# html font-size while leaving most text unchanged. Measure every carrier before
# applying any scale; temporarily disable only this test stylesheet on updates.
# Layout rules, widths, wrapping and clipping are deliberately left unchanged.
TEXT_SCALE_JS = r"""(() => {
 const start = () => {
  // Static compatibility redirects can intentionally have default-src 'none'.
  // They contain no application text and immediately leave for the real page.
  if (!document.getElementById('root') && document.querySelector('meta[http-equiv="refresh" i]')) return;
  const original = new Map();
  let pending = 0, stopped = false;
  const apply = () => {
   pending = 0;
   if (stopped || !document.body || !document.documentElement.isConnected) return;
   for (const [element, value] of original) {
    if (!element.isConnected) {original.delete(element);continue;}
    if (value.font) element.style.setProperty('font-size',value.font,value.priority);
    else element.style.removeProperty('font-size');
   }
   const rows = [...document.body.querySelectorAll('*')].filter(element => {
    if (!(element instanceof HTMLElement) || element.closest('script,style,noscript,svg,[aria-hidden="true"]')) return false;
    return ['INPUT','TEXTAREA','SELECT'].includes(element.tagName) || [...element.childNodes].some(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
   }).map(element => [element, parseFloat(getComputedStyle(element).fontSize)]).filter(row => Number.isFinite(row[1]) && row[1] > 0);
   for (const [element, size] of rows) {
    if (!original.has(element)) original.set(element,{font:element.style.getPropertyValue('font-size'),priority:element.style.getPropertyPriority('font-size')});
    element.dataset.publicTextScale = '200';
    element.dataset.publicOriginalFont = String(size);
    // Inline important is necessary: product headings legitimately use author
    // !important rules with higher specificity than a test attribute selector.
    element.style.setProperty('font-size',size * 2 + 'px','important');
   }
   document.documentElement.dataset.publicTextScaleReady = '200';
  };
  const schedule = () => { if (!stopped && !pending) pending=requestAnimationFrame(apply); };
  const observer = new MutationObserver(schedule);
  observer.observe(document.body,{childList:true,subtree:true,characterData:true});
  window.addEventListener('pagehide',()=>{stopped=true;observer.disconnect();if(pending)cancelAnimationFrame(pending);},{once:true});
  apply();
 };
 if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();"""

# Compare actual text ranges and adjacent interactive controls in their rendered
# positions. Hidden menus, SVG/decorative content and intentional toast overlays
# are excluded. Diagnostics contain structure and geometry, never private text.
GEOMETRY_JS = r"""() => {
 const rect = box => ({x:box.x,y:box.y,left:box.left,top:box.top,right:box.right,bottom:box.bottom,width:box.width,height:box.height});
 const simple = element => element.tagName.toLowerCase()+(element.id?'#'+element.id:'')+(element.classList.length?'.'+[...element.classList].slice(0,2).join('.'):'');
 const name = element => (element.parentElement?simple(element.parentElement)+'>':'')+simple(element);
 const visible = element => {
  if (element.closest('[hidden],[aria-hidden="true"],script,style,noscript,svg,[data-sonner-toaster]')) return false;
  for(let node=element;node;node=node.parentElement){
   const style=getComputedStyle(node);
   if(style.display==='none'||style.visibility==='hidden'||style.visibility==='collapse'||style.contentVisibility==='hidden'||Number(style.opacity)===0)return false;
   if(node.matches('details:not([open])')){const summary=node.querySelector(':scope > summary');if(!summary||!summary.contains(element))return false;}
  }
  const box=element.getBoundingClientRect();
  return box.width>1 && box.height>1 && box.bottom>0 && box.top<innerHeight;
 };
 const intersect = (a,b,x=true,y=true) => {
  const left=x?Math.max(a.left,b.left):a.left,right=x?Math.min(a.right,b.right):a.right,top=y?Math.max(a.top,b.top):a.top,bottom=y?Math.min(a.bottom,b.bottom):a.bottom;
  return {x:left,y:top,left,right,top,bottom,width:right-left,height:bottom-top};
 };
 const regions=[...document.querySelectorAll('.public-header-main,.sns-editorial-actions,.entry-dock-grid,.entry-real-panel,.sample-scope-bar,.app-topbar-actions,.bottom-nav')].filter(visible);
 const overlaps=[];
 for (const region of regions) {
  const controls=[...region.querySelectorAll('a[href],button,input:not([type="hidden"]),textarea,select')].filter(visible);
  for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
   const a=controls[i],b=controls[j];if(a.contains(b)||b.contains(a))continue;
   const box=intersect(a.getBoundingClientRect(),b.getBoundingClientRect());
   if(box.width>1.5&&box.height>1.5)overlaps.push({region:name(region),a:name(a),b:name(b),dx:box.width,dy:box.height});
  }
 }
 const contentTextClipped=[];
 const paintBox = (box,parent) => {
  let result=rect(box);
  for(let ancestor=parent;ancestor;ancestor=ancestor.parentElement){
   const style=getComputedStyle(ancestor),x=/^(hidden|clip|auto|scroll)$/.test(style.overflowX),y=/^(hidden|clip|auto|scroll)$/.test(style.overflowY);
   if(!x&&!y)continue;
   const bounds=ancestor.getBoundingClientRect();
   const clipped=intersect(result,bounds,x,y);
   // Scrollable regions intentionally clip content until the reader scrolls.
   // Non-scrollable clipping of actual text is a product failure instead.
   if((/^(hidden|clip)$/.test(style.overflowX)&&(result.left<bounds.left-2||result.right>bounds.right+2))||(/^(hidden|clip)$/.test(style.overflowY)&&(result.top<bounds.top-2||result.bottom>bounds.bottom+2)))contentTextClipped.push({element:name(parent),ancestor:name(ancestor),text:result,bounds:rect(bounds)});
   result=clipped;if(result.width<=1||result.height<=1)return null;
  }
  result=intersect(result,{left:0,top:0,right:innerWidth,bottom:innerHeight});
  return result.width>1&&result.height>1?result:null;
 };
 const scope=document.querySelector('dialog[open]')||document.body;
 const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);
 const lines=[],clipped=[];
 while(walker.nextNode()){
  const node=walker.currentNode,parent=node.parentElement;
  if(!node.textContent.trim()||!parent||!visible(parent))continue;
  const range=document.createRange();range.selectNodeContents(node);
  for(const box of range.getClientRects()){
   if(box.width<=1||box.height<=1||box.bottom<=0||box.top>=innerHeight)continue;
   const painted=paintBox(box,parent);if(!painted)continue;
   const owner=parent.closest('a[href],button');
   if(owner&&visible(owner)&&!owner.closest('.sidebar-brand,.app-topbar-brand,.top-avatar,.member-pass,.sns-editorial-footer-brand')){
    const bounds=owner.getBoundingClientRect();
    if(box.left<bounds.left-2||box.right>bounds.right+2||box.top<bounds.top-2||box.bottom>bounds.bottom+2)clipped.push({owner:name(owner),textParent:name(parent),text:rect(box),bounds:rect(bounds)});
   }
   lines.push({node,parent,box:painted});
  }
 }
 const opaqueFixedCover = (front,back,box) => {
  for(let ancestor=front.parent;ancestor;ancestor=ancestor.parentElement){
   const style=getComputedStyle(ancestor);if(!['fixed','sticky'].includes(style.position)||ancestor.contains(back.parent))continue;
   const color=style.backgroundColor,slash=color.match(/\/\s*([.\d]+)(%)?\s*\)$/);
   let alpha=Number.NaN;
   if(color==='transparent')alpha=0;
   else if(slash)alpha=Number(slash[1])/(slash[2]?100:1);
   else if(color.startsWith('rgba(')){const parts=color.slice(5,-1).split(',');if(parts.length===4)alpha=Number(parts[3]);}
   else if(color.startsWith('rgb(')||color.startsWith('color('))alpha=1;
   if(!(alpha>=.999)||Number(style.opacity)<.999)continue;
   const bounds=ancestor.getBoundingClientRect();
   if(box.left<bounds.left||box.right>bounds.right||box.top<bounds.top||box.bottom>bounds.bottom)continue;
   const hit=document.elementFromPoint((box.left+box.right)/2,(box.top+box.bottom)/2);
   if(hit&&ancestor.contains(hit))return true;
  }
  return false;
 };
 const textOverlaps=[];let occludedByOpaqueChrome=0;
 for(let i=0;i<lines.length;i++)for(let j=i+1;j<lines.length;j++){
  const a=lines[i],b=lines[j];
  if(a.parent.contains(b.parent)||b.parent.contains(a.parent))continue;
  const box=intersect(a.box,b.box);
  if(box.width>2&&box.height>2){
   if(opaqueFixedCover(a,b,box)||opaqueFixedCover(b,a,box)){occludedByOpaqueChrome++;continue;}
   textOverlaps.push({a:name(a.parent),b:name(b.parent),dx:box.width,dy:box.height});
  }
 }
 const inputTextClipped=[...document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file])')].filter(visible).map(element=>{const style=getComputedStyle(element),font=parseFloat(style.fontSize),available=element.clientHeight-parseFloat(style.paddingTop)-parseFloat(style.paddingBottom);return {element:name(element),font,available};}).filter(item=>item.available+2<item.font*1.1);
 const heading=document.querySelector('#main h1');
 const h=heading?heading.getBoundingClientRect():null;
 return {overflow:document.documentElement.scrollWidth-innerWidth,bodyOverflow:document.body.scrollWidth-innerWidth,regions:regions.length,controlsOverlapping:overlaps.slice(0,8),controlTextClipped:clipped.slice(0,8),contentTextClipped:contentTextClipped.slice(0,8),inputTextClipped,textOverlapping:textOverlaps.slice(0,8),occludedByOpaqueChrome,heading:h?rect(h):null,visibleTextRanges:lines.length};
}"""
CONTRAST_JS = r"""(element, options = {}) => {
  const parse = value => {
    if (value === 'transparent') return [0, 0, 0, 0];
    const rgb = value.match(/^rgba?\((.*)\)$/);
    if (rgb) {
      const values = rgb[1].replace(/,/g, ' ').replace(/\//g, ' ').trim().split(/\s+/);
      return values.map((v, i) => v.endsWith('%') ? parseFloat(v) * (i < 3 ? 2.55 : .01) : parseFloat(v)).concat([1]).slice(0, 4);
    }
    const srgb = value.match(/^color\(srgb\s+([^)]*)\)$/);
    if (srgb) {
      const values = srgb[1].replace(/\//g, ' ').trim().split(/\s+/).map(Number);
      return [values[0] * 255, values[1] * 255, values[2] * 255, values[3] ?? 1];
    }
    throw Error('Unsupported computed color: ' + value);
  };
  const over = (front, back) => {
    const alpha = front[3] + back[3] * (1 - front[3]);
    return [...front.slice(0, 3).map((v, i) => alpha ? (v * front[3] + back[i] * back[3] * (1 - front[3])) / alpha : 0), alpha];
  };
  const luminance = color => color.slice(0, 3).map(v => {
    const s = v / 255;
    return s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4;
  }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
  const chain = [];
  for (let node = element; node; node = node.parentElement) chain.push(getComputedStyle(node));
  const scheme = getComputedStyle(document.documentElement).colorScheme;
  let background = scheme === 'dark' ? [0, 0, 0, 1] : [255, 255, 255, 1];
  let imageBacked = false;
  for (const style of chain.reverse()) {
    const color = parse(style.backgroundColor);
    if (color[3] >= .999) imageBacked = false;
    background = over(color, background);
    if (style.backgroundImage !== 'none') imageBacked = true;
  }
  const style = getComputedStyle(element, options.pseudo || null);
  const foreground = parse(style.color);
  // Parent opacity also affects the final painted text. Current controls use
  // explicit disabled colors rather than reducing the entire control opacity.
  const opacity = chain.reduce((value, s) => value * Number(s.opacity || 1), 1);
  foreground[3] *= opacity;
  const painted = over(foreground, background);
  const a = luminance(painted), b = luminance(background);
  const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  const size = parseFloat(style.fontSize), weight = parseInt(style.fontWeight, 10) || 400;
  const large = size >= 24 || (size >= 18.666 && weight >= 700);
  const rect = element.getBoundingClientRect();
  return {ratio, required: large ? 3 : 4.5, foreground: style.color, background: background.map(v => Math.round(v * 100) / 100), fontSize: size, fontWeight: weight, imageBacked, visible: rect.width > 0 && rect.height > 0};
}"""


def assert_private_text(page):
    text = page.locator('body').inner_text()
    versions = {text, re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))}
    by_length = {}
    for length, digest in PROTECTED_DIGESTS:
        by_length.setdefault(length, set()).add(digest)
    for value in versions:
        for length, forbidden in by_length.items():
            for index in range(max(0, len(value) - length + 1)):
                digest = hashlib.sha256(value[index:index + length].encode()).hexdigest()
                assert digest not in forbidden, f'Protected personal token detected (digest={digest[:12]}, length={length}); content suppressed'
    assert page.locator('a[href^="mailto:"],a[href^="tel:"]').count() == 0, 'Direct personal contact link exposed'
    assert page.locator('a[href*="/owner/"],a[href$="/owner"]').count() == 0, 'Management navigation exposed to public/member sample'


def assert_geometry(page):
    result = page.evaluate(GEOMETRY_JS)
    assert result['overflow'] <= 2 and result['bodyOverflow'] <= 2, result
    assert not result['controlsOverlapping'], result
    assert not result['controlTextClipped'], result
    assert not result['contentTextClipped'], result
    assert not result['inputTextClipped'], result
    assert not result['textOverlapping'], result
    return result


def contrasts(page, selectors):
    results = []
    for selector in selectors:
        item = page.locator(selector).first
        expect(item).to_be_visible()
        value = item.evaluate(CONTRAST_JS, {})
        assert value['visible'] and not value['imageBacked'] and value['ratio'] >= value['required'], dict(selector=selector, **value)
        results.append(dict(selector=selector, **value))
    return results


def assert_round_profile_icon(page, icon):
    """Profile identity stays distinct from rectangular content and member cards."""
    expect(icon).to_be_visible()
    value = icon.evaluate("""element => {
 const style=getComputedStyle(element),box=element.getBoundingClientRect();
 const radius=value=>value.endsWith('%')?Math.min(box.width,box.height)*parseFloat(value)/100:parseFloat(value);
 return {width:box.width,height:box.height,radii:[style.borderTopLeftRadius,style.borderTopRightRadius,style.borderBottomLeftRadius,style.borderBottomRightRadius].map(radius)};
}""")
    assert abs(value['width'] - value['height']) <= 2, value
    assert all(radius >= min(value['width'], value['height']) / 2 - 1 for radius in value['radii']), value
    image = icon.locator('img')
    if image.count():
        page.wait_for_function('(image)=>image.complete&&image.naturalWidth>0', arg=image.element_handle(), timeout=10000)
    return value


def assert_no_post_comments(page):
    """A read-only notice may mention comments; no member reply controls exist."""
    feed = page.locator('.feed')
    expect(feed.locator('.comments,.comment,.comment-form')).to_have_count(0)
    expect(feed.get_by_role('textbox', name=re.compile('コメント|返信'))).to_have_count(0)
    expect(feed.get_by_role('button', name=re.compile('コメント|返信'))).to_have_count(0)
    expect(feed.locator('article.moment').first.get_by_role('button', name='スキ', exact=True)).to_be_visible()


def wait_ready(page):
    expect(page.locator('#main')).to_be_visible(timeout=20000)
    page.wait_for_function('''() => [...document.images].filter(image => {const r=image.getBoundingClientRect();return r.width>0&&r.height>0&&r.top<innerHeight&&r.bottom>0}).every(image => image.complete&&image.naturalWidth>0)''', timeout=15000)
    assert_private_text(page)


def sample_shell(page, public_path):
    expect(page.locator('.member-experience,.public-work')).to_be_visible()
    bar = page.locator('.sample-scope-bar')
    expect(bar).to_have_count(1)
    expect(page.locator('.app-utility-bar')).to_have_count(1)
    expect(bar).to_contain_text('サンプル')
    expect(bar.get_by_role('link', name='トップへ戻る', exact=True)).to_be_visible()
    assert urlsplit(bar.get_by_role('link', name='トップへ戻る', exact=True).get_attribute('href')).path == public_path
    expect(page.locator('iframe,#view,.review-header,#review-tools,.demo-banner')).to_have_count(0)
    expect(page.get_by_role('button', name=re.compile('確認用管理画面|運営メニューを開閉|確認ツール'))).to_have_count(0)
    expect(bar.get_by_role('button')).to_have_count(0)
    return bar


def scale_evidence(page, selector='#main'):
    page.wait_for_function("""selector => {
 const root=document.querySelector(selector);if(!root)return false;
 const candidates=[root,...root.querySelectorAll('*')].filter(element=>element instanceof HTMLElement&&!element.closest('script,style,noscript,svg,[aria-hidden="true"]')&&element.getBoundingClientRect().width>1&&element.getBoundingClientRect().height>1&&element.getBoundingClientRect().bottom>0&&element.getBoundingClientRect().top<innerHeight&&(['INPUT','TEXTAREA','SELECT'].includes(element.tagName)||[...element.childNodes].some(node=>node.nodeType===Node.TEXT_NODE&&node.textContent.trim())));
 return candidates.length>0&&candidates.every(element=>Number(element.dataset.publicOriginalFont)>0&&Math.abs(parseFloat(getComputedStyle(element).fontSize)-Number(element.dataset.publicOriginalFont)*2)<0.5);
}""", arg=selector, timeout=10000)
    return page.evaluate("""selector => {
 const root=document.querySelector(selector),rows=[root,...root.querySelectorAll('[data-public-text-scale]')].filter(element=>element instanceof HTMLElement&&Number(element.dataset.publicOriginalFont)>0&&element.getBoundingClientRect().width>1&&element.getBoundingClientRect().height>1&&element.getBoundingClientRect().bottom>0&&element.getBoundingClientRect().top<innerHeight).map(element=>({original:Number(element.dataset.publicOriginalFont),rendered:parseFloat(getComputedStyle(element).fontSize)}));
 const factors=rows.map(row=>row.rendered/row.original);
 return {carriers:rows.length,original:rows[0].original,rendered:rows[0].rendered,factor:factors[0],minFactor:Math.min(...factors),maxFactor:Math.max(...factors)};
}""", selector)


def main():
    # Keeping the recorder importable lets its failure paths run without a
    # browser; the actual browser verification still requires Playwright.
    global expect
    from playwright.sync_api import expect, sync_playwright

    target = sys.argv[1] if len(sys.argv) > 1 else 'release/app'
    live = target.startswith('https://')
    out = pathlib.Path('verification')
    server = None
    recorder = EvidenceRecorder(out)
    print('evidence-storage-start', json.dumps(evidence_storage(out)), flush=True)
    checks, network = recorder.checks, []
    if live:
        base = target.rstrip('/') + '/'
    else:
        root = pathlib.Path(target).resolve()
        assert (root / 'index.html').is_file() and (root / 'review/member/index.html').is_file()

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def translate_path(self, path):
                local = unquote(urlsplit(path).path).removeprefix('/muumei-public/')
                candidate = (root / local).resolve()
                return str(candidate if candidate.is_relative_to(root) and candidate.exists() else root / '404.html')

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/muumei-public/'
    public_path = urlsplit(base).path
    sample_base = base + 'review/member/'
    sample_home_path = public_path + 'review/member/demo/home/'
    origin = (urlsplit(base).scheme, urlsplit(base).netloc)

    def record(name, ok, **details):
        recorder.record(name, ok, **details)
        print(name, 'PASS' if ok else 'FAIL', details, flush=True)

    try:
        with sync_playwright() as playwright:
            engines = [item.strip() for item in os.environ.get('MUUMEI_BROWSER_ENGINES', 'chromium,firefox,webkit').split(',') if item.strip()]
            assert engines and set(engines) <= {'chromium', 'firefox', 'webkit'}
            for engine in engines:
                browser = getattr(playwright, engine).launch()
                settings = [(width, scheme, False) for width in WIDTHS for scheme in SCHEMES]
                settings += [(390, scheme, True) for scheme in SCHEMES]
                for width, scheme, enlarged in settings:
                    context = browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=scheme, reduced_motion='reduce', service_workers='block')
                    context.add_init_script("window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();event.stopImmediatePropagation();},true);")
                    context.add_init_script("window.__muumeiNotificationPermissionRequests=0;if('Notification' in window)Notification.requestPermission=()=>{window.__muumeiNotificationPermissionRequests++;return Promise.resolve('denied')};")
                    if enlarged:
                        context.add_init_script(TEXT_SCALE_JS)
                    phase = {'value': 'public'}
                    requests, errors = [], []

                    def observe(request):
                        address = urlsplit(request.url)
                        if address.scheme not in ['http', 'https']:
                            return
                        row = dict(engine=engine, width=width, scheme=scheme, text_scale=200 if enlarged else 100,
                                   scope=phase['value'], method=request.method, path=address.path,
                                   external=(address.scheme, address.netloc) != origin,
                                   backend=(address.hostname or '').endswith('.supabase.co'))
                        requests.append(row)
                        network.append(row)

                    def protect(route):
                        address = urlsplit(route.request.url)
                        if route.request.method not in ['GET', 'HEAD'] or (address.hostname or '').endswith('.supabase.co') or (address.scheme in ['http', 'https'] and (address.scheme, address.netloc) != origin):
                            route.abort()
                        else:
                            route.continue_()

                    context.on('request', observe)
                    context.route('**/*', protect)
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    tag = f'{engine}:{width}:{scheme}'+(':text-200' if enlarged else '')

                    def run_case(label, callback):
                        errors.clear()
                        try:
                            details = callback() or {}
                            assert not errors, errors
                        except EvidenceError:
                            raise
                        except Exception as error:
                            record(tag + ':' + label, False, error=str(error), traceback=traceback.format_exc(limit=5))
                            try:
                                assert_private_text(page)
                                page.screenshot(path=str(out / f'public-experience-{engine}-{width}-{scheme}-{enlarged}-{label}-failure.png'), full_page=True)
                            except OSError as persistence_error:
                                recorder.fail('failure-screenshot', persistence_error, case=tag + ':' + label)
                            except Exception:
                                pass
                        else:
                            record(tag + ':' + label, True, **details)

                    def visit(route, *, sample=False):
                        phase['value'] = 'sample' if sample else 'public'
                        response = page.goto(base + route, wait_until='domcontentloaded')
                        assert response and response.status == 200, f'HTTP {response.status if response else None}'
                        wait_ready(page)
                        if enlarged:
                            scale_evidence(page)
                        return response

                    def reload_page():
                        page.reload(wait_until='domcontentloaded')
                        wait_ready(page)
                        if enlarged:
                            scale_evidence(page)

                    def screenshot(label):
                        if engine == 'chromium' and width in [344, 390]:
                            assert_private_text(page)
                            try:
                                page.screenshot(path=str(out / (f'public-experience-{width}-{scheme}-'+('200-' if enlarged else '')+label+'.png')), full_page=True)
                            except OSError as persistence_error:
                                recorder.fail('screenshot', persistence_error, case=tag + ':' + label)

                    def public_top():
                        visit('')
                        expect(page.locator('[data-surface="public-information"]')).to_be_visible()
                        expect(page.locator('.sns-editorial-hero')).to_be_visible()
                        expect(page.locator('#sns-title')).to_contain_text('会った人と、')
                        expect(page.locator('#sns-title')).to_contain_text('ふだんの話を。')
                        hero_scene = page.locator('.sns-editorial-hero-scene')
                        expect(hero_scene).to_have_attribute('aria-hidden', 'true')
                        hero_images = hero_scene.locator('img')
                        expect(hero_images).to_have_count(2)
                        for image in hero_images.all():
                            page.wait_for_function('(image)=>image.complete&&image.naturalWidth>0', arg=image.element_handle(), timeout=10000)
                            expect(image).to_have_attribute('alt', '')
                        assert len(set(hero_images.evaluate_all('(items)=>items.map(item=>item.getAttribute("src"))'))) == 2
                        hero_layout = page.locator('.sns-editorial-hero').evaluate("""hero => {
 const box=element=>{const r=element.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom}};
 const intersection=(a,b)=>({width:Math.min(a.right,b.right)-Math.max(a.left,b.left),height:Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)});
 const photos=[...hero.querySelectorAll('.sns-editorial-hero-scene img')].map(box);
 const copy=[hero.querySelector('h1'),hero.querySelector('.sns-editorial-lead')].map(box);
 const caption=box(hero.querySelector('.sns-hero-scene-caption'));
 return {copy_photo_overlap:copy.flatMap(text=>photos.map(photo=>intersection(text,photo))).filter(r=>r.width>2&&r.height>2),caption_photo_overlap:photos.map(photo=>intersection(caption,photo)).filter(r=>r.width>2&&r.height>2)};
}""")
                        assert not hero_layout['copy_photo_overlap'] and not hero_layout['caption_photo_overlap'], hero_layout
                        expect(page.locator('.sample-scope-bar,.demo-banner,.review-header,.member-experience')).to_have_count(0)
                        expect(page.get_by_role('button', name=re.compile('確認用管理画面|運営メニューを開閉|確認ツール'))).to_have_count(0)
                        cards = page.locator('#entrances .entry-dock-grid > a.entry-dock-app')
                        expect(cards).to_have_count(3)
                        expected_paths = [public_path + 'entry/' + key + '/' for key in ['private', 'connection', 'work']]
                        assert cards.evaluate_all('(items)=>items.map(item=>new URL(item.href).pathname)') == expected_paths
                        boxes = cards.evaluate_all('(items)=>items.map(item=>{const r=item.getBoundingClientRect();return {top:r.top,left:r.left,right:r.right,bottom:r.bottom}})')
                        assert max(item['top'] for item in boxes) - min(item['top'] for item in boxes) <= 2, boxes
                        assert all(boxes[index]['right'] <= boxes[index+1]['left'] for index in [0, 1]), boxes
                        expect(page.locator('#main > #entrances:last-child')).to_be_visible()
                        sample = page.locator('#entrances .sample-entry-panel')
                        expect(page.locator('.sample-entry-panel')).to_have_count(1)
                        assert sample.evaluate('(element)=>element.getBoundingClientRect().top') >= cards.evaluate_all('(items)=>Math.max(...items.map(item=>item.getBoundingClientRect().bottom))')
                        assert urlsplit(sample.locator('a').get_attribute('href')).path == public_path + 'review/'
                        value = assert_geometry(page)
                        heading_metrics = page.locator('#sns-title').evaluate('(element)=>({height:element.getBoundingClientRect().height,line:parseFloat(getComputedStyle(element).lineHeight)})')
                        if not enlarged:
                            assert heading_metrics['height'] <= heading_metrics['line'] * 2 + 3, heading_metrics
                        page.locator('#entrances').scroll_into_view_if_needed()
                        dock_layout = assert_geometry(page)
                        sample.scroll_into_view_if_needed()
                        sample_layout = assert_geometry(page)
                        result = contrasts(page, ['#sns-title', '.sns-editorial-lead', '.sns-editorial-primary', '.entry-dock-app > strong', '.sample-entry-panel p'])
                        screenshot('top')
                        return dict(layout=value, dock_layout=dock_layout, small_sample_layout=sample_layout, heading_metrics=heading_metrics, hero_photos=2, hero_layout=hero_layout, contrast=result, ordinary_surface=True, three_horizontal_entrances=True,
                                    text_scale=scale_evidence(page) if enlarged else 100)

                    run_case('public-top-no-sample-runtime-or-owner', public_top)

                    def public_features():
                        visit('')
                        images = page.locator('.sns-editorial-feature .sns-moment-photo img')
                        expect(images).to_have_count(3)
                        for image in images.all():
                            image.scroll_into_view_if_needed()
                            page.wait_for_function('(image)=>image.complete&&image.naturalWidth>0', arg=image.element_handle(), timeout=10000)
                        sources = images.evaluate_all('(items)=>items.map(item=>item.getAttribute("src"))')
                        assert len(set(sources)) == 3
                        features = [
                            ('好きなものを、ひとつ。', '投稿へのコメント機能はありません。'),
                            ('次の楽しみも、ここで。', '仕事・お手伝いは、別の窓口から確認できます。'),
                            ('連絡は、運営者へ。', 'メンバー同士の個別DMはありません。'),
                        ]
                        layouts, feature_contrast = [], []
                        for index, (title, boundary_text) in enumerate(features):
                            opener = page.locator('.sns-editorial-feature .sns-moment-photo').nth(index)
                            previous = page.locator('body').evaluate('(element)=>element.style.overflow')
                            opener.click()
                            dialog = page.locator('dialog.sns-feature-dialog[open]')
                            expect(page.get_by_role('dialog', name=title, exact=True)).to_be_visible()
                            expect(dialog.locator('.sns-feature-detail img')).to_have_attribute('src', sources[index])
                            expect(dialog.get_by_role('heading', level=2)).to_have_text(title)
                            summary = dialog.locator('#sns-feature-summary')
                            assert 20 <= len(summary.inner_text()) <= 160, 'Feature needs a short, concrete explanation'
                            expect(dialog.locator('.sns-feature-steps > li')).to_have_count(3)
                            expect(dialog.locator('.sns-feature-boundary')).to_have_text(boundary_text)
                            expect(dialog.locator('form,input,textarea,.sample-scope-bar,.review-header,.member-experience')).to_have_count(0)
                            assert len(dialog.inner_text()) <= 500, 'Public explanation expanded into a sample experience'
                            if enlarged:
                                scale_evidence(page, '.sns-feature-dialog')
                            for section in [dialog.locator('h2'), summary, dialog.locator('.sns-feature-steps > li').last, dialog.locator('.sns-feature-boundary')]:
                                section.scroll_into_view_if_needed()
                                layouts.append(assert_geometry(page))
                            feature_contrast += contrasts(page, ['.sns-feature-dialog h2', '#sns-feature-summary', '.sns-feature-boundary'])
                            if index == 0:
                                dialog.get_by_role('button', name='次の機能', exact=True).click()
                                expect(page.get_by_role('dialog', name=features[1][0], exact=True)).to_be_visible()
                                expect(dialog.locator('.sns-feature-detail img')).to_have_attribute('src', sources[1])
                                dialog.get_by_role('button', name='前の機能', exact=True).click()
                                expect(page.get_by_role('dialog', name=title, exact=True)).to_be_visible()
                                if width == 390 and not enlarged:
                                    screenshot('feature-dialog')
                            page.keyboard.press('Escape')
                            expect(page.locator('dialog.sns-feature-dialog')).to_have_count(0)
                            expect(opener).to_be_focused()
                            page.wait_for_function('(value)=>document.body.style.overflow===value', arg=previous)
                        return dict(illustrative_photos_loaded=3, concrete_feature_explanations=3, layouts=layouts,
                                    contrast=feature_contrast, comment_boundary_explicit=True, public_sample_controls=0,
                                    focus_restored=True, scroll_state_restored=True)
                    run_case('public-feature-explanations-and-dialog', public_features)

                    for key in ['private', 'connection', 'work']:
                        def entry(key=key):
                            visit('entry/' + key + '/')
                            expect(page.locator('[data-surface="public-information"]')).to_be_visible()
                            expect(page.locator('.sample-scope-bar,.demo-banner,.review-header')).to_have_count(0)
                            expect(page.locator('.entry-mode-label')).to_have_text('実際に利用する')
                            target_path = public_path + ('jobs/' if key == 'work' else 'app/home/')
                            action = page.locator('.entry-real-action')
                            assert urlsplit(action.get_attribute('href')).path == target_path
                            sample = page.locator('.entry-choice > .sample-entry-panel a')
                            expected_sample = public_path + ('review/member/demo/work-public/' if key == 'work' else 'review/')
                            assert urlsplit(sample.get_attribute('href')).path == expected_sample
                            value = assert_geometry(page)
                            action.scroll_into_view_if_needed()
                            action_layout = assert_geometry(page)
                            sample.scroll_into_view_if_needed()
                            sample_layout = assert_geometry(page)
                            contrast = contrasts(page, ['.entry-choice-heading h1', '.entry-real-panel h2', '.entry-real-panel p', '.entry-real-action', '.sample-entry-panel p'])
                            if not enlarged:
                                phase['value'] = 'sample'
                                sample.click()
                                wait_ready(page)
                                sample_shell(page, public_path)
                                actual = urlsplit(page.url).path
                                assert actual == (expected_sample if key == 'work' else sample_home_path), dict(expected=expected_sample, actual=actual)
                                if key == 'work':
                                    expect(page.locator('.public-work-form')).to_be_visible()
                                else:
                                    expect(page.locator('.home-feature-copy')).to_be_visible()
                                page.locator('.sample-scope-bar').get_by_role('link', name='トップへ戻る', exact=True).click()
                                wait_ready(page)
                                expect(page.locator('[data-surface="public-information"]')).to_be_visible()
                                assert urlsplit(page.url).path == public_path
                            return dict(layout=value, action_layout=action_layout, small_sample_layout=sample_layout, contrast=contrast, real_destination=target_path, sample_destination=expected_sample, sample_click_verified=not enlarged)
                        run_case('separate-entry-' + key, entry)

                    def sample_home():
                        visit('review/', sample=True)
                        assert urlsplit(page.url).path == sample_home_path
                        sample_shell(page, public_path)
                        expect(page.locator('.home-feature-copy')).to_be_visible()
                        value = assert_geometry(page)
                        result = contrasts(page, ['.sample-scope-brand', '.sample-scope-bar > a', '#main h1'])
                        screenshot('member-home')
                        return dict(layout=value, contrast=result, standalone_member_sample=True, iframe_count=0,
                                    text_scale=scale_evidence(page) if enlarged else 100)
                    run_case('standalone-member-sample-one-label-bar', sample_home)

                    def feed():
                        visit('review/member/demo/moments/', sample=True)
                        sample_shell(page, public_path)
                        expect(page.get_by_role('textbox', name='今日のひとこと')).to_be_visible()
                        expect(page.locator('[data-page="moments"]')).to_have_attribute('data-comments', 'disabled')
                        images = page.locator('.moment-photo img')
                        expect(images).to_have_count(3)
                        for image in images.all():
                            image.scroll_into_view_if_needed()
                            page.wait_for_function('(image)=>image.complete&&image.naturalWidth>0', arg=image.element_handle(), timeout=10000)
                        assert len(set(images.evaluate_all('(items)=>items.map(item=>item.getAttribute("src"))'))) == 3
                        page.get_by_role('heading', level=1).scroll_into_view_if_needed()
                        assert_no_post_comments(page)
                        value = assert_geometry(page)
                        if not enlarged:
                            first_post = page.locator('article.moment').first
                            like = first_post.get_by_role('button', name='スキ', exact=True)
                            previous_like = like.get_attribute('aria-pressed')
                            expected_like = 'false' if previous_like == 'true' else 'true'
                            like.click()
                            expect(like).to_have_attribute('aria-pressed', expected_like)
                            reload_page()
                            assert_no_post_comments(page)
                            restored_like = page.locator('article.moment').first.get_by_role('button', name='スキ', exact=True)
                            expect(restored_like).to_have_attribute('aria-pressed', expected_like)
                            restored_like.click()
                            expect(restored_like).to_have_attribute('aria-pressed', previous_like)
                            body = 'この画面だけに保存する、表示確認のひとこと。'
                            page.get_by_role('textbox', name='今日のひとこと').fill(body)
                            page.get_by_role('button', name='投稿する', exact=True).click()
                            expect(page.get_by_text(body, exact=True)).to_be_visible()
                            reload_page()
                            post = page.locator('article.moment').filter(has=page.get_by_text(body, exact=True))
                            expect(post).to_be_visible()
                            post.get_by_role('button', name='自分の投稿を削除', exact=True).click()
                            page.get_by_role('button', name='削除する', exact=True).click()
                            expect(page.get_by_text(body, exact=True)).to_have_count(0)
                        screenshot('member-feed')
                        return dict(layout=value, photographs_loaded=3, comment_controls=0, likes_remain_available=True,
                                    local_like_persisted_and_restored=not enlarged, local_post_persisted_and_removed=not enlarged)
                    run_case('sample-feed-photos-and-local-post', feed)

                    def profile():
                        visit('review/member/demo/my/', sample=True)
                        sample_shell(page, public_path)
                        expect(page.locator('.profile-about')).to_be_visible()
                        expect(page.locator('.profile-interests[aria-label="好きなこと"]')).to_be_visible()
                        expect(page.locator('.profile-cover')).to_have_count(0)
                        expect(page.locator('.profile-identity')).to_contain_text('プロフィールアイコン')
                        icon = page.locator('.profile-icon-preview > .avatar[data-image-role="profile-icon"]')
                        icon_metrics = assert_round_profile_icon(page, icon)
                        card = page.locator('.profile-pass-panel article.member-pass.pass-compact')
                        expect(card).to_be_visible()
                        expect(card.locator('.pass-card-label')).to_contain_text('MEMBER CARD')
                        expect(card.locator('.pass-card-label')).to_contain_text('メンバーカード')
                        assert card.get_attribute('aria-label'), 'Member card has no accessible identity label'
                        value = assert_geometry(page)
                        result = contrasts(page, ['.profile-identity-copy h1', '.profile-icon-preview > small', '.pass-card-label', '.profile-about h2', '.profile-interests[aria-label="好きなこと"] span'])
                        if not enlarged:
                            page.get_by_role('button', name='編集する', exact=True).click()
                            expect(page.locator('.profile-pass-panel')).to_have_count(0)
                            intro = 'このサンプル画面だけで自己紹介を確認しています。'
                            page.get_by_role('textbox', name='ひとこと自己紹介', exact=False).fill(intro)
                            page.get_by_role('button', name='プロフィールを保存する', exact=True).click()
                            expect(page.locator('.profile-about')).to_contain_text(intro)
                            reload_page()
                            expect(page.locator('.profile-about')).to_contain_text(intro)
                            expect(page.locator('.profile-pass-panel article.member-pass.pass-compact')).to_be_visible()
                        screenshot('member-profile')
                        visit('review/member/demo/pass/', sample=True)
                        sample_shell(page, public_path)
                        pass_card = page.locator('article.member-pass')
                        expect(pass_card).to_be_visible()
                        expect(pass_card.locator('.pass-card-label')).to_contain_text('メンバーカード')
                        pass_card.scroll_into_view_if_needed()
                        pass_layout = assert_geometry(page)
                        pass_contrast = contrasts(page, ['.pass-card-label', '.pass-note'])
                        screenshot('member-pass')
                        return dict(layout=value, contrast=result, profile_icon=icon_metrics, visible_labeled_member_card=True,
                                    decorative_profile_cover=False, profile_edit_is_local=not enlarged, pass_layout=pass_layout,
                                    pass_contrast=pass_contrast)
                    run_case('sample-profile-no-management-controls', profile)

                    def chat():
                        visit('review/member/demo/messages/', sample=True)
                        sample_shell(page, public_path)
                        thread_contrast = contrasts(page, ['.thread-list a.person-row strong', '.thread-list a.person-row p'])
                        page.locator('.thread-list a.person-row').first.click()
                        composer = page.get_by_role('textbox', name='メッセージ', exact=True)
                        expect(composer).to_be_visible()
                        if enlarged:
                            scale_evidence(page)
                        value = assert_geometry(page)
                        composer.scroll_into_view_if_needed()
                        if enlarged:
                            scale_evidence(page, '.composer textarea')
                        composer_layout = assert_geometry(page)
                        if not enlarged:
                            body = 'このサンプルだけで確認する送信取消。'
                            composer.fill(body)
                            page.get_by_role('button', name='送信', exact=True).click()
                            bubble = page.locator('.bubble.mine').filter(has=page.get_by_text(body, exact=True))
                            expect(bubble).to_be_visible()
                            peer = page.locator('.bubble:not(.mine):not(.deleted)')
                            assert peer.count() > 0
                            expect(peer.get_by_role('button', name='送信を取り消す', exact=True)).to_have_count(0)
                            bubble.get_by_role('button', name='送信を取り消す', exact=True).click()
                            page.get_by_role('dialog').get_by_role('button', name='やめる', exact=True).click()
                            expect(bubble).to_be_visible()
                            bubble.get_by_role('button', name='送信を取り消す', exact=True).click()
                            page.get_by_role('dialog').get_by_role('button', name='取り消す', exact=True).click()
                            expect(page.get_by_text(body, exact=True)).to_have_count(0)
                            reload_page()
                            expect(page.get_by_text(body, exact=True)).to_have_count(0)
                            expect(page.locator('.bubble.deleted').last).to_contain_text('メッセージの送信が取り消されました')
                        return dict(layout=value, composer_layout=composer_layout, contrast=thread_contrast, sender_only_withdrawal_persisted=not enlarged)
                    run_case('sample-chat-local-sender-only-withdrawal', chat)

                    def install_notifications():
                        visit('review/member/demo/install/', sample=True)
                        sample_shell(page, public_path)
                        section = page.get_by_role('region', name='この端末の通知設定', exact=True)
                        expect(section).to_be_visible()
                        expect(section.get_by_role('heading', name='通知を受け取る', exact=True)).to_be_visible()
                        expect(section.locator('[data-push-state]')).to_contain_text('サンプルでは、端末の通知登録や許可の要求は行いません。')
                        expect(section.get_by_role('button', name='この端末で通知を受け取る', exact=True)).to_have_count(0)
                        expect(section.get_by_text('掲示板の返信', exact=True)).to_have_count(0)
                        link = section.get_by_role('link', name='アプリ内のお知らせを見る', exact=False)
                        assert urlsplit(link.get_attribute('href')).path == public_path + 'review/member/demo/notifications'
                        section.scroll_into_view_if_needed()
                        value = assert_geometry(page)
                        attempted = page.evaluate('window.__muumeiNotificationPermissionRequests')
                        assert attempted == 0
                        return dict(layout=value, sample_push_registration=False, notification_permission_attempts=attempted)
                    run_case('sample-install-notifications-stay-local', install_notifications)

                    def work():
                        visit('review/member/demo/work-public/', sample=True)
                        sample_shell(page, public_path)
                        form = page.locator('.public-work-form')
                        expect(form).to_be_visible()
                        images = page.locator('.public-work-job-image > img')
                        for image in images.all():
                            image.scroll_into_view_if_needed()
                            page.wait_for_function('(image)=>image.complete&&image.naturalWidth>0', arg=image.element_handle(), timeout=10000)
                        assert len(set(images.evaluate_all('(items)=>items.map(item=>item.getAttribute("src"))'))) >= 3
                        page.get_by_role('heading', level=1).scroll_into_view_if_needed()
                        value = assert_geometry(page)
                        form.locator('[name="name"]').scroll_into_view_if_needed()
                        form_layout = assert_geometry(page)
                        form.get_by_role('button', name='サンプルで送信を試す', exact=True).scroll_into_view_if_needed()
                        submit_layout = assert_geometry(page)
                        if not enlarged:
                            page.locator('.public-work-job').first.get_by_role('button', name='詳細・応募', exact=False).click()
                            dialog = page.get_by_role('dialog')
                            dialog.get_by_role('button', name='この募集に応募・相談する', exact=False).click()
                            expect(dialog).to_be_hidden()
                            expect(form.locator('[name="job_id"]')).not_to_have_value('')
                            form.locator('[name="name"]').fill('架空の利用者')
                            form.locator('[name="contact_value"]').fill('sample@example.invalid')
                            form.locator('[name="message"]').fill('実際には送信しない、サンプルでの相談内容です。')
                            form.get_by_role('button', name='サンプルで送信を試す', exact=True).click()
                            expect(form.get_by_role('heading', name='サンプルの送信が完了しました。', exact=True)).to_be_visible()
                            expect(form).to_contain_text('SAMPLE-2026')
                            expect(form).to_contain_text('通知やメール送信は行っていません')
                        screenshot('work-sample')
                        return dict(layout=value, form_layout=form_layout, submit_layout=submit_layout, real_submission=False, local_receipt=not enlarged)
                    run_case('work-sample-local-only-form', work)

                    if width == 390 and scheme == 'dark' and not enlarged:
                        def retired_owner():
                            phase['value'] = 'public'
                            page.goto(base + 'review/owner/demo/dashboard/', wait_until='domcontentloaded')
                            expect(page.locator('[data-surface="public-information"]')).to_be_visible(timeout=20000)
                            wait_ready(page)
                            assert urlsplit(page.url).path == public_path
                            expect(page.locator('iframe,.owner-shell,[data-sidebar="sidebar"]')).to_have_count(0)
                            return dict(retired_owner_route_returns_to_public=True)
                        run_case('retired-owner-route-cannot-open-management', retired_owner)

                    def boundary():
                        invalid = [row for row in requests if row['backend'] or row['external'] or row['method'] not in ['GET', 'HEAD']]
                        assert not invalid, invalid
                        response = context.request.get(sample_base + 'muumei-config.json')
                        assert response.status == 200
                        config = response.json()
                        assert not config.get('url') and not config.get('key') and not config.get('ready')
                        return dict(backend_attempts=0, external_http_attempts=0, non_get_requests=0, empty_sample_backend_config=True)
                    run_case('public-and-sample-no-backend-or-real-write', boundary)
                    context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        print('evidence-storage-final', json.dumps(evidence_storage(out)), flush=True)
        recorder.finalize(dict(live=live, target='public-introduction-and-member-sample', production_data_mutated=False,
                               real_registration_tested=False, real_work_acceptance_tested=False, native_install_attempted=False,
                               widths=WIDTHS, color_schemes=SCHEMES, text_scale_200_width=390,
                               total=len(checks), failures=sum(not row['ok'] for row in checks), checks=checks,
                               sample_backend_attempts=sum(row['backend'] and row['scope'] == 'sample' for row in network),
                               sample_non_get_requests=sum(row['method'] not in ['GET', 'HEAD'] and row['scope'] == 'sample' for row in network),
                               network=network))
    assert checks and all(row['ok'] for row in checks), f'{sum(not row["ok"] for row in checks)} public-experience checks failed'


if __name__ == '__main__':
    main()
