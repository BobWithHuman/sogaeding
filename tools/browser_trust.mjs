import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const require = createRequire(import.meta.url);
const bundle = 'C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium} = require(bundle + '/playwright');
const profile = path.resolve('artifacts/profile-browser-b');
const manual = process.argv.includes('--native-picker');
const context = await chromium.launchPersistentContext(profile, {headless:!manual,
  executablePath:'C:/Users/qkaeh/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'});
try {
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  await page.goto('chrome://certificate-manager/localcerts/usercerts');
  await page.locator('certificate-list:visible #listHeader').first().waitFor();
  const imports = page.locator('certificate-list:visible #importCert');
  await imports.first().waitFor();
  if (manual) {
    await imports.first().click();
    console.log('Native picker open: select only this application runtime CA. No global trust change.');
    await page.getByText('With Human development CA',{exact:false}).first().waitFor({timeout:120000});
  } else {
    const chooser = page.waitForEvent('filechooser',{timeout:4000});
    await imports.first().click();
    await (await chooser).setFiles(path.resolve('artifacts/runtime-browser-b/ca.pem'));
  }
  await page.screenshot({path:path.resolve('artifacts/20261013-browser-b/trust-import.png')});
  console.log(JSON.stringify({browser:context.browser()?.version(), profile,
                              buttons:await page.getByRole('button').allTextContents()}));
} finally { await context.close(); }
