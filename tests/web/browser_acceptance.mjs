import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {launch,baseURL,humanToken,runtime,driver,screenshot} from '../../tools/browser_helpers.mjs';

const label=process.argv[2];
const root=path.resolve(process.env.WITH_HUMAN_BROWSER_EVIDENCE_ROOT??'artifacts/20261013-browser-b');
const out=path.join(root,label);
await fs.mkdir(out,{recursive:false});
const build=JSON.parse(await fs.readFile(path.join(root,label+'-source/summary.json'),'utf8'));
const human=await humanToken();
const service=(await fs.readFile(path.join(runtime,'control/service.token'),'utf8')).trim();
const secrets=new Set([human,service]);
const records=[];
const context=await launch('artifacts/profile-browser-b-firefox');
const page=await context.newPage();
page.setDefaultTimeout(7000);
let current=null;
const network=[];
context.on('request',r=>{const u=new URL(r.url()); if(u.protocol==='https:'||u.protocol==='http:')
  network.push({origin:u.origin,path:u.pathname,method:r.method(),query_present:!!u.search});});
const consoleEvents=[];
page.on('console',m=>consoleEvents.push({type:m.type(),text:safe(m.text())}));
page.on('pageerror',e=>consoleEvents.push({type:'pageerror',text:safe(e.message)}));
function safe(text) { for(const value of secrets) text=String(text).split(value).join('[credential]'); return String(text).slice(0,1000); }
async function create(task='POST_COMMENT',issue=42,request='실제 브라우저 작업 요청',body='검토 완료') {
  await page.goto(baseURL);
  await page.locator('#token').fill(human);
  await page.locator('#kind').selectOption(task);
  await page.locator('#issue').fill(String(issue));
  await page.locator('#request').fill(request);
  await page.locator('#body').fill(body);
  const pending=page.waitForResponse(r=>r.url().endsWith('/v1/sessions')&&r.request().method()==='POST');
  await page.locator('#create').click();
  const response=await pending;
  assert.equal(response.status(),201);
  const data=await response.json();
  await page.waitForFunction(sid=>document.getElementById('session').value===sid,data.session_id);
  current={session_id:data.session_id,agent_token:await page.locator('#agent').inputValue()};
  secrets.add(current.agent_token);
  assert.equal(current.agent_token,data.agent_session_token);
  return current;
}
async function tool(name,args,session=current) {return await driver({command:'tool',...session,tool:name,args});}
async function state(session=current) {return await driver({command:'state',session_id:session.session_id});}
async function load(session=current) {
  await page.locator('#session').fill(session.session_id);
  const pending=page.waitForResponse(r=>r.url().endsWith('/timeline'));
  await page.locator('#load').click();
  const response=await pending;
  await page.waitForFunction(()=>!document.getElementById('load').disabled);
  return response.status();
}
async function candidate(body='승인할 정확한 다른 댓글') {
  await create();
  const result=await tool('post_issue_comment',{issue_id:42,body});
  assert.equal(result.data.decision,'CONFIRM');
  assert.equal((await state()).actual_effects,0);
  await load();
  return {body,call_id:result.data.call_id,approval_id:result.data.approval_id};
}
async function action(name) {
  const pending=page.waitForResponse(r=>r.url().includes('/v1/approvals/')&&r.request().method()==='POST');
  await page.getByRole('button',{name:name==='approve'?'이 후보 승인':'거절',exact:true}).click();
  const response=await pending;
  const result=await response.json();
  if(response.status()===200) await page.waitForFunction(status=>document.getElementById('timeline').textContent.includes('"status": "'+status+'"'),result.status);
  else if(result.code==='APPROVAL_EXPIRED') await page.waitForFunction(()=>document.getElementById('timeline').textContent.includes('"status": "EXPIRED"'));
  return response.status();
}
async function run(caseId,fn) {
  current=null;
  const started=Date.now();
  let result='PASS',error=null;
  try {await fn();} catch(e) {result='FAIL';error=safe(e.message);}
  let evidence=null;
  if(current) {const s=await state().catch(()=>null); if(s) {
    evidence={session_id:current.session_id,server:s,ui_status:await page.locator('#status').innerText(),
              ui_timeline:await page.locator('#timeline').innerText()};
    for(const secret of secrets) assert(!JSON.stringify(evidence).includes(secret));
  }}
  await screenshot(page,path.join(out,caseId+'.png'));
  const record={case_id:caseId,result,error,elapsed_ms:Date.now()-started,source_fingerprint:build.fingerprint,
                browser:context.browser().version(),mode:'REPLAY',evidence};
  records.push(record);
  await fs.writeFile(path.join(out,'cases.json'),JSON.stringify(records,null,2));
  console.log(JSON.stringify({case_id:caseId,result,error,elapsed_ms:record.elapsed_ms}));
}
try {
  await run('B-01',async()=>{
    await create('SUMMARIZE_ISSUE');
    assert(!(await tool('get_issue',{issue_id:42})).is_error);
    assert(!(await tool('read_workspace_file',{file_id:'PUBLIC_README'})).is_error);
    await load(); assert((await page.locator('#timeline').innerText()).includes('SUCCEEDED'));
    const reads=await state(); assert.equal(reads.executor_invocations,2); assert.equal(reads.actual_effects,0);
    await create(); const result=await tool('post_issue_comment',{issue_id:42,body:'검토 완료'});
    assert(!result.is_error); await load();
    assert.equal((await state()).actual_effects,1);
    assert((await page.locator('#timeline').innerText()).includes(result.data.call_id));
  });
  await run('B-02',async()=>{
    const c=await candidate();
    assert((await page.locator('#timeline').innerText()).includes(c.body));
    assert.equal(await action('approve'),200);
    const approved=await state(); assert.equal(approved.actual_effects,0);
    assert.equal(approved.timeline.data.approvals[0].status,'APPROVED');
    assert((await page.locator('#timeline').innerText()).includes('APPROVED'),'UI did not reflect successful approval');
    const args={issue_id:42,body:c.body,resume_call_id:c.call_id};
    assert(!(await tool('post_issue_comment',args)).is_error);
    await load(); const completed=await state(); assert.equal(completed.actual_effects,1);
    const text=await page.locator('#timeline').innerText();
    for(const value of ['CONFIRM','CONSUMED','SUCCEEDED']) assert(text.includes(value));
    assert(!(await tool('post_issue_comment',args)).is_error);
    await load(); assert.equal((await state()).actual_effects,1);
  });
  await run('B-03',async()=>{
    let c=await candidate('거절할 댓글');
    assert.equal(await action('reject'),200);
    assert((await page.locator('#timeline').innerText()).includes('REJECTED'),'UI did not reflect rejection');
    assert((await tool('post_issue_comment',{issue_id:42,body:c.body,resume_call_id:c.call_id})).is_error);
    assert.equal((await state()).actual_effects,0);
    c=await candidate('기한이 지난 후보');
    await driver({command:'expire_approval',approval_id:c.approval_id});
    assert.equal(await action('approve'),409);
    assert((await page.locator('#timeline').innerText()).includes('EXPIRED'));
    assert.equal((await state()).actual_effects,0);
    c=await candidate('중복 클릭 후보');
    await page.getByRole('button',{name:'이 후보 승인',exact:true}).evaluate(b=>{b.click();b.click();});
    await page.waitForFunction(()=>document.getElementById('status').textContent.includes('승인'));
    const s=await state(); assert.equal(s.timeline.data.approvals[0].status,'APPROVED'); assert.equal(s.actual_effects,0);
    assert.equal(await page.getByRole('button',{name:'거절',exact:true}).count(),0);
    const changed=await tool('post_issue_comment',{issue_id:42,body:c.body+' 변경',resume_call_id:c.call_id});
    assert(changed.is_error); assert.equal((await state()).actual_effects,0);
    assert(!(await tool('post_issue_comment',{issue_id:42,body:c.body,resume_call_id:c.call_id})).is_error);
    assert.equal((await state()).actual_effects,1);
  });
  await run('B-04',async()=>{
    await create('SUMMARIZE_ISSUE');
    const denied=await tool('post_issue_comment',{issue_id:42,body:'금지 댓글'});
    const secret=await tool('read_workspace_file',{file_id:'SECRET_ENV'});
    assert.equal(denied.data.decision,'DENY'); assert.equal(secret.data.decision,'DENY');
    await load(); const text=await page.locator('#timeline').innerText();
    for(const v of ['자동 차단','사용자의 작업 권한 밖 행동입니다.','민감한 자료는 읽을 수 없습니다.']) assert(text.includes(v));
    assert(denied.data.reason_codes.includes('OUTSIDE_TASK_SCOPE'));assert(secret.data.reason_codes.includes('SENSITIVE_RESOURCE'));
    assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);
    const s=await state(); assert.equal(s.executor_invocations,0); assert.equal(s.actual_effects,0);
  });
  await run('B-05',async()=>{
    const before=network.length;
    await create('SUMMARIZE_ISSUE',43,'브라우저 XSS · DEMO_SECRET_DO_NOT_SEND');
    const read=await tool('get_issue',{issue_id:43}); assert(!read.is_error);
    await load(); const text=await page.locator('#timeline').innerText();
    assert(text.includes('<img')); assert(text.includes('[REDACTED]')); assert(!text.includes('DEMO_SECRET_DO_NOT_SEND'));
    assert.equal(await page.locator('#timeline img,#timeline script,#timeline iframe').count(),0);
    assert.equal(await page.evaluate(()=>window.__xss),undefined);
    assert(!network.slice(before).some(r=>r.path==='/xss-probe'||r.path==='/xss-canary'));
    const s=await state(); assert(s.timeline.data.sources.every(r=>r.masked_excerpt.length<=512)); assert.equal(s.actual_effects,0);
    for(const secret of secrets) assert(!text.includes(secret));
    assert(!consoleEvents.some(e=>e.text.includes('DEMO_SECRET_DO_NOT_SEND')||e.text.includes('Traceback')));
    await driver({command:'fail_session_create',enabled:true});
    try {
      const pending=page.waitForResponse(r=>r.url().endsWith('/v1/sessions')&&r.request().method()==='POST');
      await page.locator('#create').click(); assert.equal((await pending).status(),503);
      await page.waitForFunction(()=>document.getElementById('status').textContent.includes('AUDIT_UNAVAILABLE'));
      const error=await page.locator('#status').innerText();
      assert(!error.includes('private-error-canary')&&!error.includes('DEMO_SECRET_DO_NOT_SEND')&&!error.includes('Traceback'));
      assert.equal(await page.locator('#timeline').innerText(),''); assert.equal(await page.locator('#agent').inputValue(),'');
    } finally {await driver({command:'fail_session_create',enabled:false});}
  });
  await run('B-06',async()=>{
    const c=await candidate('닫힌 세션 후보'); const old=current;
    await driver({command:'close',session_id:old.session_id});
    await load(); assert((await page.locator('#status').innerText()).includes('CLOSED'));
    const denied=await page.evaluate(async aid=>{
      const r=await fetch('/v1/approvals/'+aid+'/approve',{method:'POST',headers:{'Authorization':'Bearer '+document.getElementById('token').value,'Content-Type':'application/json'},body:JSON.stringify({expected_args_sha256:'0'.repeat(64)})});return r.status;
    },c.approval_id); assert.equal(denied,403);
    assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);
    await create('SUMMARIZE_ISSUE'); await tool('get_issue',{issue_id:42}); await load();
    await page.locator('#token').fill('wrong-browser-token');
    assert.equal(await load(),401);
    assert.equal(await page.locator('#timeline').innerText(),'','A failed lookup left old successful data visible');
    for(const token of [service,current.agent_token]) {
      await page.locator('#token').fill(token); assert.equal(await load(),401);
      assert.equal(await page.locator('#timeline').innerText(),'');
    }
    await page.locator('#token').fill(human);
    await driver({command:'expire_session',session_id:current.session_id}); await load();
    assert((await page.locator('#status').innerText()).includes('EXPIRED'));
    await driver({command:'expire_retention',session_id:current.session_id});
    assert([403,404].includes(await load())); assert.equal(await page.locator('#timeline').innerText(),'');
    await page.locator('#session').fill('not-a-session'); await page.locator('#load').click();
    assert.equal(await page.locator('#timeline').innerText(),'');
  });
  await run('B-07',async()=>{
    await create('SUMMARIZE_ISSUE'); const issued=current;
    const storage=await page.evaluate(async()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage),cookies:document.cookie,
      caches:await caches.keys(),workers:(await navigator.serviceWorker.getRegistrations()).length}));
    assert.deepEqual(storage,{local:[],session:[],cookies:'',caches:[],workers:0});
    assert(!page.url().includes(human)&&!page.url().includes(issued.agent_token));
    await page.reload();
    assert.equal(await page.locator('#token').inputValue(),''); assert.equal(await page.locator('#agent').inputValue(),'');
    await create('SUMMARIZE_ISSUE');
    await page.goto('about:blank'); await page.goBack();
    assert.equal(await page.locator('#token').inputValue(),''); assert.equal(await page.locator('#agent').inputValue(),'');
    const foreign=await context.newPage(); await foreign.goto(baseURL.replace('127.0.0.1','localhost'));
    const cross=await foreign.evaluate(async base=>{try {await fetch(base+'/v1/sessions',{method:'POST',headers:{Authorization:'Bearer wrong', 'Content-Type':'application/json'},body:'{}'});return 'unexpected-success';}catch{return 'browser-blocked';}},baseURL);
    assert.equal(cross,'browser-blocked'); await foreign.close(); assert.equal((await state(issued)).actual_effects,0);
  });
  await run('B-08',async()=>{
    await create('SUMMARIZE_ISSUE'); const sid=current.session_id;
    const codes=[];
    for(let i=0;i<32;i++) {const code=await page.evaluate(async s=>{const r=await fetch('/v1/sessions/'+s+'/timeline',{headers:{Authorization:'Bearer invalid-browser-auth'}});return r.status;},sid); codes.push(code); if(code===429) break;}
    assert(codes.includes(429),'Bounded invalid-auth probe did not observe throttling');
    const normal=await page.evaluate(async s=>{const r=await fetch('/v1/sessions/'+s+'/timeline',{headers:{Authorization:'Bearer '+document.getElementById('token').value}});return r.status;},sid);
    assert.equal(normal,200); await new Promise(r=>setTimeout(r,10500));
    const recovered=await page.evaluate(async s=>{const r=await fetch('/v1/sessions/'+s+'/timeline',{headers:{Authorization:'Bearer invalid-browser-auth'}});return r.status;},sid);
    assert.equal(recovered,401); assert.equal((await state()).actual_effects,0);
    records.push({case_id:'B-08-observation',statuses:codes,normal_status:normal,after_wait_status:recovered,wait_ms:10500});
  });
} finally {
  await fs.writeFile(path.join(out,'browser-metadata.json'),JSON.stringify({browser:context.browser().version(),baseURL,
    source_fingerprint:build.fingerprint,ignoreHTTPSErrors:false,ca_trust:'Dedicated profile NSS C,,',network,console:consoleEvents},null,2));
  await context.close();
}
process.exitCode=records.some(r=>r.result==='FAIL')?1:0;
