import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import https from 'node:https';
import {launch,baseURL,humanToken,runtime,driver,screenshot} from '../../../../tools/browser_helpers.mjs';

const label=process.argv[2], out=path.resolve('artifacts/20261013-browser-b-review',label);
await fs.mkdir(out,{recursive:false});
const build=JSON.parse(await fs.readFile(path.resolve('artifacts/20261013-browser-b-review',label+'-source/summary.json'),'utf8'));
const human=await humanToken(), service=(await fs.readFile(path.join(runtime,'control/service.token'),'utf8')).trim();
const secrets=new Set([human,service]), records=[], requests=[], consoleKinds=[];
const context=await launch('artifacts/profile-browser-b-review');
const page=await context.newPage();
page.setDefaultTimeout(8000);
context.on('request',request=>{const u=new URL(request.url());if(['http:','https:'].includes(u.protocol)) requests.push({origin:u.origin,path:u.pathname,method:request.method(),query:!!u.search});});
page.on('console',message=>consoleKinds.push(message.type()));
page.on('pageerror',()=>consoleKinds.push('pageerror'));
let current=null, notes={};
async function create(kind='POST_COMMENT',issue=42) {
  await page.goto(baseURL);
  await page.locator('#token').fill(human);
  await page.locator('#kind').selectOption(kind);
  await page.locator('#issue').fill(String(issue));
  await page.locator('#request').fill('별도 AI 검토용 가짜 사용자 작업');
  await page.locator('#body').fill('원래 정확 댓글');
  const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/v1/sessions'));
  await page.locator('#create').click();
  const r=await response; assert.equal(r.status(),201);
  const data=await r.json(); secrets.add(data.agent_session_token);
  await page.waitForFunction(id=>document.getElementById('session').value===id,data.session_id);
  current={session_id:data.session_id,agent_token:data.agent_session_token};
  assert.equal(await page.locator('#agent').inputValue(),current.agent_token);
  return current;
}
async function call(tool,args,s=current) {return await driver({command:'tool',...s,tool,args});}
async function state(s=current) {return await driver({command:'state',session_id:s.session_id});}
async function load() {
  await page.locator('#session').fill(current.session_id);
  const response=page.waitForResponse(r=>r.url().endsWith('/timeline'));
  await page.locator('#load').click();
  const r=await response; await page.waitForFunction(()=>!document.getElementById('load').disabled);
  return r.status();
}
async function candidate(body) {
  await create(); const result=await call('post_issue_comment',{issue_id:42,body});
  assert.equal(result.data.decision,'CONFIRM'); assert.equal((await state()).actual_effects,0);
  await load(); assert((await page.locator('#timeline').innerText()).includes(body));
  notes={call_id:result.data.call_id,approval_id:result.data.approval_id};
  return {...notes,body};
}
async function action(name,status) {
  const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes('/v1/approvals/'));
  await page.getByRole('button',{name,exact:true}).click(); const r=await response;
  await page.waitForFunction(value=>document.getElementById('timeline').textContent.includes('"status": "'+value+'"'),status);
  return r.status();
}
async function run(id,fn) {
  current=null;notes={};const started_at=new Date().toISOString();let result='PASS',error=null;
  try {await fn();} catch(e) {result='FAIL';error=e.name+': '+e.message;for(const secret of secrets) error=error.split(secret).join('[credential]');error=error.slice(0,600);}
  const server=current?await state().catch(()=>null):null;
  const evidence={case_id:id,result,error,started_at,completed_at:new Date().toISOString(),source_fingerprint:build.fingerprint,
    mode:'REPLAY',session_id:current?.session_id,...notes,server,ui_status:await page.locator('#status').textContent().catch(()=>null),ui_timeline:await page.locator('#timeline').textContent().catch(()=>null)};
  const serialized=JSON.stringify(evidence); for(const secret of secrets) assert(!serialized.includes(secret),'Credential evidence leak');
  records.push(evidence); await fs.writeFile(path.join(out,'cases.json'),JSON.stringify(records,null,2));
  await screenshot(page,path.join(out,id+'.png'));
  console.log(JSON.stringify({case_id:id,result,error}));
}
try {
  await run('R-B-T01',async()=>{
    const c=await candidate('별도 검토 승인 후보');
    const before=requests.filter(r=>r.path.includes('/approvals/')&&r.method==='POST').length;
    await page.getByRole('button',{name:'이 후보 승인',exact:true}).evaluate(button=>{button.click();button.click();});
    await page.waitForFunction(()=>document.getElementById('timeline').textContent.includes('"status": "APPROVED"'));
    const approved=await state();assert.equal(approved.executor_invocations,0);assert.equal(approved.actual_effects,0);
    assert.equal(requests.filter(r=>r.path.includes('/approvals/')&&r.method==='POST').length-before,1);
    notes.approve_click_effects=approved.actual_effects;notes.approve_http_requests=1;
    const wrong=await call('post_issue_comment',{issue_id:42,body:c.body+' 변형',resume_call_id:c.call_id});
    assert(wrong.is_error);assert.equal((await state()).actual_effects,0);notes.changed_action_effects=0;
    const args={issue_id:42,body:c.body,resume_call_id:c.call_id};
    assert(!(await call('post_issue_comment',args)).is_error);await load();
    const complete=await state();assert.equal(complete.executor_invocations,1);assert.equal(complete.actual_effects,1);
    assert.equal(complete.timeline.data.checks[0].decision,'CONFIRM');assert.equal(complete.timeline.data.approvals[0].status,'CONSUMED');
    for(const text of ['CONFIRM','CONSUMED','SUCCEEDED',c.call_id]) assert((await page.locator('#timeline').innerText()).includes(text));
    assert(!(await call('post_issue_comment',args)).is_error);assert.equal((await state()).actual_effects,1);notes.replay_additional_effects=0;
  });
  await run('R-B-T02',async()=>{
    const c=await candidate('별도 거절 후보');assert.equal(await action('거절','REJECTED'),200);
    assert((await call('post_issue_comment',{issue_id:42,body:c.body,resume_call_id:c.call_id})).is_error);
    assert.equal((await state()).executor_invocations,0);assert.equal((await state()).actual_effects,0);
    assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);
  });
  await run('R-B-T03',async()=>{
    const c=await candidate('별도 만료 후보');await driver({command:'expire_approval',approval_id:c.approval_id});
    assert.equal(await action('이 후보 승인','EXPIRED'),409);
    assert((await call('post_issue_comment',{issue_id:42,body:c.body,resume_call_id:c.call_id})).is_error);
    assert.equal((await state()).actual_effects,0);assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);
  });
  await run('R-B-T04',async()=>{
    await create('SUMMARIZE_ISSUE',43);const read=await call('get_issue',{issue_id:43});assert(!read.is_error);
    const deny=await call('post_issue_comment',{issue_id:43,body:'금지 검토 댓글'}), secret=await call('read_workspace_file',{file_id:'SECRET_ENV'});
    assert.equal(deny.data.decision,'DENY');assert.equal(secret.data.decision,'DENY');await load();
    const text=await page.locator('#timeline').innerText();for(const value of ['DENY','OUTSIDE_TASK_SCOPE','SENSITIVE_RESOURCE','<img','[REDACTED]']) assert(text.includes(value));
    assert(!text.includes('DEMO_SECRET_DO_NOT_SEND'));assert.equal(await page.locator('#timeline img,#timeline script,#timeline iframe').count(),0);
    assert.equal(await page.evaluate(()=>window.__xss),undefined);assert(!requests.some(r=>r.path==='/xss-probe'||r.path==='/xss-canary'));
    assert.equal((await state()).executor_invocations,1);assert.equal((await state()).actual_effects,0);
    assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);notes.denied_executor_invocations=0;
  });
  await run('R-B-T05',async()=>{
    const c=await candidate('별도 stale 버튼 후보');await page.getByRole('button',{name:'이 후보 승인',exact:true}).evaluate(button=>{window.reviewStaleButton=button;});
    const before=requests.length;await page.locator('#session').fill('invalid-session');
    await page.evaluate(()=>window.reviewStaleButton.click());await page.waitForTimeout(100);
    assert.equal(requests.slice(before).filter(r=>r.path.includes('/approvals/')).length,0);notes.stale_handler_http_requests=0;
    await driver({command:'close',session_id:current.session_id});await load();assert((await page.locator('#status').innerText()).includes('CLOSED'));
    assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);assert.equal((await state()).actual_effects,0);
    for(const token of ['invalid-review-user',service,current.agent_token]) {
      await page.locator('#token').fill(token);assert.equal(await load(),401);assert.equal(await page.locator('#timeline').innerText(),'');
    }
    await page.locator('#token').fill(human);assert.equal(await load(),200);notes.role_rejections=[401,401,401];
  });
  await run('R-B-T06',async()=>{
    await create('SUMMARIZE_ISSUE');
    const storage=await page.evaluate(async()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage),cookie:document.cookie,cache:await caches.keys(),workers:(await navigator.serviceWorker.getRegistrations()).length}));
    assert.deepEqual(storage,{local:[],session:[],cookie:'',cache:[],workers:0});notes.storage=storage;
    const foreign=await context.newPage();await foreign.goto('about:blank');
    const blocked=await foreign.evaluate(async url=>{try {await fetch(url+'/v1/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});return false;}catch{return true;}},baseURL);
    assert(blocked);await foreign.close();notes.foreign_origin_browser_blocked=true;
    // Node request context has its own CA store; use the explicit fixture CA,
    // preserving TLS verification. This direct server probe supplements the
    // actual about:blank browser preflight above.
    const ca=await fs.readFile(path.join(runtime,'ca.pem'));
    const directStatus=await new Promise((resolve,reject)=>{
      const request=https.get(baseURL+'/v1/sessions/'+current.session_id+'/timeline',{ca,rejectUnauthorized:true,
        headers:{Origin:'https://untrusted.invalid',Authorization:'Bearer '+human}},response=>{response.resume();resolve(response.statusCode);});
      request.on('error',()=>reject(new Error('VERIFIED_ORIGIN_PROBE_FAILED')));
    });
    assert.equal(directStatus,403);notes.foreign_origin_authenticated_status=403;notes.direct_probe_tls='Explicit fixture CA, rejectUnauthorized true';
    await page.reload();assert.equal(await page.locator('#token').inputValue(),'');assert.equal(await page.locator('#agent').inputValue(),'');
    await page.locator('#token').fill(human);await page.locator('#agent').evaluate((el,token)=>{el.value=token;},current.agent_token);
    await page.goto('about:blank');await page.goBack();assert.equal(await page.locator('#token').inputValue(),'');assert.equal(await page.locator('#agent').inputValue(),'');
    notes.reload_and_navigation_credentials_empty=true;assert.equal((await state()).actual_effects,0);
  });
  await run('R-B-T07',async()=>{
    await create('SUMMARIZE_ISSUE');const statuses=[];
    for(let n=0;n<32;n++){const status=await page.evaluate(async sid=>(await fetch('/v1/sessions/'+sid+'/timeline',{headers:{Authorization:'Bearer invalid-review-auth'}})).status,current.session_id);statuses.push(status);if(status===429)break;}
    assert(statuses.includes(429));assert.equal(await load(),200);await page.waitForTimeout(10500);
    const recovery=await page.evaluate(async sid=>(await fetch('/v1/sessions/'+sid+'/timeline',{headers:{Authorization:'Bearer invalid-review-auth'}})).status,current.session_id);
    assert.equal(recovery,401);notes.statuses=statuses;notes.normal_status=200;notes.after_10500ms_invalid_status=recovery;assert.equal((await state()).actual_effects,0);
  });
} finally {
  await fs.writeFile(path.join(out,'metadata.json'),JSON.stringify({browser:context.browser().version(),baseURL,ignoreHTTPSErrors:false,profile:'artifacts/profile-browser-b-review',source_fingerprint:build.fingerprint,requests,consoleKinds},null,2));
  await context.close();
}
process.exitCode=records.some(r=>r.result==='FAIL')?1:0;
