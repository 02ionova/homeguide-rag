"""Run against a local server. All chat requests are mocked; no live LLM calls."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    output = Path('data/screenshots')
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda exc: errors.append(str(exc)))
        page.goto(args.url)
        expect(page.locator('.appliance-button')).to_have_count(5)
        expect(page.locator('#appliance-count')).to_have_text('05')
        expect(page.locator('.document-link')).to_have_count(5)
        expect(page.locator('#model-label')).to_have_text('Bosch WAV28EH3GB')
        expect(page.locator('.suggestion')).to_have_count(2)
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)
        # Never make a paid request, even when the running server has credentials.
        page.route('**/api/chat', lambda route: route.fulfill(
            status=503, content_type='application/json',
            body=json.dumps({'detail': 'LLM_API_KEY is missing. Add your OpenAI API key to the local .env file and restart HomeGuide.'})))
        page.locator('#question').fill('How do I activate the child lock?')
        page.locator('#question').press('Enter')
        expect(page.locator('.message.error')).to_contain_text('LLM_API_KEY is missing')
        page.locator('#new-chat').click()
        expect(page.locator('.message')).to_have_count(0)
        page.unroute('**/api/chat')
        # Hold the response open to verify duplicate prevention and the loading state.
        pending = []
        page.route('**/api/chat', lambda route: pending.append(route))
        page.locator('#question').fill('How do I activate the child lock?')
        page.locator('#question').press('Shift+Enter')
        assert page.locator('#question').input_value().endswith('\n')
        page.locator('#question').press('Enter')
        expect(page.locator('.loading')).to_be_visible()
        expect(page.locator('#send')).to_be_disabled()
        page.locator('#question').press('Enter')
        assert len(pending) == 1
        source = {'filename': 'Bosch-WAV28EH3GB-Washing-Machine.pdf', 'page': 34, 'appliance': 'washing-machine',
                  'model': 'Bosch WAV28EH3GB', 'text': 'Press and hold the two Child Lock push 3 sec. buttons for approx. 3 seconds.',
                  'kind': 'semantic match', 'url': '/manuals/washing-machine#page=34', 'chunk_ids': []}
        mocked = {'answer': 'Hold the two Child Lock push 3 sec. buttons for about 3 seconds. [Bosch-WAV28EH3GB-Washing-Machine.pdf, p. 34]',
                  'status': 'answered', 'sources': [source]}
        pending.pop().fulfill(status=200, content_type='application/json', body=json.dumps(mocked))
        expect(page.locator('.message.assistant .citation')).to_have_attribute('href', '/manuals/washing-machine#page=34')
        page.locator('summary').click()
        expect(page.locator('.source-card')).to_contain_text('Press and hold')
        page.screenshot(path=str(output / 'chat-mocked.png'), full_page=True)
        page.locator('#new-chat').click()
        page.locator('[data-id="dishwasher"]').click()
        expect(page.locator('#model-label')).to_have_text('Bosch SMS8ZDI86M')
        page.locator('.suggestion').first.click()
        expect(page.locator('.loading')).to_be_visible()
        pending.pop().fulfill(status=200, content_type='application/json', body=json.dumps({
            'answer': '<img src=x onerror="window.unsafe=true"> [Bosch-WAV28EH3GB-Washing-Machine.pdf, p. 34]',
            'status': 'answered', 'sources': [source]}))
        expect(page.locator('.message.assistant .message-body')).to_contain_text('<img')
        expect(page.locator('.message-body img')).to_have_count(0)
        assert page.evaluate('window.unsafe === undefined')
        page.locator('[data-id="coffee-machine"]').click()
        expect(page.locator('.message')).to_have_count(0)
        expect(page.locator('#model-label')).to_have_text('Bosch TIS 3.3. family')
        page.locator('#question').fill('What is tomorrow’s weather?')
        page.locator('#question').press('Enter')
        expect(page.locator('.loading')).to_be_visible()
        pending.pop().fulfill(status=200, content_type='application/json', body=json.dumps({
            'answer': 'I don’t know based on the provided documents.', 'status': 'insufficient_information', 'sources': []}))
        expect(page.locator('.message.assistant')).to_contain_text('I don’t know based on the provided documents.')
        page.locator('#new-chat').click()
        page.locator('#question').fill('Connection test')
        page.locator('#question').press('Enter')
        expect(page.locator('.loading')).to_be_visible()
        pending.pop().abort('failed')
        expect(page.locator('.message.error')).to_contain_text('Cannot connect')
        page.locator('#new-chat').click()
        # New documents have independent models, suggested questions and PDF routes.
        for appliance, model, filename, physical_page, excerpt in [
            ('oven', 'Bosch HBG936C.1 family', 'Bosch-HBG936C.1-Oven.pdf', 18,
             'The childproof lock can be activated regardless of whether the appliance is on or off. Press and hold for approx. 4 seconds.'),
            ('microwave', 'Bosch BFL524MB2', 'Bosch-BFL524MB2-Microwave.pdf', 9,
             'Use heat-resistant, microwave-safe glass, glass ceramic, porcelain, temperature-resistant plastic or fully glazed ceramic without cracks.'),
        ]:
            page.locator(f'[data-id="{appliance}"]').click()
            expect(page.locator('#model-label')).to_have_text(model)
            expect(page.locator('.suggestion')).to_have_count(2)
            assert page.locator(f'[data-id="{appliance}"] svg').count() == 1
            page.locator('.suggestion').first.click()
            expect(page.locator('.loading')).to_be_visible()
            request = pending.pop()
            assert request.request.post_data_json['appliance'] == appliance
            new_source = {**source, 'filename': filename, 'page': physical_page,
                          'appliance': appliance, 'model': model, 'text': excerpt,
                          'url': f'/manuals/{appliance}#page={physical_page}'}
            request.fulfill(status=200, content_type='application/json', body=json.dumps({
                'answer': f'Mocked manual-specific answer. [{filename}, p. {physical_page}]',
                'status': 'answered', 'sources': [new_source]}))
            expect(page.locator('.message.assistant .citation')).to_have_attribute('href', new_source['url'])
            pdf_response = page.request.get(f'{args.url}/manuals/{appliance}')
            assert pdf_response.ok and pdf_response.body().startswith(b'%PDF')
            page.locator('#new-chat').click()
        page.screenshot(path=str(output / 'five-appliances.png'), full_page=True, animations='disabled')
        # Mobile navigation, keyboard access, model switch, and overflow checks.
        for width, height in [(390, 844), (320, 740), (768, 1024)]:
            page.set_viewport_size({'width': width, 'height': height})
            if width <= 760:
                for appliance in ('washing-machine', 'oven', 'microwave'):
                    page.locator('#menu-toggle').click()
                    expect(page.locator('#menu-toggle')).to_have_attribute('aria-expanded', 'true')
                    page.locator(f'[data-id="{appliance}"]').click()
                    expect(page.locator('#menu-toggle')).to_have_attribute('aria-expanded', 'false')
                    expect(page.locator(f'[data-id="{appliance}"]')).to_have_attribute('aria-pressed', 'true')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Overflow at {width}px'
            page.screenshot(path=str(output / f'mobile-{width}.png'), full_page=True, animations='disabled')
        assert not errors, errors
        browser.close()
        print('Browser checks passed: desktop/mobile layouts, no overflow (1440/768/390/320px), missing-key error, Enter/Shift+Enter, duplicate prevention, loading, mocked cited response and sources, safe HTML rendering, fallback, connection error, appliance/new-chat resets. Screenshots: data/screenshots/. Live LLM was not called.')


if __name__ == '__main__':
    main()
