'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge=s=>`<span class="badge ${['ALLOW','DENY','ASK'].includes(s)?s:'UNKNOWN'}">${esc(s)}</span>`;
const labels={ISSUED:'질문 전달 미확인',PRESENTED:'사용자 응답 대기',ANSWER_RECEIVED:'엔진 재검토 대기',RECHECKED:'재검토 완료',DECLINED:'사용자 거절',EXPIRED:'기한 만료',CANCELLED:'취소'};
const fmt=v=>v==null?'미수집':Number(v).toLocaleString();
let view='overview',auto=true,busy=false,epoch=0,controller=null,summary=null,listing=null,range=null,nextCursor=null,cursors=[null],page=0,lastSuccess=null,backoff=5000,nextAt=0;

function resetRange(){const end=new Date();range={from:new Date(end.getTime()-Number($('period').value)*3600000).toISOString(),to:end.toISOString()};cursors=[null];page=0;}
function params(){const p=new URLSearchParams({...range,timezone:'Asia/Seoul',limit:'10'});for(const [id,key] of Object.entries({session:'session_id',agent:'agent',tool:'tool',initial:'initial_decision',decision:'decision',outcome:'execution_outcome',reason:'reason_code',routing:'routing'})){if($(id).value)p.set(key,$(id).value);}if(view==='asks')p.set('initial_decision','ASK');return p;}
async function api(path,signal){const r=await fetch('/dashboard/v1/'+path,{signal,cache:'no-store',credentials:'same-origin'});let d;try{d=await r.json();}catch{throw new Error('ENGINE_API_RESPONSE_UNAVAILABLE');}if(!r.ok){const err=new Error(d.error?.code||'ENGINE_UNAVAILABLE');err.status=r.status;err.retryAfter=Number(r.headers.get('Retry-After')||15);throw err;}return d;}
function failure(err){if(err.name==='AbortError')return;$('engine').textContent='UNKNOWN';$('error').innerHTML=`<div class="error">${esc(err.status||'')} ${esc(err.message)}<br>현재 상태 미확인 · 마지막 성공 조회 ${esc(lastSuccess||'없음')} · 기존 값은 오래된 데이터입니다.</div>`;backoff=Math.min(60000,Math.max(backoff*2,(err.status===429?err.retryAfter:0)*1000));nextAt=Date.now()+backoff;}

async function refresh({newRange=false}={}){
  if(newRange||!range)resetRange();
  controller?.abort();controller=new AbortController();const signal=controller.signal,ticket=++epoch;
  busy=true;$('refresh').disabled=true;
  try{
    const p=params(),lp=new URLSearchParams(p);if(cursors[page])lp.set('cursor',cursors[page]);
    const [state,s,l]=await Promise.all([api('status',signal),api('summary?'+p,signal),api('events?'+lp,signal)]);
    if(ticket!==epoch)return;
    summary=s;listing=l;nextCursor=l.next_cursor;lastSuccess=new Date().toLocaleTimeString('en-GB',{timeZone:'Asia/Seoul'});
    $('engine').textContent=state.engine.state;$('gatewayState').textContent=state.services.gateway;$('upstreamState').textContent=state.services.upstream;$('jevState').textContent=state.services.jev;$('policyState').textContent='policy · '+state.engine.policy;
    $('connectionNotice').textContent=state.data_mode==='ENGINE_FIXTURE'?'연결됨 · 합성 관측을 쓰는 검증용 엔진입니다. 실제 모델 성능 측정이 아닙니다.':'연결됨 · 로컬 엔진의 보존된 실제 이력입니다. 조회만 수행하며 모델을 호출하지 않습니다.';
    $('updated').textContent='조회 '+lastSuccess+' KST';$('error').textContent='';render();
    const sp=new URLSearchParams({...range,limit:'50'});
    try{const sec=await api('security?'+sp,signal);if(ticket===epoch)security(sec);}catch(err){if(ticket===epoch&&err.name!=='AbortError'){$('securityBody').textContent=err.message+' · 보안 조회 권한/연결 확인 필요';$('signalAlerts').textContent='보안 경고 미수집';}}
    backoff=5000;nextAt=Date.now()+backoff;
  }catch(err){if(ticket===epoch)failure(err);}finally{if(ticket===epoch){busy=false;$('refresh').disabled=false;}}
}

