import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {semanticOutcomeMatches} from './f3_outcome.mjs';
const require=createRequire(import.meta.url);
const {firefox}=require('C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const executable=path.resolve('artifacts/browser-tools-b/firefox-1538/firefox/firefox.exe');
const base='https://127.0.0.1:8020';
const normalRuntime=path.resolve('artifacts/runtime-f3-01');
const label=process.argv[2]??'real-browser-first';
const out=path.resolve('artifacts/20261014-f3-01',label);
await fs.mkdir(out,{recursive:true});
const fingerprint=JSON.parse(await fs.readFile(path.resolve(out+'-source/summary.json'),'utf8')).fingerprint;
const credentials=new Set([(await fs.readFile(path.join(normalRuntime,'control/human.token'),'utf8')).trim()]);
export async function driver(value) {
  return await new Promise((resolve,reject)=>{
    const child=spawn('docker',['compose','-f','compose.f3.yaml','run','--rm','-T','--no-deps','driver','python','tools/f3_driver.py'],{windowsHide:true});
    let output='';child.stdout.on('data',x=>output+=x.toString('utf8'));child.stderr.on('data',()=>{});
    child.on('error',()=>reject(new Error('DRIVER_UNAVAILABLE')));
    child.on('close',code=>{try{const result=JSON.parse(output.trim());if(code||result.driver_error)throw new Error();resolve(result);}catch{reject(new Error('SAFE_DRIVER_FAILURE'));}});
    child.stdin.end(JSON.stringify(value));
  });
}
function safe(value) {
  let text=JSON.stringify(value);
  for(const credential of credentials)if(text.includes(credential))throw new Error('CREDENTIAL_COLLECTION_BLOCKED');
  return value;
}
const browserEnv={};
for(const key of ['PATH','SystemRoot','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA'])if(process.env[key])browserEnv[key]=process.env[key];
const context=await firefox.launchPersistentContext(path.resolve('artifacts/profile-f3-01'),{
  executablePath:executable,headless:!process.argv.includes('--headed'),ignoreHTTPSErrors:false,env:browserEnv,
  viewport:{width:1280,height:1000},firefoxUserPrefs:{'security.enterprise_roots.enabled':false,
    'browser.formfill.enable':false,'signon.rememberSignons':false,'browser.sessionstore.resume_from_crash':false}});
const page=await context.newPage();
const records=[];
const fixtures=JSON.parse(await fs.readFile('fixtures/f3/cases.json','utf8'));
const selected=process.argv.includes('--first-only')?fixtures.cases.slice(0,1):fixtures.cases;
try {
  for(const fixture of selected) {
    const started=Date.now();let record;
    try {
      await driver({command:'fixture',issue:fixture.issue});
      await page.goto(base);
      await page.locator('#token').fill([...credentials][0]);
      await page.locator('#kind').selectOption('POST_COMMENT');
      await page.locator('#mode').selectOption('ISSUE_SUMMARY');
      await page.locator('#request').fill(fixtures.request);
      const created=page.waitForResponse(r=>r.url().endsWith('/v1/sessions')&&r.request().method()==='POST');
      await page.locator('#create').click();assert.equal((await created).status(),201);
      await page.waitForFunction(()=>document.getElementById('agent').value.length>0);
      const session={session_id:await page.locator('#session').inputValue(),agent_token:await page.locator('#agent').inputValue()};
      credentials.add(session.agent_token);
      const read=await driver({command:'tool',...session,tool:'get_issue',args:{issue_id:42}});
      assert.equal(read.data.execution_state,'SUCCEEDED');
      const result=await driver({command:'tool',...session,tool:'post_issue_comment',args:{issue_id:42,body:fixture.candidate}});
      const state=await driver({command:'state',session_id:session.session_id});
      const loaded=page.waitForResponse(r=>r.url().endsWith('/timeline'));
      await page.locator('#load').click();await loaded;
      await page.waitForFunction(()=>!document.getElementById('load').disabled);
      await page.screenshot({path:path.join(out,fixture.id+'.png'),fullPage:true,
        mask:[page.locator('input[type=password]'),page.locator('#request,#body')]});
      record=safe({case_id:fixture.id,mode:'REAL_JUDGE_REPLAY_BROWSER',source_fingerprint:fingerprint,
        session_id:session.session_id,user_request:fixtures.request,comment_mode:'ISSUE_SUMMARY',
        candidate:fixture.candidate,expected_decision:fixture.expected,actual:result,
        server:state,ui:await page.locator('#timeline').textContent(),approval_clicks:0,elapsed_ms:Date.now()-started});
      assert.equal(result.data.decision,fixture.expected);
      assert.equal(state.actual_effects,fixture.expected==='ALLOW'?1:0);
      assert.equal(result.data.decision_stage,'SEMANTIC');
      assert.equal(semanticOutcomeMatches(fixture,result.data,state.actual_effects),true);
      if(fixture.expected!=='CONFIRM')assert.equal(result.data.approval_id,null);
      if(fixture.expected==='ALLOW')assert.equal(result.data.execution_state,'SUCCEEDED');
      record.result='PASS';
    } catch {record={...record,case_id:fixture.id,result:'FAIL',error:'SAFE_CASE_FAILURE',elapsed_ms:Date.now()-started};process.exitCode=1;}
    records.push(record);
    await fs.writeFile(path.join(out,'cases.json'),JSON.stringify(safe(records),null,2));
    console.log(JSON.stringify({case_id:fixture.id,result:record.result,actual_decision:record.actual?.data?.decision,
      reasons:record.actual?.data?.reason_codes,actual_effects:record.server?.actual_effects,elapsed_ms:record.elapsed_ms}));
  }
  await fs.writeFile(path.join(out,'usage.json'),JSON.stringify(await driver({command:'usage'}),null,2));
  await fs.writeFile(path.join(out,'browser.json'),JSON.stringify({version:context.browser().version(),ignoreHTTPSErrors:false,
    profile:'artifacts/profile-f3-01',baseURL:base,approval_clicks:0,source_fingerprint:fingerprint,credential_environment_allowlist:true},null,2));
} finally {await context.close();}
