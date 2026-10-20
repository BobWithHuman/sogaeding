// Read-only inventory of installed Chromium's profile certificate manager.
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(import.meta.url);
const bundle = 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium} = require(bundle + '/playwright');
const target = path.resolve(process.argv[2]);
await fs.mkdir(target, {recursive: true});
const context = await chromium.launchPersistentContext(path.join(target, 'trust-probe-profile'), {
  headless: true, executablePath: 'C:/Users/qkaeh/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'});
try {
  const page = await context.newPage();
  await page.goto('chrome://certificate-manager');
  await page.getByText(/사용자가 설치|User installed/).first().waitFor();
  await page.getByText(/사용자가 설치|User installed/).first().click();
  console.log(JSON.stringify({browser:context.browser()?.version(), url:page.url(),
                              buttons:await page.getByRole('button').allTextContents(),
                              lists:await page.locator('certificate-list:visible').evaluateAll(es=>es.map(e=>({
                                id:e.id, header:e.shadowRoot.querySelector('#listHeader')?.innerText})))}));
  await page.screenshot({path:path.join(target, 'certificate-manager.png')});
} finally { await context.close(); }