function render(){
  if(!summary||!listing)return;
  const total=summary.total_calls,c=summary.initial_decisions,d=summary.effective_decisions;
  $('cards').innerHTML=[['Total tool calls',total,'고유 실행 후보 · 선택한 기간','#829cdf'],['Initially allowed',c.ALLOW,'최초 ALLOW','#6bdba4'],['Initially denied',c.DENY,'최초 DENY','#fa797d'],['ASK requests',c.ASK,'최초 ASK','#efbb64']].map(([t,n,s,color])=>`<div class="panel card" style="--accent:${color}"><div class="eyebrow">${t}</div><div class="number" style="color:${color}">${fmt(n)}</div><div class="tiny">${s}</div></div>`).join('');
  $('breakdown').innerHTML=['ALLOW','DENY','ASK','UNKNOWN'].map((s,i)=>`<div class="barrow"><span>${s}</span><div class="track"><i style="width:${total?d[s]/total*100:0}%;background:${['var(--green)','var(--red)','var(--amber)','#8b94a3'][i]}"></i></div><span>${fmt(d[s])}</span></div>`).join('');
  $('askstats').innerHTML=Object.entries(labels).map(([s,label])=>`<div class="kv"><span>${label}</span><b>${fmt(summary.asks[s])}</b></div>`).join('');
  const j=summary.jev;$('ledger').innerHTML=`<div class="kv">API requests <b>${fmt(j.requests)} / ${j.unlimited?'제한 없음':fmt(j.request_limit)}</b></div><div class="kv">실제 입력 / 출력 토큰 <b>${fmt(j.input_tokens_actual)} / ${fmt(j.output_tokens_actual)}</b></div><div class="kv">입력 예약량 <b>${fmt(j.input_tokens_reserved)}</b></div><div class="kv">남은 입력 예약량 <b>${j.unlimited?'제한 없음':fmt(j.input_reservation_remaining)}</b></div><p class="tiny">${esc(j.scope)} · 기간별 후보 집계와 범위가 다릅니다.</p>`;
  $('aggregatebody').innerHTML='<div class="toolbar">'+Object.entries(summary.execution_outcomes).map(([s,n])=>`<span class="badge UNKNOWN">${esc(s)} ${fmt(n)}</span>`).join('')+'</div><p class="tiny">'+Object.entries(summary.denials).map(([s,n])=>esc(s)+': '+fmt(n)).join(' · ')+'</p>';
  $('rows').innerHTML=listing.items.map(e=>`<tr tabindex="0" data-id="${esc(e.event_id)}"><td class="mono">${esc(new Date(e.created_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}))}</td><td>${esc(e.agent)}<br><span class="tiny mono">${esc(e.session_id.slice(0,16))}…</span></td><td class="mono">${esc(e.tool)}<br><span class="tiny">${esc(e.target_display)}</span></td><td>${badge(e.initial_decision)} → ${badge(e.decision)}</td><td>${esc(e.execution.outcome)}${e.execution.outcome==='UNKNOWN'?'<br>실행 효과 미확정':''}</td><td class="mono">${esc(e.reasons.map(r=>r.code).join(', '))}<br>${esc(e.routing)}</td></tr>`).join('')||'<tr><td colspan="6" style="padding:32px;text-align:center">선택한 조건에 해당하는 후보가 없습니다.</td></tr>';
  $('count').textContent=fmt(listing.total)+' filtered candidates';$('pageinfo').textContent=`${listing.total?page*10+1:0}–${page*10+listing.items.length} / ${listing.total} · 서버 전체 집계`;$('prev').disabled=page===0;$('next').disabled=!nextCursor;
  chart(summary.series);
  const select=$('reason'),selected=select.value;select.innerHTML='<option value="">All reasons</option>'+summary.reasons.map(r=>`<option value="${esc(r.code)}">${esc(r.code)}</option>`).join('');if(selected&&!summary.reasons.some(r=>r.code===selected))select.add(new Option(selected,selected));select.value=selected;
}

function chart(series){
  const max=Math.max(1,...series.map(s=>s.total_calls)),width=720/Math.max(1,series.length);
  let svg='<svg viewBox="0 0 800 210" width="100%" height="100%" role="img" aria-label="시간별 최초 판정 추이">';
  series.forEach((b,i)=>{let y=170;['ALLOW','DENY','ASK','UNKNOWN'].forEach((s,j)=>{const h=(b['initial_'+s]||0)/max*145;svg+=`<rect x="${35+i*width}" y="${y-h}" width="${Math.max(1,width-5)}" height="${h}" fill="${['#6bdba4','#fa797d','#efbb64','#8b94a3'][j]}"><title>${esc(b.bucket_start)} ${s}: ${b['initial_'+s]||0}</title></rect>`;y-=h;});if(i%Math.max(1,Math.ceil(series.length/6))===0)svg+=`<text x="${35+i*width}" y="195">${esc(new Date(b.bucket_start).toLocaleTimeString('en-GB',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit'}))}</text>`;});$('chart').innerHTML=svg+'</svg>';
}

