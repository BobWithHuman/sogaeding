"""Fixed, read-only explanations; never expose model prose or source content."""
import math


# Copy is authored here, not taken from prompts, source documents or model text.
REASONS = {
    'PUBLIC_ENROLLED_READ': ('등록된 공개 자료 읽기', '서버가 허용한 공개 읽기 대상이어서 코드 규칙으로 허용했습니다. 자료 내용 전체가 안전하다는 인증은 아닙니다.'),
    'USER_INTENT_SUPPORTED': ('사용자 요청에 맞는 작업', '사용자 요청의 범위와 자료를 포함한 작업의 정당성이 정책의 허용 조건을 충족했습니다.'),
    'PROTECTED_RESOURCE': ('보호 대상 접근 차단', '서버 정책이 보호하는 경로나 자료에 접근하려 했습니다. 파일 내용에서 공격을 발견한 것이 아니라 보호 규칙에 따라 차단했습니다.'),
    'SECURITY_CONFIGURATION_FORBIDDEN': ('보안 설정 약화 차단', '보안 검증을 끄는 등 정책상 금지한 설정 변경을 시도했습니다. 이 차단은 코드 규칙에 따른 것이며 Jev의 공격 탐지 결과와 구분합니다.'),
    'SECURITY_CONFIG_UNPARSED': ('안전성을 확인할 수 없는 설정 변경', '지원하는 설정 형식이나 허용 범위를 벗어나 안전하게 검사할 수 없었습니다. 공격을 확정한 것은 아닙니다.'),
    'EXTERNAL_INSTRUCTION_DEPENDENCY': ('외부 추가 지시를 따른 작업 차단', '의미 분석에서 사용자 요청을 넘어 외부 자료의 추가 지시를 따르는 행동으로 판정했습니다. 이 기록만으로 특정 문장의 인과관계가 증명되는 것은 아닙니다.'),
    'OUTSIDE_TASK_SCOPE': ('사용자 요청 범위를 벗어난 작업', '의미 분석에서 실제 사용자 요청에 없거나 요청에 어긋나는 행동으로 판정했습니다.'),
    'JEV_NOT_AFFIRMED_RISK_CASE': ('정상 작업이라는 근거가 부족해 차단', '별도 확인이 필요한 작업인데, 사용자 요청 범위와 작업의 정당성에 대한 필요한 긍정 조건을 충족하지 못했습니다. ASK로 넘기기 전에 차단했으며, 공격을 확정했다는 뜻은 아닙니다.'),
    'JEV_REJECTED_HELD_CASE': ('확인이 필요한 작업에서 부정 판단', '별도 확인이 필요한 작업을 검토한 결과, 요청 범위 이탈이나 외부 추가 지시 채택에 대한 정책상 부정 조건이 충족돼 차단했습니다.'),
    'USER_ANSWER_AND_FRESH_POLICY_AFFIRMED': ('사용자 응답 후 재검사 통과', '에이전트의 실제 사용자 질문에 답변이 접수된 뒤 엔진이 다시 검사해 허용했습니다. 사용자 동의만으로 자동 허용한 것은 아닙니다.'),
    'ANALYSIS_UNAVAILABLE': ('분석을 완료하지 못해 실행 보류', '분석이나 검증을 완료할 수 없어 안전하게 실행을 허용하지 않았습니다. 모델이 공격을 탐지했다는 뜻은 아닙니다.'),
    'SEMANTIC_UNCERTAIN': ('정당성을 확정하기 어려운 작업', '의미 분석만으로 작업의 정당성을 충분히 확인하지 못했습니다. 실제 사용자 확인과 재검토가 필요할 수 있습니다.'),
    'DEMO_AUTHORITY_OR_SEMANTICS_UNRESOLVED': ('실행 권한이나 작업의 정당성 확인 필요', '자동 허용에 필요한 권한 또는 의미 분석 조건이 해결되지 않았습니다. 별도 확인과 재판정이 필요합니다.'),
    'TURN_ANALYSIS_STOPPED': ('현재 요청의 분석이 중단됨', '현재 요청에서 분석 중단이 기록되어 추가 실행을 허용하지 않았습니다. 공격을 확정한 결과는 아닙니다.'),
    'SENSITIVE_RESOURCE_REQUIRES_CONSENT': ('보호 자료 접근에 사용자 확인 필요', '서버가 이 대상에 별도 사용자 확인을 요구하도록 설정했습니다. 실제 개인정보를 탐지했다는 의미는 아닙니다.'),
    'OUTSIDE_TASK_CAPABILITY_REQUIRES_CONSENT': ('별도 권한 사용에 사용자 확인 필요', '현재 위임 범위에서 자동 실행할 수 없는 권한을 사용하므로 사용자 확인이 필요합니다.'),
    'PROTECTED_USER_PATH_REQUIRES_CONSENT': ('보호 경로 접근에 사용자 확인 필요', '사용자 보호 경로에 접근하려 하므로 이번 작업에 대한 확인이 필요합니다.'),
    'SIDE_EFFECT_OR_CONSENT_NOT_DELEGATED': ('자동 변경 권한 확인 필요', '파일 변경 등 부수 효과를 자동으로 실행할 권한이 확인되지 않았습니다.'),
    'SECURITY_CONFIGURATION_REQUIRES_CONSENT': ('보안 설정 변경에 사용자 확인 필요', '보안 설정에 영향을 주는 작업이어서 별도 확인이 필요합니다.'),
    'NONPUBLIC_READ_REQUIRES_CONSENT': ('비공개 자료 열람에 사용자 확인 필요', '비공개 자료를 읽는 작업이어서 이번 접근에 대한 확인이 필요합니다.'),
    'PRIVATE_MUTATION_REQUIRES_CONSENT': ('비공개 자료 변경에 사용자 확인 필요', '비공개 자료를 바꾸는 작업이어서 이번 변경에 대한 확인이 필요합니다.'),
    'ASK_RECHECK_UNRESOLVED': ('사용자 응답 후에도 허용 조건 미충족', '사용자 답변 뒤 재검사에서도 실행에 필요한 조건을 충족하지 못해 차단했습니다.'),
    'USER_DECLINED': ('사용자가 진행을 거절함', '사용자가 실제 질문 양식에서 진행을 거절했습니다.'),
    'USER_CANCELLED': ('사용자가 질문을 취소함', '사용자가 실제 질문 양식에서 응답을 취소해 실행을 허용하지 않았습니다.'),
    'ASK_DECLINED': ('사용자가 진행을 거절함', '사용자가 실제 질문 양식에서 진행을 거절했습니다.'),
}

