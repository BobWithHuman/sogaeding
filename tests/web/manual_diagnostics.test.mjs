import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {launch} from '../../tools/browser_helpers.mjs';
const sid='11111111-1111-4111-8111-111111111111';
const call='22222222-2222-4222-8222-222222222222';
const context=await launch('artifacts/profile-manual-offline-dom');
const page=await context.newPage();
const html=await fs.readFile('src/app/web/index.html','utf8');
const js=await fs.readFile('src/app/web/ui.js','utf8');
const paths=[];
let code='QUOTE_MISMATCH';
await page.route('http://manual-offline.test/**',async route=>{
  const path=new URL(route.request().url()).pathname;paths.push(path);
  if(path==='/') return route.fulfill({contentType:'text/html',body:html});
  if(path==='/ui.js') return route.fulfill({contentType:'application/javascript',body:js});
  const data=path.endsWith('/diagnostics')?{analyses:[{call_id:call,diagnostics:[{code,view:'B'}]}]}:
    {session_id:sid,status:'ACTIVE',task_kind:'POST_COMMENT',policy_version:'test',sources:[],approvals:[],executions:[],events:[],
      checks:[{call_id:call,decision:'DENY',reason_codes:['ANALYSIS_UNAVAILABLE'],decision_stage:'SEMANTIC',source_ids:[],execution_state:'NOT_STARTED'}]};
  return route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
});
try {
  await page.goto('http://manual-offline.test/');
  await page.locator('#token').fill('fake-offline-human-token');
  await page.locator('#session').fill(sid);
  await page.locator('#load').click();
  await page.waitForFunction(()=>!document.getElementById('load').disabled);
  const text=await page.locator('#timeline').textContent();
  assert.match(text,/분석 실패 · 실행 보류/);assert.match(text,/QUOTE_MISMATCH/);assert.match(text,/댓글 효과 0개/);
  assert.equal(text.includes('자동 차단'),false);
  code='<img src=x onerror=window.manualInjected=true>';
  await page.locator('#load').click();
  await page.waitForFunction(()=>!document.getElementById('load').disabled);
  assert.equal(await page.locator('#timeline img').count(),0);
  assert.equal(await page.evaluate(()=>Boolean(window.manualInjected)),false);
  await page.screenshot({path:'artifacts/20261014-manual-cli-dev/offline-diagnostic-ui.png',mask:[page.locator('#token')]});
  assert.equal(paths.some(x=>x.includes('/internal/')||x.includes('/approve')||x==='/v1/sessions'),false);
  console.log(JSON.stringify({result:'PASS',scope:'OFFLINE_BROWSER_DOM',diagnostic:'QUOTE_MISMATCH/B',actual_models:0,actual_product_effects:0,raw_html_executed:false}));
} finally {await context.close();}
