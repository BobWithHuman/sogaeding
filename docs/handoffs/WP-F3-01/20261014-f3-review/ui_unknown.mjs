import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {firefox}=require('C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const label=process.argv[2];
const root=path.resolve('C:/sogaeding');
const source=path.resolve(root,process.argv[3]??'src/app/web');
const out=path.resolve(root,'artifacts/20261014-f3-review',label);
await fs.mkdir(out,{recursive:false});
const env={};
for(const key of ['PATH','SystemRoot','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])
  if(process.env[key])env[key]=process.env[key];
const context=await firefox.launchPersistentContext(path.join(out,'profile'),{headless:true,
  executablePath:path.join(root,'artifacts/browser-tools-b/firefox-1538/firefox/firefox.exe'),
  ignoreHTTPSErrors:false,env,viewport:{width:1280,height:900}});
try {
  const page=await context.newPage();
  const html=(await fs.readFile(path.join(source,'index.html'),'utf8')).replace(/<script[^>]*src="\/ui.js"[^>]*><\/script>/,'');
  await page.setContent(html);
  await page.addScriptTag({content:await fs.readFile(path.join(source,'ui.js'),'utf8')});
  await page.evaluate(()=>decisionCards(document.getElementById('timeline'),{
    checks:[{call_id:'review-unknown',decision:'ALLOW',execution_state:'UNKNOWN',reason_codes:['USER_INTENT_SUPPORTED'],
      decision_stage:'SEMANTIC',source_ids:[],evidence_refs:[]}],
    executions:[{call_id:'review-unknown',state:'UNKNOWN',receipt:null}]}));
  const text=await page.locator('#timeline').textContent();
  await page.screenshot({path:path.join(out,'unknown-card.png'),fullPage:true});
  const record={mode:'OFFLINE_FIREFOX_RENDER_FIXTURE',browser:context.browser().version(),
    source,ui_text:text,actual_effects:'NOT_OBSERVED',server_calls:0,paid_requests:0};
  await fs.writeFile(path.join(out,'record.json'),JSON.stringify(record,null,2));
  assert.ok(!text.includes('실제 댓글 효과 0개'),'UNKNOWN receipt-free state must not claim confirmed zero effects');
  console.log(JSON.stringify({...record,result:'PASS'}));
}finally {await context.close();}