JUDGMENTS = {
    'A': {'WITHIN_TASK': '사용자 요청 범위 안', 'OUTSIDE_TASK': '사용자 요청 범위 밖', 'UNCERTAIN': '작업 범위 불확실'},
    'B': {'LEGITIMATE': '자료를 활용한 정상 작업', 'EXTERNAL_ADOPTION': '외부 추가 지시 채택',
          'OUTSIDE_TASK': '사용자 요청에 어긋나는 작업', 'UNCERTAIN': '작업의 정당성 불확실'},
}
EXECUTIONS = {'SUCCEEDED': '실행 완료', 'REPORTED_ERROR': '실행했지만 도구가 오류를 보고함',
              'NOT_EXECUTED': '실행하지 않음', 'IN_PROGRESS': '처리 중', 'UNKNOWN': '실제 실행 결과 미확인'}
# Versioned interpretation of recorded consent conditions, not a new policy.
CONSENT_THRESHOLDS = {'engine-2026-10-24-gate6-1': .50}
RISK_REASONS = {'JEV_NOT_AFFIRMED_RISK_CASE', 'JEV_REJECTED_HELD_CASE',
                'SENSITIVE_RESOURCE_REQUIRES_CONSENT', 'OUTSIDE_TASK_CAPABILITY_REQUIRES_CONSENT'}


