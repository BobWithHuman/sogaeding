import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline/promises';
import {stdin,stdout} from 'node:process';
import {launch,baseURL,humanToken,driver} from './browser_helpers.mjs';

const smoke=process.argv.includes('--smoke');
const normal=process.argv.includes('--normal');
const option=name=>process.argv.includes(name)?process.argv[process.argv.indexOf(name)+1]:undefined;
const profile=option('--profile')??'artifacts/profile-browser-b-firefox';
const context=await launch(profile,smoke);
const page=await context.newPage();
const cli=smoke?null:readline.createInterface({input:stdin,output:stdout});
try {
  await page.goto(baseURL);
  await page.locator('#token').fill(await humanToken());
  await page.locator('#kind').selectOption('POST_COMMENT');
  await page.locator('#request').fill('브라우저 승인 시연 요청');
  await page.locator('#body').fill('검토 완료');
  console.log('로컬 URL: '+baseURL+' · 전용 Firefox 프로필 · 사용자 토큰은 메모리에만 준비했습니다.');
  if(!smoke) await cli.question('화면에서 [세션 만들기]를 클릭한 뒤 Enter를 누르세요. ');
  else {
    const reply=page.waitForResponse(r=>r.url().endsWith('/v1/sessions')&&r.request().method()==='POST');
    await page.locator('#create').click(); assert.equal((await reply).status(),201);
    await page.waitForFunction(()=>document.getElementById('agent').value.length>0);
  }
  const session={session_id:await page.locator('#session').inputValue(),agent_token:await page.locator('#agent').inputValue()};
  if(!session.agent_token||!session.session_id) throw new Error('먼저 새 댓글 세션을 만들어 주세요.');
  const allowed=await page.locator('#body').inputValue();
  if(normal) {
    const result=await driver({command:'tool',...session,tool:'post_issue_comment',args:{issue_id:42,body:allowed}});
    assert.equal(result.data.decision,'ALLOW'); assert.equal(result.data.execution_state,'SUCCEEDED');
    const refreshed=page.waitForResponse(r=>r.url().endsWith('/timeline'));
    await page.locator('#load').click(); await refreshed;
    await page.waitForFunction(()=>document.getElementById('timeline').textContent.includes('SUCCEEDED'));
    const state=await driver({command:'state',session_id:session.session_id});
    assert.equal(state.actual_effects,1); assert.equal(state.executor_invocations,1);
    const safe={mode:'REPLAY',session_id:session.session_id,call_id:result.data.call_id,
      decision:'ALLOW',execution_state:'SUCCEEDED',executor_invocations:state.executor_invocations,actual_effects:state.actual_effects};
    console.log(JSON.stringify(safe));
    if(smoke) await fs.writeFile(path.resolve(option('--output')??'artifacts/20261013-browser-b/demo-normal-smoke.json'),JSON.stringify(safe,null,2),{flag:'wx'});
    else await cli.question('정확한 댓글1개·ALLOW/SUCCEEDED 화면을 확인한 뒤 Enter로 종료합니다. ');
  } else {
  const body=allowed==='승인 시연용 별도 댓글'?'다른 승인 시연 댓글':'승인 시연용 별도 댓글';
  const pending=await driver({command:'tool',...session,tool:'post_issue_comment',args:{issue_id:42,body}});
  assert.equal(pending.data.decision,'CONFIRM');
  const first=await driver({command:'state',session_id:session.session_id});
  assert.equal(first.actual_effects,0);
  const load=page.waitForResponse(r=>r.url().endsWith('/timeline'));
  await page.locator('#load').click(); await load;
  await page.getByRole('button',{name:'이 후보 승인',exact:true}).waitFor();
  console.log('다른 본문 후보가 CONFIRM입니다. 현재 실제 댓글0. 화면에서 본문·call ID를 확인하고 승인하세요.');
  if(!smoke) await cli.question('승인 또는 거절한 뒤 Enter를 누르면 같은 MCP 호출을 재개합니다. ');
  else {
    const approval=page.waitForResponse(r=>r.url().endsWith('/approve'));
    await page.getByRole('button',{name:'이 후보 승인',exact:true}).click(); assert.equal((await approval).status(),200);
    await page.waitForFunction(()=>document.getElementById('timeline').textContent.includes('APPROVED'));
  }
  const before=await driver({command:'state',session_id:session.session_id}); assert.equal(before.actual_effects,0);
  const result=await driver({command:'tool',...session,tool:'post_issue_comment',
    args:{issue_id:42,body,resume_call_id:pending.data.call_id}});
  const refreshed=page.waitForResponse(r=>r.url().endsWith('/timeline'));
  await page.locator('#load').click(); await refreshed;
  await page.waitForFunction(()=>!document.getElementById('load').disabled);
  const state=await driver({command:'state',session_id:session.session_id});
  console.log(JSON.stringify({session_id:session.session_id,call_id:pending.data.call_id,
    decision:result.data.decision,execution_state:result.data.execution_state,
    executor_invocations:state.executor_invocations,actual_effects:state.actual_effects}));
  if(smoke) {
    assert.equal(result.data.execution_state,'SUCCEEDED'); assert.equal(state.actual_effects,1);
    assert.equal(state.timeline.data.approvals[0].status,'CONSUMED');
    const output=path.resolve(option('--output')??'artifacts/20261013-browser-b/demo-smoke.json');
    await fs.writeFile(output,JSON.stringify({
      mode:'REPLAY',session_id:session.session_id,call_id:pending.data.call_id,
      before_approval_effects:first.actual_effects,after_approval_effects:before.actual_effects,
      executor_invocations:state.executor_invocations,after_resume_effects:state.actual_effects,
      decision:result.data.decision,approval:'CONSUMED',execution:'SUCCEEDED'},null,2),{flag:'wx'});
  } else await cli.question('화면 확인을 마치면 Enter로 전용 브라우저를 닫습니다. ');
  }
} catch {
  console.error('시연을 완료하지 못했습니다. 새 댓글 세션·승인 상태·로컬 서비스 연결을 확인해 주세요. 자격증명은 출력하지 않았습니다.');
  process.exitCode=1;
} finally {cli?.close();await context.close();}