function security(sec){
  const alerts=sec.alerts.map(a=>`<div class="alert">${esc(a.code)} · ${esc(a.severity)}<br><span class="tiny">${esc(a.at)} · ${a.acknowledged?'확인됨':'미확인'}</span></div>`).join('')||'<p>보존된 경고 없음</p>';
  $('signalAlerts').innerHTML=alerts;
  $('securityBody').innerHTML=alerts+'<table><tr><th>TIME</th><th>ACTION</th><th>ACTOR HASH</th><th>RESOURCE HASH</th><th>RESULT</th></tr>'+sec.items.map(e=>`<tr><td>${esc(new Date(e.at).toLocaleString('ko-KR'))}</td><td>${esc(e.kind)}</td><td class="mono">${esc(e.actor_hash)}</td><td class="mono">${esc(e.resource_hash)}</td><td>${esc(e.result)}</td></tr>`).join('')+'</table><p class="tiny">최신 페이지50건 · 경고 확인/실행 승인 기능 없음</p>'+(sec.next_cursor?'<button id="securityMore">다음 감사 기록</button>':'');
  if($('securityMore'))$('securityMore').onclick=async()=>{const p=new URLSearchParams({...range,limit:'50',cursor:sec.next_cursor});try{security(await api('security?'+p));}catch(err){failure(err);}};
}

async function detail(id){
  $('detailbody').textContent='조회 중…';if(!$('detail').open)$('detail').showModal();
  try{const e=await api('events/'+encodeURIComponent(id));
    $('detailbody').innerHTML=`<div class="mono muted">${esc(e.event_id)}<br>session: ${esc(e.session_id)}</div><h2>${esc(e.tool)} ${badge(e.decision)}</h2><p>${esc(e.target_display)}</p><div class="kv">최초 → 최종 <span>${badge(e.initial_decision)} → ${badge(e.decision)}</span></div><div class="kv">실제 실행 결과 <b>${esc(e.execution.outcome)}</b></div>${e.execution.outcome==='UNKNOWN'?'<p>실행 효과 미확정</p>':''}<p class="mono tiny">${esc(e.policy)} · ${esc(e.routing)}</p><h3>요청·후보</h3><p>${esc(e.user_request_summary)}</p><pre>${esc(JSON.stringify(e.candidate_summary,null,2))}</pre><h3>출처</h3>${e.sources.map(s=>`<p>${esc(s.label)} · ${esc(s.origin)}<br>Integrity ${esc(s.integrity)} / Completeness ${esc(s.completeness)}</p>`).join('')||'<p>표시 가능한 출처 없음</p>'}<h3>검사·ASK</h3><pre>${esc(JSON.stringify(e.checks,null,2))}</pre>${e.ask_history.map(a=>`<p>${esc(a.ask_id)} · ${esc(a.state)} → ${esc(a.outcome)}<br>${esc(a.question_redacted)}<br>${esc(a.answer_summary)}</p>`).join('')||'<p>ASK 없음</p>'}<h3>Timeline</h3><div class="timeline">${e.timeline.map(t=>`<p>${esc(t.at)}<br>${esc(t.label)}</p>`).join('')}</div><p class="tiny">원문·nonce·승인 토큰 비공개. 실행 승인·사용자 답변은 대시보드에서 처리하지 않습니다.</p>`;
  }catch(err){$('detailbody').textContent=err.message+' · 삭제·만료·권한·연결을 확인하세요.';}
}

for(const id of ['period','session','agent','tool','initial','decision','outcome','reason','routing'])$(id).addEventListener(id==='session'?'change':'change',()=>refresh({newRange:true}));
$('refresh').onclick=()=>refresh({newRange:page===0});$('auto').onclick=()=>{auto=!auto;$('auto').textContent=auto?'Ⅱ Auto · 5s':'▷ Paused';};
$('next').onclick=()=>{if(nextCursor){cursors[++page]=nextCursor;refresh();}};$('prev').onclick=()=>{if(page){page--;refresh();}};
$('reset').onclick=()=>{['session','agent','tool','initial','decision','outcome','reason','routing'].forEach(id=>$(id).value='');refresh({newRange:true});};
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{view=b.dataset.view;document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x===b));$('overview').classList.toggle('hide',view!=='overview');$('history').classList.toggle('hide',view==='security');$('aggregate').classList.toggle('hide',view==='security');$('security').classList.toggle('hide',view!=='security');$('title').textContent={overview:'Engine overview',events:'Tool call history',asks:'ASK lifecycle',security:'Security & audit'}[view];refresh({newRange:true});});
$('rows').onclick=e=>{const row=e.target.closest('[data-id]');if(row){location.hash=encodeURIComponent(row.dataset.id);detail(row.dataset.id);}};
$('rows').onkeydown=e=>{if(e.key==='Enter')e.target.click();};$('close').onclick=()=>{$('detail').close();history.replaceState(null,'',location.pathname+location.search);};
window.onhashchange=()=>{if(location.hash)detail(decodeURIComponent(location.hash.slice(1)));};
setInterval(()=>{if(auto&&!document.hidden&&!busy&&Date.now()>=nextAt)refresh({newRange:page===0});},1000);
refresh();if(location.hash)detail(decodeURIComponent(location.hash.slice(1)));