def reason_text(value):
    return REASONS.get(value, ('상세 해설이 없는 사유', '이유 코드는 기록돼 있지만 제공할 수 있는 한글 상세 해설은 없습니다. 추가 내용을 추측하지 않습니다.'))


def semantic_checks(context):
    """Only allowlisted enums and finite validated confidence leave the server."""
    trace = context.get('policy_trace')
    trace = trace if isinstance(trace, dict) else {}
    observations = trace.get('view_observations')
    observations = observations if isinstance(observations, dict) else {}
    checks = context.get('view_checks')
    checks = checks if isinstance(checks, dict) else {}
    result = []
    for view, title in (('A', '사용자 요청 범위 검사'), ('B', '자료를 포함한 행동 검사')):
        check = checks.get(view)
        check = check if isinstance(check, dict) else {}
        status = check.get('status')
        state = 'COMPLETED' if status == 'VALID' else 'NOT_RUN' if status in (None, 'NOT_RUN', 'NOT_RUN_RULE') else 'UNAVAILABLE'
        row = {'view': view, 'title': title, 'status': state, 'judgment': None,
               'judgment_label': '세부 판단 기록 없음', 'confidence': None}
        # A completed request is not the same as an affirmative observation.
        allowed_questions = {'task_relation'} if view == 'A' else {'behavior', 'current_behavior', 'benchmark_behavior'}
        entries = observations.get(view)
        matches = [e for e in entries if isinstance(e, dict) and e.get('question') in allowed_questions] if isinstance(entries, list) else []
        if state == 'COMPLETED' and len(matches) == 1:
            entry = matches[0]
            choice, confidence = entry.get('choice'), entry.get('effective_confidence')
            if isinstance(choice, str) and choice in JUDGMENTS[view]:
                row.update(judgment=choice, judgment_label=JUDGMENTS[view][choice])
                if type(confidence) in (int, float) and math.isfinite(confidence) and 0 <= confidence <= 1:
                    row['confidence'] = confidence
        result.append(row)
    return result


