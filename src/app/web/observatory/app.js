'use strict';
// Adapted from BobWithHuman/sogaeding_dashboard @ 2f6bbb33b289fbd57ec950261e541a72b03b0df0.
// Live engine view only: no simulated decisions, counters or approval actions.

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? '—').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const formatNumber = (value) => value == null ? '—' : Number(value).toLocaleString('ko-KR');
const formatTime = (value, includeDate = true) => value ? new Date(value).toLocaleString('ko-KR', {timeZone:'Asia/Seoul', ...(includeDate ? {} : {hour:'2-digit', minute:'2-digit'})}) : '—';
const decisionBadge = (value) => `<span class="badge ${['ALLOW','DENY','ASK'].includes(value) ? value : 'UNKNOWN'}">${escapeHtml(value)}</span>`;

const state = {view:'overview', range:null, summary:null, previousSummary:null, listing:null, status:null, security:null, page:0, cursors:[null], nextCursor:null, controller:null, requestId:0, auto:true, busy:false, lastSuccess:null, nextRefresh:0, backoff:5000};
const viewLabels = {overview:['Overview','Security overview'],events:['Tool calls','Tool call history'],asks:['ASK lifecycle','Human review lifecycle'],security:['Security audit','Security & audit']};
const askLabels = {ISSUED:'Issued',PRESENTED:'Presented',ANSWER_RECEIVED:'Answer received',RECHECKED:'Rechecked',DECLINED:'Declined',EXPIRED:'Expired',CANCELLED:'Cancelled'};
const routingLabels = {RULE_ALLOW:'코드 규칙으로 허용',RULE_DENY:'코드 규칙으로 차단',SEMANTIC:'Jev 분석 + 엔진 정책',ANALYSIS_FAILED:'분석·검증 실패',UNKNOWN:'처리 경로 미기록'};
const outcomeLabels = {SUCCEEDED:'실행 완료',REPORTED_ERROR:'실행했지만 오류 발생',NOT_EXECUTED:'실행하지 않음',IN_PROGRESS:'처리 중',UNKNOWN:'실행 결과 미확인'};
const askStateLabels = {ISSUED:'질문 생성',PRESENTED:'사용자에게 질문 표시',ANSWER_RECEIVED:'사용자 답변 접수',RECHECKED:'답변 후 엔진 재판정',DECLINED:'사용자가 거절함',EXPIRED:'질문 유효기간 만료',CANCELLED:'질문 취소'};
const toolLabels = {read_file:'파일 읽기',write_file:'파일 저장',read_github_issue:'이슈 자료 읽기',read_project_file:'프로젝트 파일 읽기',edit_project_file:'프로젝트 파일 변경',run_npm_install:'npm 패키지 설치'};

