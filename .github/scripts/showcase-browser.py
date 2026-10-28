"""Verify the new synthetic Review showcase while preserving the existing production root.

All backend requests and non-GET/HEAD network requests are blocked. No real
registration, acceptance, email or production content operation is performed.
"""
import http.server
import json
import os
import pathlib
import sys
import threading
import traceback
from urllib.parse import parse_qs, unquote, urlsplit

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


def contrast(locator, *, pseudo=None, label=None):
    expect(locator).to_be_visible()
    result = locator.evaluate(CONTRAST_JS, {'pseudo': pseudo})
    diagnostic = dict(selector=label or str(locator), **result)
    assert result['visible'], diagnostic
    assert not result['imageBacked'], 'Choose an opaque text/control surface: ' + str(diagnostic)
    assert result['ratio'] >= result['required'], diagnostic
    return result


def contrast_pairs(page, selectors):
    results = []
    for selector in selectors:
        locator = page.locator(selector).first
        result = contrast(locator, label=selector)
        results.append(dict(selector=selector, **result))
    return results


def document_box(locator):
    return locator.evaluate('(e) => { const r=e.getBoundingClientRect(); return {top:r.top+scrollY,bottom:r.bottom+scrollY,width:r.width,height:r.height,fontSize:parseFloat(getComputedStyle(e).fontSize)}; }')


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else 'release/app'
    live = target.startswith('https://')
    out = pathlib.Path('verification')
    out.mkdir(exist_ok=True)
    server, checks = None, []
    if live:
        root_base = target.rstrip('/') + '/'
    else:
        root = pathlib.Path(target).resolve()
        assert (root / 'review/member/index.html').is_file(), 'Missing synthetic Review member build'

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def translate_path(self, path):
                local = unquote(urlsplit(path).path).removeprefix('/muumei-public/')
                path = (root / local).resolve()
                return str(path if path.is_relative_to(root) and path.exists() else root / '404.html')

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        root_base = f'http://127.0.0.1:{server.server_port}/muumei-public/'
    base = root_base + 'review/member/'
    root_origin = (urlsplit(root_base).scheme, urlsplit(root_base).netloc)
    network = []

    def record(name, ok, **details):
        checks.append(dict(name=name, ok=bool(ok), **details))
        (out / 'showcase-browser.json').write_text(json.dumps(dict(
            live=live, target='synthetic-review-only', production_data_mutated=False,
            real_registration_tested=False, real_work_acceptance_tested=False,
            native_install_attempted=False, widths=[390, 1280], color_schemes=['light', 'dark'],
            total=len(checks), failures=sum(not item['ok'] for item in checks),
            external_posts=sum(item['method'] not in ['GET', 'HEAD'] and item['external'] for item in network),
            backend_attempts=sum(item['backend'] for item in network),
            checks=checks, network=network,
        ), ensure_ascii=False, indent=2))
        print(name, 'PASS' if ok else 'FAIL', details, flush=True)

    def loaded_image(page, image):
        image.scroll_into_view_if_needed()
        page.wait_for_function('(image)=>image.complete&&image.naturalWidth>0', arg=image.element_handle(), timeout=10000)
        return image.get_attribute('src')

    def utility(page):
        bar = page.locator('.app-utility-bar')
        expect(bar).to_have_count(1)
        expect(bar).to_contain_text('サンプル')
        size = bar.evaluate('(e)=>({height:e.getBoundingClientRect().height,scroll:e.scrollHeight,client:e.clientHeight})')
        assert 0 < size['height'] <= 44 and size['scroll'] <= size['client'] + 2, size
        return contrast_pairs(page, ['.utility-caption', '.utility-actions button'])

    try:
        with sync_playwright() as playwright:
            engines = [x.strip() for x in os.environ.get('MUUMEI_BROWSER_ENGINES', 'chromium,firefox,webkit').split(',') if x.strip()]
            assert engines and set(engines) <= {'chromium', 'firefox', 'webkit'}
            for engine in engines:
                browser = getattr(playwright, engine).launch()
                for width in [390, 1280]:
                    for scheme in ['light', 'dark']:
                        context = browser.new_context(viewport={'width': width, 'height': 900}, color_scheme=scheme, reduced_motion='reduce', service_workers='block')
                        context.add_init_script("window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();event.stopImmediatePropagation();},true);")
                        local_network = []

                        def observe(request):
                            u = urlsplit(request.url)
                            if u.scheme not in ['http', 'https']:
                                return
                            item = dict(method=request.method, path=u.path,
                                        external=(u.scheme, u.netloc) != root_origin,
                                        backend=(u.hostname or '').endswith('.supabase.co'))
                            local_network.append(item)
                            network.append(dict(engine=engine, width=width, scheme=scheme, **item))

                        def protect(route):
                            u = urlsplit(route.request.url)
                            if route.request.method not in ['GET', 'HEAD'] or (u.hostname or '').endswith('.supabase.co') or (u.scheme in ['http', 'https'] and (u.scheme, u.netloc) != root_origin):
                                route.abort()
                            else:
                                route.continue_()

                        context.on('request', observe)
                        context.route('**/*', protect)
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))

                        def run_case(label, callback):
                            errors.clear()
                            name = f'{engine}:{width}:{scheme}:{label}'
                            try:
                                details = callback() or {}
                                assert not errors, errors
                                record(name, True, **details)
                            except Exception as error:
                                record(name, False, error=str(error), traceback=traceback.format_exc(limit=5))
                                page.screenshot(path=str(out / f'showcase-{engine}-{width}-{scheme}-{label}-failure.png'), full_page=True)

                        def visit(route=''):
                            response = page.goto(base + route, wait_until='domcontentloaded')
                            assert response and response.status == 200, f'HTTP {response.status if response else None}'
                            expect(page.locator('#main')).to_be_visible(timeout=20000)
                            page.wait_for_function('''() => [...document.images].filter(image => {const box=image.getBoundingClientRect();return box.width>0&&box.height>0&&box.top<innerHeight&&box.bottom>0}).every(image => image.complete&&image.naturalWidth>0)''', timeout=15000)
                            layout = page.evaluate('''() => ({
                              overflow:document.documentElement.scrollWidth-innerWidth,
                              scheme:getComputedStyle(document.documentElement).colorScheme,
                              broken:[...document.images].filter(i=>i.getBoundingClientRect().top<innerHeight&&i.getBoundingClientRect().bottom>0&&(!i.complete||!i.naturalWidth)).map(i=>i.getAttribute('src'))
                            })''')
                            assert layout['overflow'] <= 2 and not layout['broken'] and layout['scheme'] == scheme, layout
                            return layout

                        def top():
                            visit()
                            expect(page.locator('[data-page="community-landing"]')).to_be_visible()
                            expect(page.locator('#sns-title')).to_contain_text('またね')
                            result = utility(page)
                            text = page.locator('#main').inner_text()
                            assert not any(word in text for word in ['準備中', '受付停止', '登録受付はまだ']), text
                            dock = page.locator('#entrances.entry-dock')
                            cards = dock.locator('.entry-dock-grid > a.entry-dock-app')
                            expect(cards).to_have_count(3)
                            expected = [urlsplit(base).path + 'entry/' + key + '/' for key in ['private', 'connection', 'work']]
                            actual_paths = cards.evaluate_all('(els)=>els.map(e=>new URL(e.href).pathname)')
                            assert actual_paths == expected, dict(actual=actual_paths, expected=expected)
                            assert dock.evaluate('(e)=>e===document.querySelector("#main").lastElementChild'), 'The three entrances must be the final main section'
                            boxes = cards.evaluate_all('(els)=>els.map(e=>{const r=e.getBoundingClientRect();return {top:r.top,left:r.left,right:r.right}})')
                            assert max(x['top'] for x in boxes) - min(x['top'] for x in boxes) <= 3, boxes
                            assert all(boxes[i]['right'] <= boxes[i+1]['left'] + 2 for i in range(2)), boxes
                            sample = dock.locator(':scope > .sample-entry-panel')
                            a, b = document_box(sample), document_box(dock.locator('.entry-dock-grid'))
                            assert a['top'] >= b['bottom'] + 8 and a['height'] < b['height'], (a, b)
                            assert a['width'] <= (342 if width < 768 else 437), a
                            expect(sample).to_contain_text('架空データ')
                            photos = page.locator('.sns-moment-photo img')
                            expect(photos).to_have_count(3)
                            photo_sources = [loaded_image(page, photos.nth(i)) for i in range(3)]
                            assert len(set(photo_sources)) == 3, dict(photo_sources=photo_sources)
                            opening_photo = page.locator('.sns-moment-photo').first
                            previous_body_overflow = page.locator('body').evaluate('(element)=>element.style.overflow')
                            opening_photo.click()
                            viewer = page.get_by_role('dialog', name='写真を大きく見る')
                            expect(viewer).to_be_visible()
                            page.wait_for_function("document.body.style.overflow === 'hidden'", timeout=5000)
                            assert page.locator('body').evaluate('(element)=>element.style.overflow') == 'hidden', 'Photo viewer must lock background scrolling'
                            viewer_image = viewer.locator('img')
                            expect(viewer_image).to_have_attribute('src', photo_sources[0])
                            first = loaded_image(page, viewer_image)
                            viewer.get_by_role('button', name='次の写真', exact=True).click()
                            expect(viewer_image).to_have_attribute('src', photo_sources[1])
                            second = loaded_image(page, viewer_image)
                            page.keyboard.press('ArrowRight')
                            expect(viewer_image).to_have_attribute('src', photo_sources[2])
                            third = loaded_image(page, viewer_image)
                            assert len({first, second, third}) == 3, dict(first=first, second=second, third=third)
                            viewer.get_by_role('button', name='前の写真', exact=True).click()
                            expect(viewer_image).to_have_attribute('src', photo_sources[1])
                            assert loaded_image(page, viewer_image) == second, dict(expected=second, actual=viewer_image.get_attribute('src'))
                            page.keyboard.press('Escape')
                            expect(viewer).to_have_count(0)
                            expect(opening_photo).to_be_focused()
                            page.wait_for_function('(expected)=>document.body.style.overflow === expected', arg=previous_body_overflow, timeout=5000)
                            actual_body_overflow = page.locator('body').evaluate('(element)=>element.style.overflow')
                            assert actual_body_overflow == previous_body_overflow, dict(expected=previous_body_overflow, actual=actual_body_overflow)
                            next_section = page.locator('.sns-intro-next')
                            expect(next_section).to_be_visible()
                            next_layout = next_section.evaluate('''(section) => {
 const copy = section.querySelector(':scope > div');
 const heading = copy.querySelector('h2');
 const paragraph = copy.querySelector('p:last-child');
 return {copyWidth:copy.getBoundingClientRect().width,headingHeight:heading.getBoundingClientRect().height,headingLine:parseFloat(getComputedStyle(heading).lineHeight),paragraphWidth:paragraph.getBoundingClientRect().width,writingMode:getComputedStyle(paragraph).writingMode,sectionHeight:section.getBoundingClientRect().height};
}''')
                            assert next_layout['copyWidth'] >= 200 and next_layout['paragraphWidth'] >= 200, next_layout
                            assert next_layout['headingHeight'] <= next_layout['headingLine'] * 2 + 3, next_layout
                            assert next_layout['writingMode'] == 'horizontal-tb', next_layout
                            result += contrast_pairs(page, ['.public-login', '.entry-dock-heading h2', '.entry-dock-app > strong', '.entry-dock-note', '.sample-entry-panel p', '.sample-entry-panel > a'])
                            dock_hints = page.locator('.entry-dock-app > small')
                            expect(dock_hints).to_have_count(3)
                            if width <= 600:
                                for index in range(3):
                                    expect(dock_hints.nth(index)).to_be_hidden()
                            else:
                                result += contrast_pairs(page, ['.entry-dock-app > small'])
                            if engine == 'chromium':
                                page.screenshot(path=str(out / f'showcase-top-{width}-{scheme}.png'), full_page=True)
                            sample.locator('a').click()
                            expect(page.get_by_role('button', name='メンバー画面', exact=True)).to_be_visible()
                            expect(page.get_by_role('button', name='確認用管理画面', exact=True)).to_be_visible()
                            expect(page.frame_locator('#view').locator('.home-feature-copy')).to_be_visible()
                            expect(page.locator('#load-status')).to_contain_text('表示完了')
                            assert urlsplit(page.url).path.rstrip('/') == (urlsplit(root_base).path + 'review').rstrip('/'), page.url
                            visit()
                            page.locator('.app-utility-bar').get_by_role('button', name='ホーム画面に追加', exact=True).click()
                            expect(page.locator('[data-page="public-install"]')).to_be_visible()
                            expect(page.locator('.top-install-instructions')).to_be_visible()
                            return {'contrast': result, 'sample_photographs_loaded': 3, 'entry_paths': expected, 'next_layout': next_layout, 'photo_focus_restored': True}

                        run_case('top-bottom-three-entrances-photos-and-compact-bar', top)

                        for key in ['private', 'connection', 'work']:
                            def entry(key=key):
                                visit('entry/' + key + '/')
                                panel = page.locator('.entry-real-panel')
                                expect(panel).to_contain_text('サンプルの操作')
                                action = panel.locator('.entry-real-action')
                                sample = page.locator('.entry-choice > .sample-entry-panel')
                                expect(sample).to_contain_text('架空データ')
                                assert action.get_attribute('href') != sample.locator('a').get_attribute('href')
                                assert document_box(sample)['top'] >= document_box(panel)['bottom'] + 20
                                result = utility(page) + contrast_pairs(page, ['.entry-choice-heading h1', '.entry-real-panel h2', '.entry-real-panel p', '.entry-real-action', '.sample-entry-panel p'])
                                if engine == 'chromium' and width == 390 and key == 'private':
                                    page.screenshot(path=str(out / f'showcase-entry-private-390-{scheme}.png'), full_page=True)
                                action.click()
                                if key == 'work':
                                    expect(page.locator('.public-work-form')).to_be_visible()
                                    expect(page.get_by_role('button', name='サンプルで送信を試す', exact=True)).to_be_visible()
                                    visit('entry/work/')
                                    page.locator('.sample-entry-panel a').click()
                                    expect(page.locator('.public-work-form')).to_be_visible()
                                    assert urlsplit(page.url).path.rstrip('/') == (urlsplit(base).path + 'demo/work-public').rstrip('/'), page.url
                                else:
                                    expect(page.locator('.member-experience')).to_be_visible()
                                    expect(page.locator('.home-feature-copy')).to_be_visible()
                                return {'contrast': result, 'synthetic_destination': True}
                            run_case('sample-entry-' + key, entry)

                        def feed():
                            visit('demo/home/')
                            expect(page.locator('.home-feature-copy h2')).to_be_visible()
                            if engine == 'chromium':
                                page.screenshot(path=str(out / f'showcase-member-home-{width}-{scheme}.png'), full_page=True)
                            visit('demo/moments/')
                            expect(page.get_by_role('textbox', name='今日のひとこと')).to_be_visible()
                            photos = page.locator('.moment-photo img')
                            expect(photos).to_have_count(3)
                            photo_sources = [loaded_image(page, photos.nth(i)) for i in range(3)]
                            assert len(set(photo_sources)) == 3, dict(photo_sources=photo_sources)
                            if engine == 'chromium' and width == 390:
                                page.screenshot(path=str(out / f'showcase-member-moments-390-{scheme}.png'), full_page=True)
                            trigger = page.get_by_role('button', name='写真を大きく開く', exact=True).first
                            trigger.click()
                            viewer = page.get_by_role('dialog', name='投稿写真')
                            expect(viewer).to_be_visible()
                            loaded_image(page, viewer.locator('img'))
                            page.keyboard.press('Escape')
                            expect(viewer).to_have_count(0)
                            expect(trigger).to_be_focused()
                            body = 'Reviewだけの近況表示試験'
                            page.get_by_role('textbox', name='今日のひとこと').fill(body)
                            page.get_by_role('button', name='投稿する', exact=True).click()
                            expect(page.get_by_text(body, exact=True)).to_be_visible()
                            page.reload(wait_until='domcontentloaded')
                            expect(page.get_by_text(body, exact=True)).to_be_visible()
                            return {'contrast': utility(page) + contrast_pairs(page, ['#main h1', 'article.moment p', '.post-composer textarea']), 'synthetic_post_persists': True, 'photographs_loaded': 3}

                        run_case('member-feed-three-photos-and-local-post', feed)

                        for route in ['next', 'people', 'pass']:
                            def member_page(route=route):
                                visit('demo/' + route + '/')
                                return {'contrast': utility(page) + contrast_pairs(page, ['#main h1'])}
                            run_case('member-' + route, member_page)

                        def profile():
                            visit('demo/my/')
                            expect(page.locator('.profile-about')).to_be_visible()
                            interests = page.locator('.profile-interests[aria-label="好きなこと"]')
                            expect(interests).to_be_visible()
                            assert interests.locator('span').count() > 0
                            work = page.locator('.profile-work-about')
                            expect(work).not_to_have_attribute('open', '')
                            if engine == 'chromium' and width == 390:
                                page.screenshot(path=str(out / f'showcase-member-profile-390-{scheme}.png'), full_page=True)
                            work.locator('summary').click()
                            expect(work).to_have_attribute('open', '')
                            result = utility(page) + contrast_pairs(page, ['.profile-about h2', '.profile-about > p:last-of-type', '.profile-interests span', '.profile-work-about summary'])
                            page.get_by_role('button', name='編集する', exact=True).click()
                            form = page.locator('.profile-edit-form')
                            expect(form).to_be_visible()
                            optional = form.locator('.profile-work-settings')
                            expect(optional).not_to_have_attribute('open', '')
                            intro = 'これはReview内だけに保存する自己紹介です。'
                            page.get_by_role('textbox', name='ひとこと自己紹介', exact=False).fill(intro)
                            page.get_by_role('button', name='プロフィールを保存する', exact=True).click()
                            expect(page.locator('.profile-about')).to_contain_text(intro)
                            return {'contrast': result, 'profile_edit_is_local': True}

                        run_case('profile-interests-and-optional-work-fields', profile)

                        def chat():
                            visit('demo/messages/')
                            page.locator('.thread-list a.person-row').first.click()
                            composer = page.get_by_role('textbox', name='メッセージ', exact=True)
                            expect(composer).to_be_visible()
                            body = 'Review送信取消の検証'
                            composer.fill(body)
                            page.get_by_role('button', name='送信', exact=True).click()
                            bubble = page.locator('.bubble.mine').filter(has=page.get_by_text(body, exact=True))
                            expect(bubble).to_be_visible()
                            peer = page.locator('.bubble:not(.mine):not(.deleted)')
                            assert peer.count() > 0
                            expect(peer.get_by_role('button', name='送信を取り消す', exact=True)).to_have_count(0)
                            bubble.get_by_role('button', name='送信を取り消す', exact=True).click()
                            dialog = page.get_by_role('dialog')
                            dialog.get_by_role('button', name='やめる', exact=True).click()
                            expect(bubble).to_be_visible()
                            bubble.get_by_role('button', name='送信を取り消す', exact=True).click()
                            dialog.get_by_role('button', name='取り消す', exact=True).click()
                            expect(page.get_by_text(body, exact=True)).to_have_count(0)
                            page.reload(wait_until='domcontentloaded')
                            expect(page.get_by_text(body, exact=True)).to_have_count(0)
                            expect(page.locator('.bubble.deleted').last).to_contain_text('メッセージの送信が取り消されました')
                            return {'contrast': utility(page) + contrast_pairs(page, ['.conversation-header strong', '.composer textarea', '.bubble.deleted p']), 'sender_only_withdrawal_persists': True}

                        run_case('sender-only-chat-withdrawal', chat)

                        def work_sample():
                            visit('jobs/')
                            form = page.locator('.public-work-form')
                            expect(form).to_be_visible()
                            expect(page.locator('.public-work-job').first).to_be_visible()
                            scenes = page.locator('.public-work-job-image > img')
                            assert len({loaded_image(page, image) for image in scenes.all()}) >= 3, 'Work samples need distinct scenes appropriate to their categories'
                            if engine == 'chromium' and width == 390:
                                for image in page.locator('.public-work img').all():
                                    loaded_image(page, image)
                                page.screenshot(path=str(out / f'showcase-public-work-390-{scheme}.png'), full_page=True)
                            page.locator('.public-work-job').first.get_by_role('button', name='詳細・応募', exact=False).click()
                            dialog = page.get_by_role('dialog')
                            expect(dialog).to_be_visible()
                            dialog.get_by_role('button', name='この募集に応募・相談する', exact=False).click()
                            expect(dialog).to_be_hidden()
                            expect(form.locator('[name="job_id"]')).not_to_have_value('')
                            form.locator('[name="name"]').fill('架空の利用者')
                            form.locator('[name="contact_value"]').fill('review@example.invalid')
                            form.locator('[name="message"]').fill('本番には送信しない、Review専用の相談内容です。')
                            result = utility(page) + contrast_pairs(page, ['.public-work-field input', '.public-work-reply > input', '.public-work-field textarea', '.public-work-submit'])
                            form.get_by_role('button', name='サンプルで送信を試す', exact=True).click()
                            expect(form.get_by_role('heading', name='サンプルの送信が完了しました。', exact=True)).to_be_visible()
                            expect(form).to_contain_text('SAMPLE-2026')
                            expect(form).to_contain_text('通知やメール送信は行っていません')
                            return {'contrast': result, 'real_submission': False, 'receipt': 'SAMPLE-2026'}

                        run_case('work-sample-local-receipt-no-delivery', work_sample)

                        def boundary():
                            assert not any(x['backend'] for x in local_network), local_network
                            assert not any(x['method'] not in ['GET', 'HEAD'] for x in local_network), local_network
                            assert not any(x['external'] for x in local_network), local_network
                            response = context.request.get(base + 'muumei-config.json')
                            assert response.status == 200
                            config = response.json()
                            assert not config.get('url') and not config.get('key') and not config.get('ready')
                            return {'external_posts': 0, 'backend_attempts': 0, 'non_get_requests': 0, 'empty_backend_config': True}

                        run_case('synthetic-network-and-empty-config-boundary', boundary)
                        context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    assert checks and all(x['ok'] for x in checks), f'{sum(not x["ok"] for x in checks)} showcase checks failed'


if __name__ == '__main__':
    main()