def policy_detail(item, context, evidence):
    reasons = {r['code'] for r in item['reasons']}
    action = {'write':'파일 쓰기', 'read':'자료 읽기', 'execute':'명령 실행'}.get(item.get('candidate_summary',{}).get('action'), '도구 실행')
    result = {'name': '기록된 정책 사유', 'condition': '이유 코드에 대응하는 개별 규칙 설명이 없습니다.',
              'observed': action + ' / 대상: ' + (item.get('target_display') or '개별 파일 경로 없음'),
              'violation': '기록하지 않은 조건을 추측하지 않습니다.', 'basis': 'STORED_REASON_ONLY'}
    if 'PROTECTED_RESOURCE' in reasons:
        result.update(name='보호 자원 표식 접근 금지',
                      condition='도구 요청에 서버가 지정한 보호 표식이 포함되면 실행을 차단합니다.',
                      violation='보호 자원 규칙에 걸렸다는 당시 사유는 남아 있습니다. 당시 설정과 일치하는 보호 표식까지 확인할 근거는 부족합니다.')
        hits = (evidence or {}).get('resource_hits') or []
        if (evidence or {}).get('grant_matches') and hits:
            descriptions = [('대상 경로' if hit['location']=='TARGET' else '도구 인자') + '에 보호 표식 ' + hit['marker'] + ' 포함' for hit in hits]
            result.update(violation='; '.join(descriptions), basis='STORED_REASON_AND_MATCHING_GRANT')
    elif 'SECURITY_CONFIGURATION_FORBIDDEN' in reasons:
        npm = item.get('tool') == 'edit_project_file' and item.get('target_display') == '.npmrc'
        result.update(name='npm TLS 인증서 검증 유지' if npm else '보안 설정 약화 금지',
                      condition='npm의 strict-ssl을 false로 끄는 변경은 허용하지 않습니다.' if npm else '정책상 금지된 보안 설정 변경은 허용하지 않습니다.',
                      violation='이 설정 변경이 금지 규칙에 해당한다는 코드 판정이 기록됐습니다. 구체적인 변경 문구는 마스킹된 인자 미리보기에서 확인합니다.')
    elif reasons & {'JEV_NOT_AFFIRMED_RISK_CASE','JEV_REJECTED_HELD_CASE'}:
        threshold = CONSENT_THRESHOLDS.get(context.get('policy'))
        result.update(name='동의가 필요한 작업의 사전 긍정 조건',
                      condition='ASK로 진행하려면 권한 검증과 함께 A의 요청 범위 안·B의 정상 작업 판단이 각각 확신도 50% 이상이어야 합니다.' if threshold is not None else '동의 보류 작업은 해당 버전 정책의 권한·의미 판단 조건을 충족해야 합니다. 이 버전의 수치 조건은 확인하지 못했습니다.',
                      violation='긍정 조건 부족으로 사용자 질문 전에 차단했습니다.' if 'JEV_NOT_AFFIRMED_RISK_CASE' in reasons else '의미 분석에서 정책상 부정 조건이 충족돼 차단했습니다.')
    elif 'OUTSIDE_TASK_SCOPE' in reasons:
        result.update(name='사용자 요청 범위 준수', condition='실제 사용자가 요청한 작업 범위를 벗어난 행동은 허용하지 않습니다.',
                      violation='이 실행 후보가 요청 범위를 벗어난다는 의미 판정이 기록됐습니다.')
    elif 'EXTERNAL_INSTRUCTION_DEPENDENCY' in reasons:
        result.update(name='외부 자료의 추가 지시로 작업 확대 금지', condition='외부 자료가 사용자 대신 실행 권한을 부여하거나 추가 행동을 지시할 수 없습니다.',
                      violation='외부 추가 지시를 따르는 행동이라는 의미 판정이 기록됐습니다. 특정 문장의 인과관계를 증명한 것은 아닙니다.')
    elif item.get('denial_origin') == 'ANALYSIS_FAILURE':
        result.update(name='필수 분석 실패 시 실행 금지', condition='필요한 분석·검증을 완료하지 못하면 실행을 허용하지 않습니다.',
                      violation='분석·검증 장애가 기록돼 실행을 허용하지 않았습니다.')
    elif 'SENSITIVE_RESOURCE_REQUIRES_CONSENT' in reasons:
        result.update(name='보호 자료의 개별 사용자 동의', condition='서버가 동의를 요구한 자원은 자동으로 실행하지 않고 실제 사용자에게 질문합니다.',
                      violation='이 자원에 사용자 확인이 필요하다는 판정입니다. 금지 위반으로 확정한 것은 아닙니다.')
    elif 'PUBLIC_ENROLLED_READ' in reasons:
        result.update(name='등록된 공개 읽기 허용', condition='등록·권한·보호 규칙을 확인한 공개 읽기는 코드 규칙으로 허용할 수 있습니다.',
                      violation='해당 읽기 허용 규칙으로 ALLOW한 기록입니다.')
    elif item['decision'] == 'ALLOW':
        result.update(name='실행 허용 조건', condition='등록 권한과 적용 정책의 의미 판단·동의 조건을 충족한 후보만 허용합니다.',
                      violation='적용 정책이 이 실행 후보를 허용했습니다. 실제 실행 성공과는 별개입니다.')
    return result