function reasonLabel(item){return item.reasons[0]?.label||item.reasons[0]?.code||'판정 사유 미기록';}
function renderTaskContext(item){
  const target=item.target_display||item.candidate_summary?.target;
  const subject=target?`<code>${escapeHtml(target)}</code>`:'연결된 작업 대상';
  const tools={
    read_file:[`${subject} 파일의 내용을 읽으려 했습니다.`,'파일을 열어 내용을 가져오는 기능입니다.'],
    write_file:[`${subject} 파일에 내용을 저장하려 했습니다.`,'파일을 새로 만들거나 기존 내용을 덮어쓰는 기능입니다.'],
    read_project_file:[`${subject} 파일의 내용을 읽으려 했습니다.`,'연결된 프로젝트 안의 지정 파일을 읽는 기능입니다.'],
    edit_project_file:[`${subject} 파일의 일부 내용을 바꾸려 했습니다.`,'기존 문구를 찾아 지정한 새 문구로 바꾸는 기능입니다.'],
    read_github_issue:['설치 문제에 관한 이슈 자료를 읽으려 했습니다.','이 시연에서는 미리 준비한 로컬 이슈 스냅샷을 가져옵니다.'],
    run_npm_install:['연결된 프로젝트에서 npm 패키지를 설치하려 했습니다.','필요한 패키지를 설치하는 정해진 npm 명령을 실행하는 기능입니다.']
  };
  const action=tools[item.tool];
  const sentence=action?`에이전트가 ${action[0]}`:'에이전트가 아래 도구의 실행을 요청했습니다. 지원하는 작업 설명이 없어 구체적인 동작을 추측하지 않습니다.';
  return `<section class="task-context"><h3>어떤 작업을 하려 했나요?</h3><p class="task-sentence">${sentence}</p><p><strong>사용 도구:</strong> ${escapeHtml(toolLabels[item.tool]||item.tool)} <code>${escapeHtml(item.tool)}</code></p>${action?`<p>${escapeHtml(action[1])}</p>`:''}<p class="context-boundary">실제로 실행하려던 도구 요청 한 건입니다. 아래에서 사용자 요청과 도구 인자를 마스킹된 미리보기로 비교할 수 있습니다. 생략되거나 가려진 내용을 추측하지 않습니다.</p></section>`;
}
function renderContentPreview(item){
  const preview=item.content_preview;
  if(!preview)return '<section class="explanation-note">이 서버 응답에는 요청·인자 미리보기가 없습니다.</section>';
  const labels={DISPLAYED:'마스킹 검사를 거친 미리보기',MASKED:'민감한 값을 가린 미리보기',WITHHELD:'안전한 마스킹을 확인하지 못해 내용 비공개',UNAVAILABLE:'이 기록에 내용 없음'};
  const field=(title,value)=>`<article class="preview-field"><h4>${escapeHtml(title)}</h4><p class="preview-status">${escapeHtml(labels[value.status]||'미리보기 상태 미확인')}${value.truncated?' · 길어서 일부만 표시':''}</p>${typeof value.text==='string'?`<pre class="preview-text">${escapeHtml(value.text||'(빈 내용)')}</pre>`:''}</article>`;
  return `<section class="detail-section"><h3>사용자 요청과 실행하려던 내용 비교</h3>${field('사용자가 요청한 일',preview.user_request)}<div class="preview-fields">${preview.fields.map(f=>field(f.label,f)).join('')}</div>${preview.before_note?`<p class="preview-status">${escapeHtml(preview.before_note)}</p>`:''}<p class="explanation-note">${escapeHtml(preview.note)}</p></section>`;
}
function renderSourcePreview(item){
  const preview=item.source_preview;
  if(!preview)return '';
  const associations={LINKED:'Jev가 행동과 관련된 근거로 연결함 · 인과관계 증명 아님',UNRELATED:'Jev가 연결하지 않은 자료',UNCERTAIN:'Jev의 자료 연결이 불확실함',NOT_EVALUATED:'Jev 자료 연결 검사 미실행',NOT_RECORDED:'Jev 자료 연결 근거 미기록',AFTER_DECISION:'이 읽기 호출이 허용된 뒤에 얻은 자료 · 이 호출의 판정 근거가 아님'};
  const statuses={DISPLAYED:'마스킹 검사를 거친 당시 내용',MASKED:'민감한 값을 가린 당시 내용',WITHHELD:'안전한 마스킹을 확인하지 못해 내용 비공개',UNAVAILABLE:'표시할 문서 본문이 기록돼 있지 않음'};
  const cards=preview.items.map(s=>`<article class="source-card"><h4>${escapeHtml(s.target?.text||'대상 경로 비공개')}</h4><p class="subtle">${escapeHtml(toolLabels[s.tool]||s.tool)} · 읽은 시각 ${escapeHtml(formatTime(s.observed_at))}</p><p class="source-relationship">${s.relationship==='THIS_CALL_RESULT'?'이번 호출로 읽은 자료':'이 작업 전에 읽은 자료'}</p><p>${escapeHtml(associations[s.association]||'자료 연결 상태 미확인')}</p>${s.analysis_complete?'':'<p class="preview-status">엔진의 분석용 사본에 가림 또는 잘림이 기록돼 있습니다.</p>'}<details class="source-document"${s.relationship==='THIS_CALL_RESULT'?' open':''}><summary>당시 문서 내용 보기 · 민감정보 마스킹</summary><p class="preview-status">${escapeHtml(statuses[s.content.status]||'내용 상태 미확인')}${s.content.truncated?' · 길어서 일부만 표시':''}</p>${typeof s.content.text==='string'?`<pre class="preview-text">${escapeHtml(s.content.text||'(빈 내용)')}</pre>`:''}</details>${s.evidence_excerpts?.length?`<details class="source-document"><summary>Jev가 연결한 기록상의 근거 조각</summary><p class="preview-status">문서 본문을 감싼 도구 응답의 일부가 표시될 수 있습니다.</p>${s.evidence_excerpts.map(p=>typeof p.text==='string'?`<pre class="preview-text">${escapeHtml(p.text)}</pre>`:'<p class="preview-status">근거 조각 비공개</p>').join('')}</details>`:''}</article>`).join('');
  return `<section class="detail-section source-section"><h3>에이전트가 읽은 자료와 출처</h3><p class="explanation-note">${escapeHtml(preview.note)}</p>${cards||'<p class="subtle">이 작업 전에 기록된 파일·이슈 읽기 자료가 없습니다. 실제로 실행하지 않은 읽기는 본문을 표시할 수 없습니다.</p>'}${preview.truncated?'<p class="preview-status">자료가 많아 일부 기록만 표시합니다.</p>':''}</section>`;
}
function renderReviewFlow(item){
  const checks=item.explanation?.semantic_checks||[];
  const analyzed=checks.some(c=>c.status==='COMPLETED');
  const hardRule=['RULE_ALLOW','RULE_DENY'].includes(item.routing)||item.reasons.some(r=>r.code==='PROTECTED_RESOURCE');
  const codeStep=analyzed?'코드의 사전 조건을 검사한 뒤 Jev 분석으로 넘어갔습니다. 사전 검사는 최종 실행 허용과 다릅니다.':hardRule?'코드 규칙에서 판정했습니다. 이 후보의 Jev 검사가 미실행인지 아래에서 확인할 수 있습니다.':'개별 사전 검사 결과가 이 조회 기록에 없습니다. 기록하지 않은 통과 여부를 추측하지 않습니다.';
  const semanticStep=analyzed?'Jev가 사용자 요청과 읽은 자료를 바탕으로 이 도구 요청을 검토했습니다. Jev의 답이 곧 실행 권한은 아닙니다.':'기록된 Jev 검사 상태를 아래에 표시합니다. 모든 도구 요청에 Jev를 호출하는 것은 아닙니다.';
  return `<section class="detail-section"><h3>어떤 순서로 검사하나요?</h3><ol class="review-flow"><li><strong>코드로 사전 검사</strong><p>${escapeHtml(codeStep)}</p></li><li><strong>필요하면 Jev 의미 분석</strong><p>${escapeHtml(semanticStep)}</p></li><li><strong>엔진 정책으로 최종 결정</strong><p>코드 검사와 의미 분석 결과를 합쳐 ALLOW·DENY·ASK를 결정합니다. ALLOW 이후에도 Gateway에서 현재 권한과 정확한 실행 요청을 다시 확인합니다.</p></li></ol></section>`;
}
function renderExplanation(item){
  const e=item.explanation;
  if(!e)return '<section class="explanation-note">상세 한글 설명을 제공하는 서버 응답이 없습니다. 아래 기록된 이유 코드와 처리 이력을 확인하세요.</section>';
  const reasons=e.reasons.map(r=>`<article class="reason-card"><h4>${escapeHtml(r.label)}</h4><p>${escapeHtml(r.description)}</p><code>${escapeHtml(r.code)}</code></article>`).join('');
  const rule=e.policy_rule?`<dl class="policy-rule"><dt>적용 규칙</dt><dd>${escapeHtml(e.policy_rule.name)}</dd><dt>규칙의 조건</dt><dd>${escapeHtml(e.policy_rule.condition)}</dd><dt>실제로 시도한 동작</dt><dd>${escapeHtml(e.policy_rule.observed)}</dd><dt>이 기록의 규칙 적용 결과</dt><dd>${escapeHtml(e.policy_rule.violation)}</dd></dl>`:'';
  const holds=e.initial_hold_reasons.length?`<section class="detail-section"><h3>처음 사용자 확인을 요청한 이유</h3>${e.initial_hold_reasons.map(r=>`<article class="reason-card"><h4>${escapeHtml(r.label)}</h4><p>${escapeHtml(r.description)}</p></article>`).join('')}</section>`:'';
  const semantic=e.semantic_checks.map(c=>{
    const completed=c.status==='COMPLETED',notRun=c.status==='NOT_RUN';
    const label=completed?'분석 완료 · 통과를 의미하지 않음':notRun?'분석하지 않음':'분석·검증 결과 확인 불가';
    const note=completed?c.judgment_label:notRun?'이 후보의 해당 Jev 검사는 실행하지 않았습니다.':'유효한 분석 결과를 사용할 수 없습니다.';
    return `<article class="semantic-card"><h4>Jev ${escapeHtml(c.view)} · ${escapeHtml(c.title)}</h4><span class="subtle">${escapeHtml(label)}</span><p>${escapeHtml(note)}</p>${typeof c.confidence==='number'?`<span class="confidence">기록된 모델 확신도 ${escapeHtml((c.confidence*100).toFixed(1))}%</span>`:''}${c.condition_label?`<p class="condition ${c.positive_condition_met===false?'not-met':''}">${escapeHtml(c.condition_label)} · 기준 ${escapeHtml(c.required_confidence*100)}%</p>`:''}</article>`;
  }).join('');
  const failed=e.semantic_checks.filter(c=>c.positive_condition_met===false).map(c=>`Jev ${c.view}(${c.title})`).join(', ');
  const conclusion=item.reasons.some(r=>r.code==='JEV_NOT_AFFIRMED_RISK_CASE')&&failed?`<p class="decision-conclusion"><strong>이 기록에서 부족했던 조건</strong><br>${escapeHtml(failed)}의 긍정 조건이 부족했습니다. 다른 검사가 긍정적이어도 필요한 조건을 모두 충족하지 못하면 실행을 허용하지 않습니다.</p>`:'';
  return `<section class="detail-section"><h3>왜 이런 판정이 나왔나요?</h3><p class="explanation-source">판정 근거: <strong>${escapeHtml(e.decision_source)}</strong></p>${rule}<div class="reason-cards">${reasons||'<p>기록된 상세 사유가 없습니다.</p>'}</div>${e.ask_state_label?`<p class="explanation-source">사용자 질문 상태: <strong>${escapeHtml(e.ask_state_label)}</strong></p>`:''}<p class="explanation-effect">${escapeHtml(e.effect)}</p></section>${holds}<section class="detail-section"><h3>Jev는 이 작업을 어떻게 봤나요?</h3><p class="subtle">A와 B는 서로 다른 도구가 아니라 Jev에 주는 정보와 질문이 다른 두 검사입니다. A는 “사용자가 요청한 일인가?”, B는 “읽은 자료까지 볼 때 요청에 맞는 행동인가?”를 검토합니다.</p>${e.consent_requirement?`<p class="explanation-note">${escapeHtml(e.consent_requirement)}</p>`:''}<div class="semantic-grid">${semantic}</div>${conclusion}<p class="explanation-note">${escapeHtml(e.evidence_note)}</p></section>`;
}
function timelineLabel(entry){
  const known={CANDIDATE_REGISTERED:'도구 요청 접수',PRE_REGISTERED:'실행 후보 등록',EXECUTE_RESERVED:'단회 실행 예약',OBSERVE_COMPLETED:'도구 결과 관측'};
  if(known[entry.type])return known[entry.type];
  if(entry.type.startsWith('DECISION_'))return '엔진 판정 기록';
  if(entry.type.startsWith('ASK_'))return askStateLabels[entry.type.slice(4)]||'사용자 확인 처리';
  return entry.label;
}

