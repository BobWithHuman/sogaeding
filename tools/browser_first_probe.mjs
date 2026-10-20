import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {launch,policy,baseURL,humanToken,screenshot} from './browser_helpers.mjs';
const evidence=path.resolve('artifacts/20261013-browser-b');
const records=[];
await policy(false);
let context=await launch(path.join(evidence,'untrusted-firefox-profile'));
try { const p=await context.newPage(); let denied=false;
  try {await p.goto(baseURL);} catch(error) {denied=error.message.includes('SEC_ERROR_UNKNOWN_ISSUER');}
  if(!denied) throw new Error('UNTRUSTED_CA_WAS_ACCEPTED');
  records.push({case:'TLS-browser-untrusted',denied:true,ignoreHTTPSErrors:false});
} finally {await context.close();}
await policy(true);
const seeded=spawnSync('C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
                      ['-X','utf8','tools/browser_profile_ca.py','artifacts/profile-browser-b-firefox'],{windowsHide:true});
if(seeded.status!==0) throw new Error('PROFILE_CA_PREPARATION_FAILED');
context=await launch('artifacts/profile-browser-b-firefox');
try { const p=await context.newPage(); p.setDefaultTimeout(8000);
  await p.goto(baseURL); await p.locator('#create').waitFor();
  records.push({case:'TLS-browser-trusted',title:await p.title(),browser:context.browser().version(),ignoreHTTPSErrors:false});
  await p.locator('#token').fill(await humanToken());
  await p.locator('#request').fill('브라우저 이슈 요약 요청');
  await p.locator('#create').click();
  await p.waitForFunction(()=>document.getElementById('status').textContent!=='');
  const sid=await p.locator('#session').inputValue();
  records.push({case:'B-01-first-session',created:!!sid,status:await p.locator('#status').innerText()});
  await screenshot(p,path.join(evidence,'first-session.png'));
  await fs.writeFile(path.join(evidence,'first-browser-records.json'),JSON.stringify(records,null,2));
  console.log(JSON.stringify(records));
  if(!sid) throw new Error('B01_BROWSER_SESSION_NOT_CREATED');
} finally {await context.close();}
