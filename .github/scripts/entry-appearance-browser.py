"""Entry separation and light/dark appearance checks; all accounts/data are synthetic.

Run against release/app or the published MUUMEI URL. Production Supabase traffic,
service workers and native install prompts are blocked in every test context.
"""
import http.server
import json
import os
import pathlib
import sys
import threading
from urllib.parse import unquote, urlsplit

from playwright.sync_api import expect, sync_playwright


# Text contrast is computed from the element's real foreground and the alpha-
# composited ancestor surfaces. Decorative/image-backed text is not auto-rated.
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


def contrast(locator, *, pseudo=None):
    expect(locator).to_be_visible()
    result = locator.evaluate(CONTRAST_JS, {'pseudo': pseudo})
    assert result['visible'], result
    assert not result['imageBacked'], 'Choose an opaque text/control surface: ' + str(result)
    assert result['ratio'] >= result['required'], result
    return result


def contrast_pairs(page, selectors):
    results = []
    for selector in selectors:
        locator = page.locator(selector).first
        result = contrast(locator)
        results.append(dict(selector=selector, **result))
    return results


def document_box(locator):
    return locator.evaluate('(e) => { const r=e.getBoundingClientRect(); return {top:r.top+scrollY,bottom:r.bottom+scrollY,width:r.width,height:r.height,fontSize:parseFloat(getComputedStyle(e).fontSize)}; }')


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else 'release/app'
    out = pathlib.Path('verification')
    out.mkdir(exist_ok=True)
    checks, server = [], None
    live = target.startswith('https://')
    if live:
        base = target.rstrip('/') + '/'
    else:
        root = pathlib.Path(target).resolve()
        assert (root / 'index.html').is_file(), 'Missing static release index'

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def translate_path(self, path):
                local = unquote(urlsplit(path).path).removeprefix('/muumei-public/')
                resolved = root / local
                if not resolved.resolve().is_relative_to(root):
                    return str(root / '404.html')
                return str(resolved if resolved.exists() else root / '404.html')

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/muumei-public/'

    def record(name, ok, **details):
        checks.append(dict(name=name, ok=bool(ok), **details))
        (out / 'entry-appearance-browser.json').write_text(json.dumps(dict(
            live=live, production_data_mutated=False, native_install_attempted=False,
            color_schemes=['light', 'dark'], total=len(checks),
            failures=sum(not item['ok'] for item in checks), checks=checks,
        ), ensure_ascii=False, indent=2))
        print(name, 'PASS' if ok else 'FAIL', details, flush=True)

    def assert_page(page):
        expect(page.locator('#main')).to_be_visible(timeout=20000)
        layout = page.evaluate('''() => ({
          overflow: document.documentElement.scrollWidth-innerWidth,
          broken: [...document.images].filter(i => i.getBoundingClientRect().top < innerHeight && i.getBoundingClientRect().bottom > 0 && (!i.complete || !i.naturalWidth)).map(i => i.getAttribute('src')),
          scheme: getComputedStyle(document.documentElement).colorScheme
        })''')
        assert layout['overflow'] <= 2, layout
        assert not layout['broken'], layout
        return layout

    try:
        with sync_playwright() as playwright:
            engines = [value.strip() for value in os.environ.get('MUUMEI_BROWSER_ENGINES', 'chromium,firefox,webkit').split(',') if value.strip()]
            assert engines and set(engines) <= {'chromium', 'firefox', 'webkit'}
            for engine in engines:
                browser = getattr(playwright, engine).launch()
                for scheme in ['light', 'dark']:
                    context = browser.new_context(viewport={'width': 390, 'height': 844}, color_scheme=scheme, reduced_motion='reduce', service_workers='block')
                    context.route('https://*.supabase.co/**', lambda route: route.abort())
                    # Exercise the public fallback guide without invoking an OS
                    # install dialog, even if a browser offers an install event.
                    context.add_init_script("window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();event.stopImmediatePropagation();},true);")
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))

                    def run_case(label, callback):
                        name = f'{engine}:{scheme}:{label}'
                        errors.clear()
                        try:
                            details = callback() or {}
                            assert not errors, errors
                            record(name, True, **details)
                        except Exception as error:
                            record(name, False, error=str(error))
                            page.screenshot(path=str(out / f'entry-{engine}-{scheme}-{label}-failure.png'), full_page=True)

                    def visit(route):
                        response = page.goto(base + route, wait_until='networkidle')
                        assert response and response.status == 200, f'HTTP {response.status if response else None}'
                        layout = assert_page(page)
                        assert layout['scheme'] == scheme, layout
                        return layout

                    def top():
                        visit('')
                        expect(page.locator('.sns-hero-label')).to_have_text('招待制プライベートSNS')
                        expect(page.get_by_role('link', name='あなたの入口を選ぶ', exact=True)).to_be_visible()
                        cards = page.locator('.sns-entry-card')
                        expect(cards).to_have_count(3)
                        assert {urlsplit(href).path for href in cards.evaluate_all('(els)=>els.map(e=>e.getAttribute("href"))')} == {urlsplit(base).path + 'entry/' + key + '/' for key in ['qr', 'invite', 'member']}
                        assert not any(word in page.locator('.private-hero').inner_text() for word in ['タイミー', '仕事募集', '求人'])
                        install = page.get_by_role('button', name='ホーム画面に追加', exact=True)
                        expect(install).to_be_enabled()
                        assert document_box(install)['top'] < 350, 'Install action is not near the top'
                        sample = page.locator('.public-footer > .sample-entry-panel:last-child')
                        expect(sample).to_be_visible()
                        assert document_box(sample)['top'] > document_box(page.locator('.sns-entry-grid'))['bottom']
                        result = contrast_pairs(page, ['.public-login', '.top-install-copy strong', '.top-install-copy p', '.top-install-panel > button', '.hero-cta', '.sns-section-heading h2', '.sns-entry-card strong', '.sns-entry-copy > span', '.sample-entry-panel strong', '.sample-entry-panel p', '.sample-entry-panel > a'])
                        page.screenshot(path=str(out / f'entry-{engine}-{scheme}-top-390.png'), full_page=True)
                        install.click()
                        expect(page.locator('.top-install-instructions')).to_be_visible()
                        expect(install).to_have_attribute('aria-expanded', 'true')
                        expect(page.locator('.top-install-instructions')).to_contain_text('ブラウザ')
                        result += contrast_pairs(page, ['.top-install-instructions h2', '.top-install-instructions li', '.top-install-instructions p'])
                        return {'contrast': result}

                    run_case('top-install-and-three-entrances', top)

                    for entry, destination in [('qr', '/receive'), ('invite', '/invite'), ('member', '/app/home')]:
                        def choice(entry=entry, destination=destination):
                            visit('entry/' + entry + '/')
                            real, sample = page.locator('.entry-real-panel'), page.locator('.entry-choice > .sample-entry-panel')
                            expect(real).to_be_visible()
                            expect(sample).to_be_visible()
                            action = real.locator('.entry-real-action')
                            assert action.get_attribute('href').rstrip('/').endswith(destination)
                            assert document_box(sample)['top'] >= document_box(real)['bottom'] + 20
                            assert document_box(sample.locator('a'))['fontSize'] < document_box(action)['fontSize']
                            if entry != 'member':
                                expect(real.locator('.entry-reception-status')).to_contain_text('登録受付はまだ開始していません')
                                contrast(real.locator('.entry-reception-status'))
                            expect(sample).to_contain_text('架空データ')
                            assert urlsplit(sample.locator('a').get_attribute('href')).path == urlsplit(base).path + 'review/'
                            return {'contrast': contrast_pairs(page, ['.entry-choice-heading h1', '.entry-choice-heading > p:last-child', '.entry-real-panel h2', '.entry-real-panel p', '.entry-real-action', '.entry-real-panel > small', '.sample-entry-panel p', '.sample-entry-panel a'])}
                        run_case('entry-' + entry, choice)

                    def public_install():
                        visit('install/')
                        expect(page.get_by_role('heading', name='ホーム画面に追加', exact=True)).to_be_visible()
                        expect(page.get_by_role('button', name='ホーム画面に追加', exact=True)).to_be_enabled()
                        expect(page.locator('.top-install-instructions')).to_be_visible()
                        return {'contrast': contrast_pairs(page, ['.entry-choice-heading h1', '.entry-choice-heading > p:last-child', '.top-install-copy p', '.top-install-panel > button', '.top-install-instructions h2', '.top-install-instructions li'])}

                    run_case('public-install', public_install)

                    def login():
                        visit('login')
                        expect(page.get_by_role('heading', name='ログイン', exact=True)).to_be_visible()
                        expect(page.get_by_role('alert')).to_contain_text('通信状態を確認', timeout=15000)
                        confirm = page.get_by_role('button', name='確認メールを受け取る', exact=False)
                        expect(confirm).to_be_disabled()
                        result = contrast_pairs(page, ['.auth-box h1', '.auth-box .field input', '.auth-box .notice.error', '.auth-box .notice.error button'])
                        result.append(dict(selector='disabled-email-action', **contrast(confirm)))
                        result.append(dict(selector='email-placeholder', **contrast(page.locator('.auth-box input[type="email"]').first, pseudo='::placeholder')))
                        return {'contrast': result}

                    run_case('login-controls-and-errors', login)

                    def receive():
                        visit('receive')
                        expect(page.locator('[data-page="qr-receive"]')).to_be_visible()
                        expect(page.get_by_role('button', name='招待を受け取る', exact=False)).to_be_disabled()
                        disclosure = page.locator('.public-disclosure')
                        disclosure.locator('summary').click()
                        return {'contrast': contrast_pairs(page, ['.auth-box h1', '.auth-box > p', '.invite-state', '.public-disclosure summary', '.public-disclosure > div p'])}

                    run_case('qr-receive-gate', receive)

                    def chat():
                        visit('review/member/demo/messages')
                        page.locator('.thread-list a.person-row').first.click()
                        composer = page.get_by_role('textbox', name='メッセージ', exact=True)
                        expect(composer).to_be_visible()
                        composer.fill('表示色の確認 ' + scheme)
                        page.get_by_role('button', name='送信', exact=True).click()
                        expect(page.get_by_text('表示色の確認 ' + scheme, exact=True)).to_be_visible()
                        assert_page(page)
                        return {'contrast': contrast_pairs(page, ['.heading h1', '.conversation-header strong', '.bubble.mine > p', '.bubble.mine small', '.message-unsend', '.composer textarea'])}

                    run_case('synthetic-chat', chat)

                    def owner():
                        visit('review/owner/demo/invites')
                        result = contrast_pairs(page, ['.heading h1', '.heading .eyebrow', '.owner-content .field input'])
                        page.get_by_role('button', name='Toggle Sidebar', exact=True).click()
                        nav = page.locator('[data-sidebar="sidebar"] [data-sidebar="menu-button"][data-active="true"]').first
                        expect(nav).to_be_visible()
                        result.append(dict(selector='owner-active-menu', **contrast(nav)))
                        assert_page(page)
                        return {'contrast': result}

                    run_case('synthetic-owner-navigation', owner)
                    context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    assert checks and all(item['ok'] for item in checks), f'{sum(not item["ok"] for item in checks)} entry/appearance checks failed'


if __name__ == '__main__':
    main()