function resetRange(){const end=new Date();state.range={from:new Date(end.getTime()-Number($('period').value)*3600000).toISOString(),to:end.toISOString()};state.page=0;state.cursors=[null];}
function queryParams(){const params=new URLSearchParams({...state.range,timezone:'Asia/Seoul',bucket:Number($('period').value)>48?'day':'hour',limit:'20'});for(const [id,key] of Object.entries({session:'session_id',tool:'tool',decision:'decision',outcome:'execution_outcome',reason:'reason_code'})){if($(id).value)params.set(key,$(id).value);}if(state.view==='asks')params.set('initial_decision','ASK');return params;}
function previousQueryParams(){const current=queryParams();const start=new Date(state.range.from),end=new Date(state.range.to),duration=end-start;current.set('from',new Date(start-duration).toISOString());current.set('to',start.toISOString());return current;}
async function api(path, signal){const response=await fetch(`/dashboard/v1/${path}`,{credentials:'same-origin',cache:'no-store',signal});let data;try{data=await response.json();}catch{throw Object.assign(new Error('INVALID_ENGINE_RESPONSE'),{status:response.status});}if(!response.ok){throw Object.assign(new Error(data.error?.code||'ENGINE_UNAVAILABLE'),{status:response.status,retryAfter:Number(response.headers.get('Retry-After')||15)});}return data;}
function setConnection(kind,label){$('sidebarState').textContent=label;$('sidebarDot').className=`status-dot ${kind}`;}
function showFailure(error){if(error.name==='AbortError')return;setConnection('offline','Engine unknown');$('error').innerHTML=`<div class="error-card"><strong>${escapeHtml(error.message)}</strong> · 현재 상태를 확인할 수 없습니다.<br>마지막 성공 조회: ${escapeHtml(state.lastSuccess||'없음')}. 표시 중인 값은 오래된 데이터일 수 있습니다.</div>`;state.backoff=Math.min(60000,Math.max(state.backoff*2,(error.status===429?error.retryAfter:0)*1000));state.nextRefresh=Date.now()+state.backoff;}

