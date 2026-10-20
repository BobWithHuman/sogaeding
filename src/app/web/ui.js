"use strict";
const el = id => document.getElementById(id);
const codes = new Set([
  "AUTH_REQUIRED", "SESSION_INACTIVE", "INVALID_ARGUMENTS", "RESOURCE_OUT_OF_SCOPE",
  "ACTION_BINDING_MISMATCH", "POLICY_CHANGED", "APPROVAL_PENDING", "APPROVAL_EXPIRED",
  "APPROVAL_REJECTED", "APPROVAL_CONSUMED", "AUDIT_UNAVAILABLE", "PDP_UNAVAILABLE",
  "TASK_CALL_BUDGET_EXHAUSTED", "TASK_WRITE_BUDGET_EXHAUSTED", "REQUEST_KEY_CONFLICT",
  "EXECUTION_IN_PROGRESS", "EXECUTION_OUTCOME_UNKNOWN", "EXECUTION_FAILED"
]);
class UIError extends Error {}
let revision = 0;
let creating = false;
let approving = false;
function show(text) { el("status").textContent = text; }
function errorText(error) {
  return error instanceof UIError ? error.message : "요청을 처리하지 못했습니다. 연결과 입력을 확인해 주세요.";
}
function clearTimeline() { revision++; el("timeline").replaceChildren(); }
function clearCredentials() { el("token").value = ""; el("agent").value = ""; }
async function api(path, value) {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), 5000);
  try {
    const response = await fetch(path, {method: value === undefined ? "GET" : "POST",
      redirect: "error", cache: "no-store", signal: abort.signal,
      headers: {"Authorization": "Bearer " + el("token").value, "Content-Type": "application/json"},
      body: value === undefined ? undefined : JSON.stringify(value)});
    const data = await response.json();
    if (!response.ok) {
      const code = data && typeof data === "object" && codes.has(data.code) ? data.code : "요청 실패";
      throw new UIError(code + " (HTTP " + response.status + ")" +
        (response.status === 429 ? " · 잠시 기다린 뒤 다시 시도해 주세요." : ""));
    }
    return data;
  } finally { clearTimeout(timer); }
}
function section(parent, title, value) {
  const heading = document.createElement("h3"); heading.textContent = title; parent.append(heading);
  const pre = document.createElement("pre"); pre.textContent = JSON.stringify(value, null, 2); parent.append(pre);
}
const reasonLabels={USER_INTENT_SUPPORTED:'사용자가 요청한 작업에 해당합니다.',TASK_DATA_SUPPORTED:'수집한 이슈의 정상 데이터를 사용했습니다.',
  EXTERNAL_INSTRUCTION_DEPENDENCY:'외부 문서가 추가한 지시를 따르는 행동입니다.',SEMANTIC_UNCERTAIN:'정상 범위 여부가 모호해 확인이 필요합니다.',
  SOURCE_CONTEXT_MISSING:'같은 이슈의 성공한 읽기 근거가 없습니다.',SOURCE_CONTEXT_INCOMPLETE:'분석 자료가 누락되거나 잘렸습니다.',
  ANALYSIS_UNAVAILABLE:'분석이 완료되지 않아 실행하지 않았습니다.',ANALYSIS_STALE:'분석 중 작업 문맥이 변경됐습니다.',
  ANALYSIS_IN_PROGRESS:'분석이 진행 중이며 실행하지 않았습니다.',EXACT_USER_CONTENT:'사용자가 지정한 정확한 본문입니다.',
  OUTSIDE_TASK_SCOPE:'사용자의 작업 권한 밖 행동입니다.',SENSITIVE_RESOURCE:'민감한 자료는 읽을 수 없습니다.',
  SENSITIVE_DATA_IN_ARGUMENTS:'민감정보를 포함한 후보는 실행하지 않습니다.'};
