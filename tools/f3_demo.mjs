// Display already-observed automatic decisions. No new judge/actor/tool calls.
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline/promises';
import {stdin,stdout} from 'node:process';
import {launch,baseURL,humanToken} from './browser_helpers.mjs';
const root=path.resolve('artifacts/20261014-f3-01');
const labels=(await fs.readdir(root,{withFileTypes:true})).filter(x=>x.isDirectory()&&/^manual-real-\d{8}T\d{6}Z$/.test(x.name)).map(x=>x.name).sort();
if(!labels.length)throw new Error('먼저 scripts/f3_verify.ps1로 실제 모델 검증을 실행하세요.');
const label=process.argv[2]??labels.at(-1);
if(!labels.includes(label))throw new Error('해당 안전한 모델 증거 라벨이 없습니다.');
const cases=JSON.parse(await fs.readFile(path.join(root,label,'cases.json'),'utf8'));
const selected=['normal','external-data','paired-attack'].map(id=>cases.find(x=>x.case_id===id));
if(selected.some(x=>!x?.session_id))throw new Error('자동 정상/외부데이터/차단 세션 증거가 아직 없습니다.');
const context=await launch('artifacts/profile-f3-demo',false);
const cli=readline.createInterface({input:stdin,output:stdout});
try {
  for(const record of selected) {
    const page=await context.newPage();await page.goto(baseURL);
    await page.locator('#token').fill(await humanToken());
    await page.locator('#session').fill(record.session_id);
    const loaded=page.waitForResponse(r=>r.url().endsWith('/timeline'));
    await page.locator('#load').click();await loaded;
    await page.waitForFunction(()=>!document.getElementById('load').disabled);
    console.log(JSON.stringify({case_id:record.case_id,recorded_result:record.result,decision:record.actual?.data?.decision,
      actual_effects:record.server?.actual_effects,new_model_requests:0}));
  }
  console.log('세 탭에서 실제 자동판정·관련 출처·효과를 확인하세요. 승인 클릭은 필요 없습니다. 현재 서버 이력을 재조회했으며 유료 요청을 추가하지 않았습니다.');
  await cli.question('확인 후 Enter로 전용 브라우저를 닫습니다. ');
} finally {cli.close();await context.close();}