def explain(item, context, rule_evidence=None):
    reasons = [r['code'] for r in item['reasons']]
    primary = reasons[0] if reasons else None
    title, summary = reason_text(primary)
    decision, routing = item['decision'], item['routing']
    source = {'RULE_ALLOW': '코드 규칙', 'RULE_DENY': '코드 규칙',
              'SEMANTIC': 'Jev 분석 결과 + 엔진 정책', 'ANALYSIS_FAILED': '분석·검증 장애 시 안전 차단'}.get(routing, '처리 경로 분류 미기록')
    if primary == 'PROTECTED_RESOURCE':
        source = '코드의 보호 자원 규칙'
    if item['denial_origin'] == 'USER_DECLINED':
        title, summary = REASONS['USER_DECLINED']
        source = '사용자 거절 + 엔진 정책'
    elif item['denial_origin'] == 'ANALYSIS_FAILURE':
        title, summary = REASONS['ANALYSIS_UNAVAILABLE']
        source = '분석·검증 장애 시 안전 차단'
    effect = {'ALLOW': '실행이 허용됐습니다. 실제 완료 여부는 실행 결과에서 확인합니다.',
              'DENY': '이 후보는 실행을 허용하지 않았습니다. 실제 실행 여부는 실행 결과 항목에서 확인합니다.',
              'ASK': '실행을 보류했습니다. 에이전트의 질문 창에서 실제 사용자 답변을 받은 뒤 다시 판정합니다.'}.get(decision, '기록만으로 최종 판정을 확인할 수 없습니다.')
    holds = []
    for ask in item['ask_history']:
        for reason in ask.get('hold_reasons') or []:
            if isinstance(reason, str) and reason in REASONS and reason not in [r['code'] for r in holds]:
                label, description = reason_text(reason)
                holds.append({'code': reason, 'label': label, 'description': description})
    ask_state = item['ask_history'][-1].get('state') if item['ask_history'] else None
    ask_labels = {'ISSUED': '질문 생성됨', 'PRESENTED': '사용자에게 질문 표시됨',
                  'ANSWER_RECEIVED': '사용자 답변 접수됨', 'RECHECKED': '답변 후 재판정 완료',
                  'DECLINED': '사용자가 거절함', 'EXPIRED': '질문 유효기간 만료', 'CANCELLED': '질문 취소됨'}
    if decision == 'ASK' and ask_state in ('CANCELLED', 'EXPIRED'):
        effect = '이 작업은 실행되지 않았고 질문은 취소되거나 만료됐습니다. 현재 사용자 응답을 기다리는 요청이 아닙니다.'
    semantic = semantic_checks(context)
    threshold = CONSENT_THRESHOLDS.get(context.get('policy'))
    requirement = None
    if threshold is not None and set(reasons) & RISK_REASONS:
        requirement = '이 확인 보류 작업은 A가 요청 범위 안, B가 정상 작업으로 판단하고 각각 모델 확신도 50% 이상이어야 긍정 조건을 충족합니다. 권한 등 다른 검사도 별도로 필요합니다.'
        for row in semantic:
            expected = 'WITHIN_TASK' if row['view'] == 'A' else 'LEGITIMATE'
            met = (row['judgment'] == expected and row['confidence'] >= threshold) if row['confidence'] is not None else None
            row.update(required_confidence=threshold, positive_condition_met=met,
                       condition_label='긍정 조건 충족' if met is True else '긍정 조건 미충족' if met is False else '기록 부족으로 조건 확인 불가')
    return {'title': title, 'summary': summary, 'decision_source': source, 'effect': effect,
            'policy_rule': policy_detail(item, context, rule_evidence),
            'ask_state_label': ask_labels.get(ask_state),
            'execution_label': EXECUTIONS.get(item['execution']['outcome'], EXECUTIONS['UNKNOWN']),
            'reasons': [{'code': r, 'label': reason_text(r)[0], 'description': reason_text(r)[1]} for r in reasons],
            'initial_hold_reasons': holds, 'semantic_checks': semantic, 'consent_requirement': requirement,
            'evidence_note': '설명은 기록된 이유 코드와 검증된 판단 항목을 해석한 것입니다. 요청·도구 인자는 마스킹된 미리보기만 제공하며, 전체 원문·모델 자유 서술은 공개하지 않습니다. 모델 확신도는 실제 정확도나 공격 확률이 아닙니다.'}
