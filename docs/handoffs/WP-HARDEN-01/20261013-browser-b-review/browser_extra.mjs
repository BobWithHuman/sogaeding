import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {launch,baseURL,humanToken,runtime,driver,screenshot} from '../../../../tools/browser_helpers.mjs';
const label=process.argv[2], out=path.resolve('artifacts/20261013-browser-b-review',label);
await fs.mkdir(out,{recursive:false});
const build=JSON.parse(await fs.readFile(path.resolve('artifacts/20261013-browser-b-review',label+'-source/summary.json'),'utf8'));
const human=await humanToken(), service=(await fs.readFile(path.join(runtime,'control/service.token'),'utf8')).trim();
const secrets=new Set([human,service]), records=[];
const context=await launch('artifacts/profile-browser-b-review'), page=await context.newPage();page.setDefaultTimeout(7000);
async function create() {
  await page.goto(baseURL);await page.locator('#token').fill(human);await page.locator('#kind').selectOption('POST_COMMENT');
  await page.locator('#request').fill('별도 역할 경계 검토');await page.locator('#body').fill('정확 댓글');
  const response=page.waitForResponse(r=>r.url().endsWith('/v1/sessions')&&r.request().method()==='POST');
  await page.locator('#create').click();const r=await response;assert.equal(r.status(),201);const data=await r.json();secrets.add(data.agent_session_token);
  await page.waitForFunction(id=>document.getElementById('session').value===id,data.session_id);
  return {session_id:data.session_id,agent_token:data.agent_session_token};
}
async function load(s) {
  await page.locator('#session').fill(s.session_id);const response=page.waitForResponse(r=>r.url().endsWith('/timeline'));
  await page.locator('#load').click();const r=await response;await page.waitForFunction(()=>!document.getElementById('load').disabled);return r.status();
}
async function state(s){return await driver({command:'state',session_id:s.session_id});}
try {
  for(const kind of ['close','expire_session','roles']) {
    const started_at=new Date().toISOString(), s=await create();let result='PASS',error=null,observations={};
    try {
      const candidate=await driver({command:'tool',...s,tool:'post_issue_comment',args:{issue_id:42,body:'검토 후보'}});
      assert.equal(candidate.data.decision,'CONFIRM');await load(s);
      const id=candidate.data.approval_id, args={issue_id:42,body:'검토 후보',resume_call_id:candidate.data.call_id};
      if(kind==='roles') {
        const statuses=[];
        for(const token of [s.agent_token,service]) {
          const codes=await page.evaluate(async ({token,id})=>{
            const headers={Authorization:'Bearer '+token,'Content-Type':'application/json'};
            const create=await fetch('/v1/sessions',{method:'POST',headers,body:JSON.stringify({task_kind:'SUMMARIZE_ISSUE',user_request:'가짜 경계 요청',issue_id:42})});
            const approve=await fetch('/v1/approvals/'+id+'/approve',{method:'POST',headers,body:JSON.stringify({expected_args_sha256:'0'.repeat(64)})});
            const reject=await fetch('/v1/approvals/'+id+'/reject',{method:'POST',headers,body:'{}'});
            return [create.status,approve.status,reject.status];
          },{token,id});assert.deepEqual(codes,[401,401,401]);statuses.push(codes);
        }
        observations.role_create_approve_reject_statuses=statuses;assert.equal((await state(s)).timeline.data.approvals[0].status,'PENDING');
      } else {
        await driver({command:kind,session_id:s.session_id});assert.equal(await load(s),200);
        const expected=kind==='close'?'CLOSED':'EXPIRED';assert((await page.locator('#status').innerText()).includes(expected));
        assert.equal(await page.getByRole('button',{name:'이 후보 승인',exact:true}).count(),0);
        let blocked=false;try {const tool=await driver({command:'tool',...s,tool:'post_issue_comment',args});blocked=tool.is_error;}catch(e){blocked=e.message==='SAFE_DRIVER_FAILURE';}
        assert(blocked);observations.mcp_inactive_token_blocked=true;
        const approve=await page.evaluate(async id=>(await fetch('/v1/approvals/'+id+'/approve',{method:'POST',headers:{Authorization:'Bearer '+document.getElementById('token').value,'Content-Type':'application/json'},body:JSON.stringify({expected_args_sha256:'0'.repeat(64)})})).status,id);
        assert.equal(approve,403);observations.inactive_approve_status=approve;
      }
      const effect=await state(s);assert.equal(effect.executor_invocations,0);assert.equal(effect.actual_effects,0);
      observations.call_id=candidate.data.call_id;observations.approval_id=id;
    } catch(e){result='FAIL';error=e.name+': '+e.message;for(const secret of secrets)error=error.split(secret).join('[credential]');}
    const record={case_id:'R-B-X-'+kind,result,error,started_at,completed_at:new Date().toISOString(),source_fingerprint:build.fingerprint,
      mode:'REPLAY',session_id:s.session_id,observations,server:await state(s),ui_status:await page.locator('#status').innerText(),ui_timeline:await page.locator('#timeline').innerText()};
    for(const secret of secrets)assert(!JSON.stringify(record).includes(secret));records.push(record);
    await fs.writeFile(path.join(out,'cases.json'),JSON.stringify(records,null,2));await screenshot(page,path.join(out,record.case_id+'.png'));
    console.log(JSON.stringify({case_id:record.case_id,result,error}));
  }
} finally {await context.close();}
process.exitCode=records.some(r=>r.result==='FAIL')?1:0;