async function refresh({newRange=false}={}){
  if(newRange||!state.range)resetRange();
  state.controller?.abort();state.controller=new AbortController();const signal=state.controller.signal;const ticket=++state.requestId;
  state.busy=true;$('refresh').disabled=true;
  try{
    const params=queryParams();const previousParams=previousQueryParams();const listParams=new URLSearchParams(params);if(state.cursors[state.page])listParams.set('cursor',state.cursors[state.page]);
    const [status,summary,previousSummary,listing]=await Promise.all([api('status',signal),api(`summary?${params}`,signal),api(`summary?${previousParams}`,signal),api(`events?${listParams}`,signal)]);
    if(ticket!==state.requestId)return;
    Object.assign(state,{status,summary,previousSummary,listing,nextCursor:listing.next_cursor,lastSuccess:new Date().toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul'}),backoff:5000});
    state.nextRefresh=Date.now()+5000;$('updated').textContent=`Updated ${state.lastSuccess} KST`;$('error').textContent='';setConnection('online','Engine online');
    $('connectionNotice').textContent=status.data_mode==='ENGINE_FIXTURE'?'합성 관측 데이터에 연결됨 · 검증용 엔진이며 실제 모델 성능 측정이 아닙니다.':'로컬 엔진에 안전하게 연결됨 · 조회 전용이며 모델 호출이나 실행 승인을 수행하지 않습니다.';
    render();
    try{state.security=await api(`security?${new URLSearchParams({...state.range,limit:'50'})}`,signal);if(ticket===state.requestId)renderSecurity();}catch(error){if(ticket===state.requestId&&error.name!=='AbortError'){$('alerts').innerHTML='<div class="empty">보안 조회 권한 또는 연결을 확인하세요.</div>';$('securityRows').innerHTML=emptyRow(5,error.message);}}
  }catch(error){if(ticket===state.requestId)showFailure(error);}finally{if(ticket===state.requestId){state.busy=false;$('refresh').disabled=false;}}
}

function render(){renderMetrics();renderReviewBrief();renderChart();renderServices();renderDistribution();renderAskPipeline();renderLedger();renderEvents();renderReasonOptions();}

function trend(current,previous){if(!previous)return 'New';const delta=current-previous;if(delta===0)return 'No change';return `${delta>0?'↑':'↓'} ${Math.abs(delta)} vs prior`;}



function renderReasonOptions(){const select=$('reason');const selected=select.value;select.innerHTML='<option value="">모든 판정 이유</option>'+state.summary.reasons.map(item=>`<option value="${escapeHtml(item.code)}">${escapeHtml(item.label||item.code)} (${formatNumber(item.count)})</option>`).join('');if(selected&&!state.summary.reasons.some(item=>item.code===selected))select.add(new Option(selected,selected));select.value=selected;}
function renderReviewBrief(){
  const asks=state.summary.asks,pending=(asks.ISSUED||0)+(asks.PRESENTED||0),rechecking=asks.ANSWER_RECEIVED||0;
  $('demoBrief').className='demo-brief'+(pending?'':' resolved');
  $('demoStep').textContent='실제 ASK 이력 · 조회 전용';
  $('demoHeadline').textContent=pending?pending+'건의 요청이 사용자 응답을 기다리고 있습니다.':'현재 사용자 응답을 기다리는 요청이 없습니다.';
  $('demoSummary').textContent='질문과 답변은 연결된 에이전트에서 처리합니다. 이 화면은 저장된 상태만 조회합니다.'+(rechecking?' '+rechecking+'건 재검토 대기.':'');
  $('askPending').textContent=formatNumber(pending);
}

function renderMetrics(){
  const s=state.summary,p=state.previousSummary;
  const pending=(s.asks.ISSUED||0)+(s.asks.PRESENTED||0);
  const cards=[['Total calls',s.total_calls,p?.total_calls,'선택 기간의 도구 실행 후보','var(--blue)',''],['Allowed',s.effective_decisions.ALLOW,p?.effective_decisions.ALLOW,'최종 허용 판정','var(--green)',''],['Denied',s.effective_decisions.DENY,p?.effective_decisions.DENY,'최종 거부 판정','var(--red)',''],['Human review',s.initial_decisions.ASK,p?.initial_decisions.ASK,pending+'건 사용자 응답 대기','var(--yellow)',pending?'attention':'']];
  $('metrics').innerHTML=cards.map(([label,value,previous,note,color,klass])=>`<article class="metric ${klass}" style="--metric-color:${color}"><span class="metric-trend">${trend(value,previous)}</span><span class="metric-label">${label}</span><strong class="metric-value">${formatNumber(value)}</strong><span class="metric-note">${note}</span></article>`).join('');
}
function renderChart(){const series=state.summary.series;if(!series.length){$('chart').innerHTML='<div class="empty">선택한 기간에 판정 데이터가 없습니다.</div>';return;}const chart=$('chart'),style=getComputedStyle(chart),width=Math.max(320,chart.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight)),height=Math.max(180,chart.clientHeight-parseFloat(style.paddingTop)-parseFloat(style.paddingBottom)),pad={x:38,y:18,bottom:32},max=Math.max(1,...series.flatMap(item=>[item.initial_ALLOW||0,item.initial_DENY||0,item.initial_ASK||0]));const plotWidth=width-pad.x-16;const slot=plotWidth/Math.max(series.length,7);const groupWidth=Math.min(34,slot*.64);const barWidth=Math.max(5,(groupWidth-6)/3);const base=height-pad.bottom;const y=(value)=>base-(value/max*(height-pad.y-pad.bottom));const steps=Math.min(4,max);let grid='';for(let i=0;i<=steps;i++){const gy=pad.y+i*(height-pad.y-pad.bottom)/steps;grid+=`<line class="grid-line" x1="${pad.x}" y1="${gy}" x2="${width-12}" y2="${gy}"/><text class="axis-value" x="5" y="${gy+3}">${Math.round(max*(steps-i)/steps)}</text>`;}const offset=(plotWidth-slot*series.length)/2;const labelEvery=Math.max(1,Math.ceil(series.length/8));const bars=series.map((item,i)=>{const start=pad.x+offset+i*slot+(slot-groupWidth)/2;const values=[['initial_ALLOW','bar-allow','ALLOW'],['initial_DENY','bar-deny','DENY'],['initial_ASK','bar-ask','ASK']];const rects=values.map(([key,klass],j)=>{const top=y(item[key]||0);return `<rect class="${klass}" x="${start+j*(barWidth+3)}" y="${top}" width="${barWidth}" height="${Math.max(0,base-top)}" rx="2"/>`;}).join('');const incident=(item.initial_ASK||item.initial_DENY)?`<circle class="incident-marker" cx="${start+groupWidth/2}" cy="${Math.max(8,y(Math.max(item.initial_ASK||0,item.initial_DENY||0))-7)}" r="3"/>`:'';const label=i%labelEvery===0||i===series.length-1?`<text class="time-label" x="${start+groupWidth/2}" y="${height-7}" text-anchor="middle">${escapeHtml(formatTime(item.bucket_start,false))}</text>`:'';const title=`${formatTime(item.bucket_start)} · ALLOW ${item.initial_ALLOW||0} · DENY ${item.initial_DENY||0} · ASK ${item.initial_ASK||0} · 클릭하여 사건 보기`;return `<g class="chart-bucket" tabindex="0" role="button" data-bucket="${escapeHtml(item.bucket_start)}"><title>${escapeHtml(title)}</title>${rects}${incident}${label}</g>`;}).join('');chart.innerHTML=`<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">${grid}${bars}</svg>`;}
function renderServices(){const status=state.status;const values=[['Control engine',status.engine.state],['Gateway',status.services.gateway],['Upstream',status.services.upstream],['Jev analysis',status.services.jev],['Policy',status.engine.policy]];$('services').innerHTML=values.map(([name,value])=>{const good=['ONLINE','CONFIGURED'].includes(value);const warn=value==='UNKNOWN'||String(value).includes('NOT_TESTED');return `<div class="service"><span class="service-name"><i class="state-icon ${good?'good':warn?'warn':''}"></i>${escapeHtml(name)}</span><span class="service-state">${escapeHtml(value)}</span></div>`;}).join('');}
function renderDistribution(){const s=state.summary,values=s.effective_decisions,total=Math.max(1,s.total_calls);const colors={ALLOW:'var(--green)',DENY:'var(--red)',ASK:'var(--yellow)',UNKNOWN:'var(--dim)'};$('distribution').innerHTML=`<div class="stack">${Object.entries(values).map(([name,value])=>`<div class="bar-row"><span>${name}</span><div class="bar-track"><div class="bar-fill" style="width:${value/total*100}%;background:${colors[name]}"></div></div><strong>${formatNumber(value)}</strong></div>`).join('')}</div>`;}
function renderAskPipeline(){const asks=state.summary.asks;$('askPipeline').innerHTML=`<div class="pipeline">${Object.entries(askLabels).map(([key,label])=>`<div class="pipeline-row ${asks[key]?'active-stage':''}"><span>${label}</span><strong>${formatNumber(asks[key])}</strong></div>`).join('')}</div>`;}
function renderLedger(){const j=state.summary.jev;const limit=j.unlimited?'Unlimited':formatNumber(j.request_limit);$('jevLedger').innerHTML=`<div class="ledger"><div class="pipeline-row"><span>Status</span><strong>${escapeHtml(j.status)}</strong></div><div class="ledger-row"><span>API requests</span><strong>${formatNumber(j.requests)} / ${limit}</strong></div><div class="ledger-row"><span>Input tokens</span><strong>${formatNumber(j.input_tokens_actual)}</strong></div><div class="ledger-row"><span>Output tokens</span><strong>${formatNumber(j.output_tokens_actual)}</strong></div><div class="ledger-row"><span>Reserved input</span><strong>${formatNumber(j.input_tokens_reserved)}</strong></div></div>`;}
function emptyRow(cols,message='선택한 조건에 해당하는 기록이 없습니다.'){return `<tr><td colspan="${cols}"><div class="empty">${escapeHtml(message)}</div></td></tr>`;}
function renderEvents(){
  const list=state.listing,isAsk=state.view==='asks';
  $('eventHeading').textContent=isAsk?'ASK review history':'Tool call history';
  $('eventCount').textContent=`${formatNumber(list.total)} records`;
  $('eventRows').innerHTML=list.items.map(item=>{
    const risk=item.initial_decision==='ASK'||item.decision==='DENY',reason=item.reasons[0]?.code||'POLICY_EVALUATED';
    return `<tr tabindex="0" class="${risk?'risk-row':''}" data-id="${escapeHtml(item.event_id)}"><td class="mono">${escapeHtml(formatTime(item.created_at))}<span class="subtle">${escapeHtml(item.session_id.slice(0,16))}…</span></td><td><strong>${escapeHtml(item.tool)}</strong><span class="subtle">${escapeHtml(item.target_display)}</span></td><td><span class="decision-flow">${decisionBadge(item.initial_decision)}<span>→</span>${decisionBadge(item.decision)}</span></td><td><span class="outcome">${escapeHtml(outcomeLabels[item.execution.outcome]||item.execution.outcome)}</span>${Number.isInteger(item.execution.exit_code)?'<span class="subtle">종료코드: '+escapeHtml(item.execution.exit_code)+'</span>':''}</td><td><strong class="reason-label">${escapeHtml(reasonLabel(item))}</strong><span class="subtle">${escapeHtml(routingLabels[item.routing]||item.routing)}</span><span class="reason-code">${escapeHtml(reason)}</span></td><td class="inspect">›</td></tr>`;
  }).join('')||emptyRow(6);
  const start=list.total?state.page*20+1:0,end=state.page*20+list.items.length;
  $('pageInfo').textContent=`${start}–${end} of ${formatNumber(list.total)}`;$('prev').disabled=state.page===0;$('next').disabled=!state.nextCursor;
}
function renderSecurity(){const sec=state.security;if(!sec)return;$('securityCount').textContent=`${formatNumber(sec.total)} records`;$('alerts').innerHTML=sec.alerts.map(alert=>`<div class="alert-card ${alert.severity==='INFO'?'info':''}"><span class="alert-code">${escapeHtml(alert.code)}</span><span class="alert-meta">${escapeHtml(alert.severity)} · ${escapeHtml(formatTime(alert.at))} · ${alert.acknowledged?'acknowledged':'unacknowledged'}</span></div>`).join('')||'<div class="empty">보존된 보안 경고가 없습니다.</div>';$('securityRows').innerHTML=sec.items.map(item=>`<tr><td class="mono">${escapeHtml(formatTime(item.at))}</td><td>${escapeHtml(item.kind)}</td><td class="mono">${escapeHtml(item.actor_hash)}</td><td class="mono">${escapeHtml(item.resource_hash)}</td><td>${escapeHtml(item.result)}</td></tr>`).join('')||emptyRow(5);}

async function showDetail(id){
  $('detailBody').innerHTML='<div class="empty">상세 기록을 불러오는 중입니다.</div>';if(!$('detail').open)$('detail').showModal();
  try{
    const item=await api(`events/${encodeURIComponent(id)}`),outcome=item.execution.outcome;
    const summary=item.denial_origin==='ANALYSIS_FAILURE'?'분석을 완료하지 못해 실행을 허용하지 않았습니다.':item.decision==='DENY'?'실행 전에 거부되어 도구를 실행하지 않았습니다.':item.decision==='ASK'?'사용자 확인을 위해 실행을 보류했습니다.':outcome==='REPORTED_ERROR'?'엔진이 실행을 허용했고, 도구가 오류를 보고했습니다.':outcome==='SUCCEEDED'?'엔진이 실행을 허용했고 완료 결과를 관측했습니다.':outcome==='IN_PROGRESS'?'허용 또는 실행 처리가 진행 중입니다.':'최종 실행 결과를 확정할 수 없습니다.';
    $('detailBody').innerHTML=`<div class="detail-content"><div class="detail-title"><h2>${escapeHtml(toolLabels[item.tool]||item.tool)}</h2>${decisionBadge(item.decision)}</div><span class="subtle">${escapeHtml(item.tool)} · ${escapeHtml(item.target_display)}</span><p class="subtle">기록 시각: ${escapeHtml(formatTime(item.created_at))}</p><p class="subtle mono">Session: ${escapeHtml(item.session_id)}</p><p class="detail-record-note">이 창은 선택한 요청 한 건의 상세입니다. 새 시연 기록은 창을 닫고 목록에서 선택하세요.</p><button class="ghost-button" data-session="${escapeHtml(item.session_id)}">이 세션만 보기</button>${renderTaskContext(item)}<section class="event-summary"><span>이 작업에서 일어난 일</span><strong>${escapeHtml(item.explanation?.title||summary)}</strong><p>${escapeHtml(summary)}</p></section><div class="detail-grid"><div class="detail-cell"><span>최초 → 최종 판정</span><strong>${escapeHtml(item.initial_decision)} → ${escapeHtml(item.decision)}</strong></div><div class="detail-cell"><span>실제 실행 결과</span><strong>${escapeHtml(outcomeLabels[outcome]||outcome)}${Number.isInteger(item.execution.exit_code)?' · 종료코드 '+escapeHtml(item.execution.exit_code):''}</strong></div><div class="detail-cell"><span>판정 이유</span><strong>${escapeHtml(reasonLabel(item))}</strong></div></div>${renderContentPreview(item)}${renderSourcePreview(item)}${renderReviewFlow(item)}${renderExplanation(item)}<section class="detail-section"><h3>이 기록에 남은 처리 시각</h3>${item.timeline.map(entry=>`<div class="timeline-item"><time>${escapeHtml(formatTime(entry.at))}</time><strong>${escapeHtml(timelineLabel(entry))}</strong><span class="subtle">${escapeHtml(entry.type)}</span></div>`).join('')}</section><details class="raw-details"><summary>기술 정보 · 원본 코드와 상태 보기</summary><p class="subtle">정책 ${escapeHtml(item.policy)} · 경로 ${escapeHtml(item.routing)}</p><div class="privacy-note">요청·인자는 민감한 값을 가린 미리보기만 제공합니다. 인증 키·토큰·ASK 승인용 비밀값을 제외하고 마스킹 검사를 거친 미리보기만 전달합니다.</div><section class="detail-section"><h3>실행 후보</h3><pre class="code-block">${escapeHtml(JSON.stringify(item.candidate_summary,null,2))}</pre></section><section class="detail-section"><h3>검사 상태</h3><pre class="code-block">${escapeHtml(JSON.stringify(item.checks,null,2))}</pre></section><section class="detail-section"><h3>사용자 확인 이력</h3>${item.ask_history.length?item.ask_history.map(a=>`<div class="pipeline-row"><span>${escapeHtml(askStateLabels[a.state]||a.state)} · ${escapeHtml(a.outcome)}</span><strong>${escapeHtml(a.ask_id)}</strong></div>`).join(''):'<p class="subtle">사용자 확인을 요청한 기록이 없습니다.</p>'}</section></details></div>`;
  }catch(error){$('detailBody').innerHTML=`<div class="empty">${escapeHtml(error.message)} · 기록 만료, 삭제 또는 권한을 확인하세요.</div>`;}
}
function switchView(view){state.view=view;document.querySelectorAll('.nav-item').forEach(button=>button.classList.toggle('active',button.dataset.view===view));const [crumb,title]=viewLabels[view];$('crumb').textContent=crumb;$('pageTitle').textContent=title;$('overviewView').classList.toggle('hidden',view!=='overview');$('eventsView').classList.toggle('hidden',!['events','asks'].includes(view));$('securityView').classList.toggle('hidden',view!=='security');refresh({newRange:true});}
function focusBucket(bucket){const start=new Date(bucket),end=new Date(start.getTime()+(Number($('period').value)>48?86400000:3600000));state.view='events';state.range={from:start.toISOString(),to:end.toISOString()};state.page=0;state.cursors=[null];document.querySelectorAll('.nav-item').forEach(button=>button.classList.toggle('active',button.dataset.view==='events'));$('crumb').textContent='Tool calls';$('pageTitle').textContent=`Events at ${formatTime(bucket,false)}`;$('overviewView').classList.add('hidden');$('eventsView').classList.remove('hidden');$('securityView').classList.add('hidden');refresh();}




document.querySelectorAll('.nav-item').forEach(button=>button.addEventListener('click',()=>switchView(button.dataset.view)));
for(const id of ['period','session','tool','decision','outcome','reason'])$(id).addEventListener('change',()=>refresh({newRange:true}));
$('refresh').addEventListener('click',()=>refresh({newRange:state.page===0}));
$('chart').addEventListener('click',(event)=>{const bucket=event.target.closest('.chart-bucket');if(bucket)focusBucket(bucket.dataset.bucket);});
$('chart').addEventListener('keydown',(event)=>{if(['Enter',' '].includes(event.key)){const bucket=event.target.closest('.chart-bucket');if(bucket){event.preventDefault();focusBucket(bucket.dataset.bucket);}}});
$('next').addEventListener('click',()=>{if(state.nextCursor){state.cursors[++state.page]=state.nextCursor;refresh();}});
$('prev').addEventListener('click',()=>{if(state.page){state.page--;refresh();}});
$('eventRows').addEventListener('click',(event)=>{const row=event.target.closest('[data-id]');if(row){location.hash=row.dataset.id;showDetail(row.dataset.id);}});
$('eventRows').addEventListener('keydown',(event)=>{if(event.key==='Enter'){const row=event.target.closest('[data-id]');if(row)row.click();}});
$('close').addEventListener('click',()=>{$('detail').close();history.replaceState(null,'',location.pathname+location.search);});
$('detail').addEventListener('click',(event)=>{if(event.target===$('detail'))$('close').click();});
window.addEventListener('hashchange',()=>{if(location.hash)showDetail(decodeURIComponent(location.hash.slice(1)));});
setInterval(()=>{if(state.auto&&!document.hidden&&!state.busy&&Date.now()>=state.nextRefresh)refresh({newRange:state.page===0});},1000);

$('viewAsks').addEventListener('click',()=>switchView('asks'));
$('resetFilters').addEventListener('click',()=>{for(const id of ['session','tool','decision','outcome','reason'])$(id).value='';refresh({newRange:true});});
$('autoToggle').addEventListener('click',()=>{state.auto=!state.auto;$('autoToggle').textContent=state.auto?'Auto · 5s':'Paused';});
$('detailBody').addEventListener('click',(event)=>{const button=event.target.closest('[data-session]');if(button&&/^[a-f0-9]{64}$/.test(button.dataset.session)){for(const id of ['tool','decision','outcome','reason'])$(id).value='';$('session').value=button.dataset.session;$('detail').close();history.replaceState(null,'',location.pathname);switchView('events');}});
refresh();if(location.hash)showDetail(decodeURIComponent(location.hash.slice(1)));
