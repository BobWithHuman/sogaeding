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



function renderReasonOptions(){const select=$('reason');const selected=select.value;select.innerHTML='<option value="">All reasons</option>'+state.summary.reasons.map(item=>`<option value="${escapeHtml(item.code)}">${escapeHtml(item.code)} (${formatNumber(item.count)})</option>`).join('');if(selected&&!state.summary.reasons.some(item=>item.code===selected))select.add(new Option(selected,selected));select.value=selected;}
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
    return `<tr tabindex="0" class="${risk?'risk-row':''}" data-id="${escapeHtml(item.event_id)}"><td class="mono">${escapeHtml(formatTime(item.created_at))}<span class="subtle">${escapeHtml(item.session_id.slice(0,16))}…</span></td><td><strong>${escapeHtml(item.tool)}</strong><span class="subtle">${escapeHtml(item.target_display)}</span></td><td><span class="decision-flow">${decisionBadge(item.initial_decision)}<span>→</span>${decisionBadge(item.decision)}</span></td><td><span class="outcome">${escapeHtml(item.execution.outcome)}</span>${Number.isInteger(item.execution.exit_code)?'<span class="subtle">exit code: '+escapeHtml(item.execution.exit_code)+'</span>':''}</td><td><strong class="reason-code">${escapeHtml(reason)}</strong><span class="subtle">${escapeHtml(item.routing)}</span></td><td class="inspect">›</td></tr>`;
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
    $('detailBody').innerHTML=`<div class="detail-content"><div class="detail-title"><h2>${escapeHtml(item.tool)}</h2>${decisionBadge(item.decision)}</div><span class="subtle">${escapeHtml(item.target_display)}</span><p class="subtle mono">Session: ${escapeHtml(item.session_id)}</p><button class="ghost-button" data-session="${escapeHtml(item.session_id)}">이 세션만 보기</button><section class="event-summary"><span>What happened</span><strong>${escapeHtml(summary)}</strong></section><div class="detail-grid"><div class="detail-cell"><span>Initial → final</span><strong>${escapeHtml(item.initial_decision)} → ${escapeHtml(item.decision)}</strong></div><div class="detail-cell"><span>Execution</span><strong>${escapeHtml(outcome)}${Number.isInteger(item.execution.exit_code)?' · exit '+escapeHtml(item.execution.exit_code):''}</strong></div><div class="detail-cell"><span>Reason</span><strong>${escapeHtml(item.reasons[0]?.code||item.routing)}</strong></div></div><p class="subtle">${escapeHtml(item.policy)} · ${escapeHtml(item.routing)}</p><section class="detail-section"><h3>처리 타임라인</h3>${item.timeline.map(entry=>`<div class="timeline-item"><time>${escapeHtml(formatTime(entry.at))}</time>${escapeHtml(entry.label)}</div>`).join('')}</section><details class="raw-details"><summary>Technical evidence</summary><div class="privacy-note">원문 요청, 파일 본문, ASK nonce와 승인 토큰은 이 조회 API에 포함되지 않습니다.</div><section class="detail-section"><h3>Candidate</h3><pre class="code-block">${escapeHtml(JSON.stringify(item.candidate_summary,null,2))}</pre></section><section class="detail-section"><h3>Policy checks</h3><pre class="code-block">${escapeHtml(JSON.stringify(item.checks,null,2))}</pre></section><section class="detail-section"><h3>ASK history</h3>${item.ask_history.length?item.ask_history.map(a=>`<div class="pipeline-row"><span>${escapeHtml(a.state)} · ${escapeHtml(a.outcome)}</span><strong>${escapeHtml(a.ask_id)}</strong></div>`).join(''):'<p class="subtle">ASK 기록 없음</p>'}</section></details></div>`;
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