function decisionCards(parent,data) {
  for(const check of data.checks) {
    const card=document.createElement('section'); card.dataset.callId=check.call_id;
    const heading=document.createElement('h3'); heading.textContent=(check.reason_codes.includes('ANALYSIS_UNAVAILABLE')?'분석 실패 · 실행 보류':check.decision==='ALLOW'?'자동 허용':check.decision==='DENY'?'자동 차단':'예외 확인')+' · '+check.execution_state;
    card.append(heading);
    const reason=document.createElement('p'); reason.textContent=check.reason_codes.map(x=>reasonLabels[x]??x).join(' '); card.append(reason);
    const source=document.createElement('p'); source.textContent='판정 단계 '+(check.decision_stage??'POLICY')+' · 관련 출처 '+check.source_ids.length+'개'; card.append(source);
    for(const related of data.sources.filter(s=>check.source_ids.includes(s.source_id)||s.call_id===check.call_id)) {
      const excerpt=document.createElement('p');excerpt.textContent=related.kind+' · '+related.masked_excerpt;card.append(excerpt);
    }
    const execution=data.executions.find(x=>x.call_id===check.call_id);
    const effect=document.createElement('p');
    const state=execution?.state??check.execution_state;
    const effectText=state==='UNKNOWN'?'실제 효과 불명 · 재실행하지 않습니다.':state==='RESERVED'?'실제 효과 확인 중':
      state==='NOT_STARTED'?'실행 전 · 댓글 효과 0개':execution?.receipt?
      '확인된 댓글 효과 '+execution.receipt.write_count_for_call+'개':'실제 효과 확인 필요';
    effect.textContent=effectText+' · call '+check.call_id; card.append(effect);
    if(check.evidence_refs?.length) section(card,'검증한 출처 근거',check.evidence_refs);
    const diagnostic=data.analysis_diagnostics?.analyses.find(x=>x.call_id===check.call_id);
    if(diagnostic?.diagnostics.length) section(card,'분석 실패 진단 · 공격 식별 성공과 다릅니다',diagnostic.diagnostics);
    parent.append(card);
  }
}
async function loadTimeline(message = "") {
  clearTimeline();
  const mine = revision;
  const sid = el("session").value.trim();
  el("load").disabled = true;
  show("조회 중입니다. 이전 이력은 숨겼습니다.");
  try {
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(sid))
      throw new UIError("세션 ID를 확인해 주세요.");
    const data = await api("/v1/sessions/" + sid + "/timeline");
    data.analysis_diagnostics=await api("/v1/sessions/"+sid+"/diagnostics");
    if (mine !== revision || el("session").value.trim() !== sid) return;
    const parent = el("timeline");
    show(data.status + " · " + data.task_kind + " · " + data.policy_version + (message ? " · " + message : ""));
    decisionCards(parent,data);
    const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='상세 이력과 원문 JSON';details.append(summary);
    section(details, "출처 · 문자열 일치는 관측 근거입니다", data.sources);
    section(details, "판정 · ALLOW는 실행 성공과 다릅니다", data.checks);
    section(details, "실제 실행과 효과 receipt", data.executions);
    section(details, "이력", data.events); parent.append(details);
    for (const approval of data.approvals) {
      const event = data.events.find(x => x.call_id === approval.call_id && x.kind === "CHECKED");
      section(parent, "승인 후보 · " + approval.status, {approval, exact_action: event?.safe_payload});
      if (approval.status !== "PENDING" || data.status !== "ACTIVE") continue;
      if (!event?.safe_payload || event.safe_payload.args_sha256 !== approval.args_sha256) {
        section(parent, "정확한 후보 정보를 확인할 수 없어 승인 버튼을 숨겼습니다", {});
        continue;
      }
      const buttons = [];
      for (const action of ["approve", "reject"]) {
        const button = document.createElement("button");
        button.textContent = action === "approve" ? "이 후보 승인" : "거절";
        buttons.push(button);
        button.onclick = async () => {
          if (approving || mine !== revision || el("session").value.trim() !== sid) return;
          approving = true;
          buttons.forEach(b => { b.disabled = true; });
          el("create").disabled = true;
          let notice;
          try {
            await api("/v1/approvals/" + approval.approval_id + "/" + action,
              action === "approve" ? {expected_args_sha256: approval.args_sha256} : {});
            notice = action === "approve" ?
              "승인했습니다. 아직 실행되지 않았습니다. 같은 MCP 인자와 call ID로 재개해 주세요." : "거절했습니다.";
          } catch (error) { notice = errorText(error); }
          try {
            if (mine === revision && el("session").value.trim() === sid) await loadTimeline(notice);
          } finally {
            approving = false;
            el("create").disabled = creating;
          }
        };
        parent.append(button);
      }
    }
  } catch (error) {
    if (mine === revision) { el("timeline").replaceChildren(); show(errorText(error)); }
  } finally { if (mine === revision) el("load").disabled = false; }
}
el("create").onclick = async () => {
  if (creating || approving) return;
  creating = true;
  clearTimeline();
  const mine = revision;
  el("create").disabled = true;
  el("created").textContent = ""; el("agent").value = ""; el("session").value = "";
  show("작업 세션을 만드는 중입니다.");
  try {
    const value = {task_kind: el("kind").value, user_request: el("request").value, issue_id: Number(el("issue").value)};
    if (value.task_kind === "POST_COMMENT") {
      value.comment_mode=el('mode').value;
      if(value.comment_mode==='EXACT') value.allowed_comment_body = el("body").value;
    }
    const data = await api("/v1/sessions", value);
    if (mine !== revision) return;
    el("session").value = data.session_id; el("agent").value = data.agent_session_token;
    el("created").textContent = "세션 " + data.session_id + " · 에이전트에는 이 세션 토큰만 제공합니다.";
    show("작업 세션을 만들었습니다.");
  } catch (error) { if (mine === revision) show(errorText(error)); }
  finally { creating = false; el("create").disabled = approving; }
};
el("load").onclick = () => loadTimeline();
el("session").addEventListener("input", () => { clearTimeline(); el("load").disabled = false; show("세션 ID를 변경했습니다. 다시 조회해 주세요."); });
el("token").addEventListener("input", () => {
  clearTimeline(); el("agent").value = ""; el("created").textContent = "";
  el("load").disabled = false; show("인증 입력을 변경했습니다. 다시 조회해 주세요.");
});
window.addEventListener("pagehide", () => { clearCredentials(); clearTimeline(); });
window.addEventListener("pageshow", event => { if (event.persisted) { clearCredentials(); clearTimeline(); show("다시 인증하고 조회해 주세요."); } });
el('mode').addEventListener('change',()=>{el('body').hidden=el('mode').value==='ISSUE_SUMMARY';if(el('body').hidden)el('body').value='';});
