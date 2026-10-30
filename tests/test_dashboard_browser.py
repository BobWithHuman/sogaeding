"""Run with the development-only Playwright package and Chromium installed."""
import re
import unittest
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'Install development-only Playwright and Chromium')
class DashboardBrowserTest(unittest.TestCase):
    def test_hostile_api_values_and_distribution(self):
        assets = Path(__file__).resolve().parents[1] / 'src/app/web/observatory'
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                markup = re.sub(r'<script[^>]*src=[^>]*></script>', '', (assets / 'index.html').read_text())
                page.set_content(markup)
                page.evaluate('window.fetch=()=>new Promise(()=>{});window.attacked=false')
                page.add_script_tag(content=(assets / 'app.js').read_text())
                result = page.evaluate('''() => {
                    const attack='<img src=x onerror="window.attacked=true"><svg onload="window.attacked=true">';
                    state.summary={total_calls:0,effective_decisions:{ALLOW:Infinity,DENY:-1,ASK:999,UNKNOWN:NaN,[attack]:1}};
                    renderDistribution();
                    const widths=[...document.querySelectorAll('.bar-fill')].map(e=>e.style.width);
                    const preview={status:'DISPLAYED',text:attack};
                    const item={tool:attack,target_display:attack,content_preview:{user_request:preview,fields:[{...preview,label:attack}],note:attack,before_note:attack}};
                    document.getElementById('detailBody').innerHTML=renderTaskContext(item)+renderContentPreview(item);
                    renderSecurity.call(null);
                    return {widths,labels:[...document.querySelectorAll('.bar-row>span')].map(e=>e.textContent),images:document.querySelectorAll('#detailBody img,#detailBody svg').length,text:document.getElementById('detailBody').textContent};
                }''')
                page.wait_for_timeout(100)
                self.assertFalse(page.evaluate('window.attacked'))
                self.assertEqual(result['widths'], ['0%', '0%', '100%', '0%'])
                self.assertEqual(result['labels'], ['ALLOW', 'DENY', 'ASK', 'UNKNOWN'])
                self.assertEqual(result['images'], 0)
                self.assertIn('<img', result['text'])
            finally:
                browser.close()
