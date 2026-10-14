"""Run against a local server. Chat successes are explicit browser mocks, not live LLM calls."""
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
        expect(page.locator('.appliance-button')).to_have_count(3)
        expect(page.locator('#model-label')).to_have_text('Bosch WAV28EH3GB')
        expect(page.locator('.suggestion')).to_have_count(2)
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.screenshot(path=str(output / 'desktop.png'), full_page=True)
        page.locator('#question').fill('How do I activate the child lock?')
        page.locator('#question').press('Enter')
        expect(page.locator('.message.error')).to_contain_text('LLM_API_KEY is missing')
        page.locator('#new-chat').click()
        expect(page.locator('.message')).to_have_count(0)
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
        source = {'filename': '9001599859_B.pdf', 'page': 34, 'appliance': 'washing-machine',
                  'model': 'Bosch WAV28EH3GB', 'text': 'Press and hold the two Child Lock push 3 sec. buttons for approx. 3 seconds.',
                  'kind': 'semantic match', 'url': '/manuals/washing-machine#page=34', 'chunk_ids': []}
        mocked = {'answer': 'Hold the two Child Lock push 3 sec. buttons for about 3 seconds. [9001599859_B.pdf, p. 34]',
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
            'answer': '<img src=x onerror="window.unsafe=true"> [9001599859_B.pdf, p. 34]',
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
        # Mobile navigation, keyboard access, model switch, and overflow checks.
        for width, height in [(390, 844), (320, 740), (768, 1024)]:
            page.set_viewport_size({'width': width, 'height': height})
            if width <= 760:
                page.locator('#menu-toggle').click()
                expect(page.locator('#menu-toggle')).to_have_attribute('aria-expanded', 'true')
                page.locator('[data-id="washing-machine"]').click()
                expect(page.locator('#menu-toggle')).to_have_attribute('aria-expanded', 'false')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Overflow at {width}px'
            page.screenshot(path=str(output / f'mobile-{width}.png'), full_page=True, animations='disabled')
        assert not errors, errors
        browser.close()
        print('Browser checks passed: desktop/mobile layouts, no overflow (1440/768/390/320px), missing-key error, Enter/Shift+Enter, duplicate prevention, loading, mocked cited response and sources, safe HTML rendering, fallback, connection error, appliance/new-chat resets. Screenshots: data/screenshots/. Live LLM was not called.')


if __name__ == '__main__':
    main()
