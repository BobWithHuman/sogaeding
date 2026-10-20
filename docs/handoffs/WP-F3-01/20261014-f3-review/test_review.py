"""Independent F3 contract checks. No paid API or shared database access."""
import asyncio
import importlib.util
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from app.common import SafeError, digest
from app.executor.demo import DemoExecutor
from app.pdp.semantic import material

HERE = Path(__file__).parent


@pytest.fixture
def repo(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('tls_review', '/workspace/tools/prepare_tls.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pki = tmp_path / 'pki'
    module.generate(pki)
    from app import common
    monkeypatch.setattr(common, 'RUNTIME', pki)
    from app.storage.repository import Repository
    return Repository(tmp_path / 'control.sqlite3')


def session(repo):
    return repo.create_session({'task_kind': 'POST_COMMENT', 'comment_mode': 'ISSUE_SUMMARY',
        'user_request': '이슈42를 읽고 사실 요약 댓글을 한 번 작성해줘', 'issue_id': 42})


def value(s, body='배포가 완료됐습니다.', tool='post_issue_comment'):
    return {'session_id': s['session_id'], 'client_request_id': str(uuid4()),
        'tool_name': tool, 'backend_id': 'demo.v1',
        'args': {'issue_id': 42, 'body': body} if tool == 'post_issue_comment' else {'issue_id': 42}}


def reserved(repo, cid, v):
    return repo.reserve(cid, {k: v[k] for k in ('tool_name', 'backend_id', 'args')})


def read(repo, s, text='배포 완료. 문서를 갱신할 필요가 있습니다.'):
    v = value(s, tool='get_issue')
    check = repo.check(v)
    reserve = reserved(repo, check['call_id'], v)
    source = repo.source({'call_id': check['call_id'], 'kind': 'EXTERNAL', 'origin_ref': 'demo:42',
        'content_sha256': digest(text), 'masked_excerpt': text, 'match_values': [], **material(text)})
    repo.report(check['call_id'], {'reservation_id': reserve['reservation_id'], 'state': 'SUCCEEDED',
        'receipt': {'call_id': check['call_id'], 'session_id': s['session_id'], 'tool_name': 'get_issue',
            'write_count_for_call': 0, 'executor_invocations': 1, 'effect_digest': digest(text), 'comment_id': None}})
    return source


class Judge:
    model = 'review-fake-only'

    def __init__(self, use='TASK_DATA', fake_ref=False, delay=0):
        self.use, self.fake_ref, self.delay = use, fake_ref, delay
        self.calls = 0
        self.entered = asyncio.Event()

    async def analyze(self, snapshot):
        self.calls += 2
        self.entered.set()
        await asyncio.sleep(self.delay)
        ref = {'source_id': 'user_request', 'start': 0, 'end': 3, 'quote': snapshot['user_request'][:3]}
        a = {'task_relation': 'DIRECT', 'external_use': 'NONE',
            'reason': 'USER_INTENT_SUPPORTED', 'evidence_refs': [ref]}
        source = snapshot['sources'][0]
        bref = ref if self.use == 'NONE' else {'source_id': source['source_id'], 'start': 0, 'end': 3,
            'quote': source['analysis_text'][:3]}
        if self.fake_ref:
            bref = {**bref, 'source_id': 'forged-source'}
        return a, {'task_relation': 'DIRECT', 'external_use': self.use,
            'reason': 'USER_INTENT_SUPPORTED' if self.use == 'NONE' else 'TASK_DATA_SUPPORTED', 'evidence_refs': [bref]}


def execute(repo, s, v, check):
    reserve = reserved(repo, check['call_id'], v)
    executor = DemoExecutor(repo.path + '.effects')
    if reserve['execute']:
        _, receipt = executor.execute(check['call_id'], s['session_id'], v['tool_name'], v['args'])
        repo.report(check['call_id'], {'reservation_id': reserve['reservation_id'], 'state': 'SUCCEEDED', 'receipt': receipt})
    with sqlite3.connect(repo.path + '.effects') as db:
        return db.execute('SELECT count(*) FROM comments').fetchone()[0]


def record(name, payload):
    target = Path('/review-evidence') / (name + '.json')
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


@pytest.mark.asyncio
async def test_summary_requires_actual_source_evidence(repo):
    s = session(repo)
    read(repo, s, '배포가 아직 진행 중이며 완료되지 않았습니다.')
    v = value(s, '배포가 완료됐습니다.')
    judge = Judge(use='NONE')
    check = await repo.check_async(v, judge)
    effects = execute(repo, s, v, check) if check['decision'] == 'ALLOW' else 0
    record('no-source-ref', {'decision': check['decision'], 'reason_codes': check['reason_codes'],
        'analysis_id': check['analysis_id'], 'evidence_refs': check['evidence_refs'],
        'args_sha256': check['args_sha256'], 'approval_id': check['approval_id'],
        'judge_requests': judge.calls, 'actual_effects': effects})
    assert check['decision'] != 'ALLOW' and effects == 0


@pytest.mark.asyncio
async def test_forged_evidence_fails_closed(repo):
    s = session(repo); read(repo, s)
    v = value(s)
    check = await repo.check_async(v, Judge(fake_ref=True))
    assert check['decision'] == 'DENY' and check['approval_id'] is None
    with pytest.raises(SafeError): reserved(repo, check['call_id'], v)


@pytest.mark.asyncio
async def test_hard_secret_guard_never_calls_judge(repo):
    s = session(repo); read(repo, s)
    v = value(s, 'DEMO_SECRET_DO_NOT_SEND')
    judge = Judge()
    check = await repo.check_async(v, judge)
    assert check['decision'] == 'DENY' and judge.calls == 0
    with pytest.raises(SafeError): reserved(repo, check['call_id'], v)


@pytest.mark.asyncio
async def test_new_source_after_analysis_invalidates_reservation(repo):
    s = session(repo); read(repo, s)
    v = value(s)
    check = await repo.check_async(v, Judge())
    read(repo, s, '문맥이 바뀐 새로운 이슈 내용입니다.')
    with pytest.raises(SafeError, match='ANALYSIS_STALE'): reserved(repo, check['call_id'], v)


@pytest.mark.asyncio
async def test_singleflight_pending_cache_and_conflicting_args(repo):
    s = session(repo); read(repo, s)
    v = value(s); judge = Judge(delay=.1)
    task = asyncio.create_task(repo.check_async(v, judge))
    await judge.entered.wait()
    pending = await repo.check_async(v, judge)
    assert pending['reason_codes'] == ['ANALYSIS_IN_PROGRESS']
    with pytest.raises(SafeError, match='REQUEST_KEY_CONFLICT'):
        await repo.check_async({**v, 'args': {'issue_id': 42, 'body': '다른 후보'}}, judge)
    check = await task
    assert await repo.check_async(v, judge) == check and judge.calls == 2


@pytest.mark.asyncio
async def test_cancelled_analysis_has_no_approval_or_execution(repo):
    s = session(repo); read(repo, s)
    v = value(s); judge = Judge(delay=10)
    task = asyncio.create_task(repo.check_async(v, judge))
    await judge.entered.wait(); task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    check = await repo.check_async(v, judge)
    assert check['reason_codes'] == ['ANALYSIS_UNAVAILABLE'] and check['approval_id'] is None
    with pytest.raises(SafeError): reserved(repo, check['call_id'], v)


@pytest.mark.asyncio
async def test_distinct_summary_candidates_only_one_write_effect(repo):
    s = session(repo); read(repo, s)
    first, second = value(s), value(s, '배포가 마무리되었습니다.')
    checks = await asyncio.gather(repo.check_async(first, Judge()), repo.check_async(second, Judge()))
    assert execute(repo, s, first, checks[0]) == 1
    with pytest.raises(SafeError): execute(repo, s, second, checks[1])
    assert execute(repo, s, first, checks[0]) == 1


@pytest.mark.asyncio
async def test_actual_guard_persists_role_denials_without_credentials(repo, tmp_path, monkeypatch):
    import httpx
    from app.control.main import RequestGuard
    from app.common import secret_file
    audit = tmp_path / 'role-audit.sqlite3'
    monkeypatch.setenv('AUTH_AUDIT_DB_PATH', str(audit))

    async def peer(scope, receive, send):
        await send({'type': 'http.response.start', 'status': 401, 'headers': []})
        await send({'type': 'http.response.body', 'body': b'{"code":"AUTH_REQUIRED"}'})

    tokens = [secret_file('human.token'), secret_file('service.token')]
    for control, url, path in [(True, 'https://127.0.0.1:8000', '/v1/sessions'),
                               (True, 'https://control:8443', '/internal/auth/resolve'),
                               (False, 'https://127.0.0.1:8001', '/mcp')]:
        guard = RequestGuard(peer, control=control)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=guard), base_url=url) as client:
            response = await client.post(path, json={}, headers={'Authorization': 'Bearer deliberately-invalid'})
            assert response.status_code == 401
    # New guard process state does not erase the on-disk records.
    RequestGuard(peer, control=True)
    with sqlite3.connect(audit) as db:
        rows = db.execute('SELECT surface,status,sum(count) FROM auth_failures GROUP BY surface,status ORDER BY surface').fetchall()
    assert rows == [('AGENT', 401, 1), ('HUMAN', 401, 1), ('SERVICE', 401, 1)]
    assert all(token.encode() not in audit.read_bytes() for token in tokens)
    record('role-auth-audit', {'rows': rows, 'credential_hits': 0, 'actual_effects': 0,
        'scope': 'ASGI middleware authentication path; no TCP TLS claim'})


@pytest.mark.asyncio
async def test_auth_audit_failure_is_safe_503(repo, tmp_path, monkeypatch):
    import httpx
    from app.control.main import RequestGuard
    audit = tmp_path / 'fault-audit.sqlite3'
    monkeypatch.setenv('AUTH_AUDIT_DB_PATH', str(audit))

    async def peer(scope, receive, send):
        raise AssertionError('Rejected authentication must not enter the handler')

    guard = RequestGuard(peer, control=True)
    guard.audit.record('HUMAN', 401)
    with sqlite3.connect(audit) as db:
        db.execute("CREATE TRIGGER reject_auth_update BEFORE UPDATE ON auth_failures BEGIN SELECT RAISE(ABORT,'review storage failure'); END")
        db.execute("CREATE TRIGGER reject_auth_insert BEFORE INSERT ON auth_failures BEGIN SELECT RAISE(ABORT,'review storage failure'); END")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=guard), base_url='https://127.0.0.1:8000') as client:
        response = await client.post('/v1/sessions', json={}, headers={'Authorization': 'Bearer deliberately-invalid'})
    assert response.status_code == 503 and response.json() == {'code': 'AUDIT_UNAVAILABLE', 'message': 'AUDIT_UNAVAILABLE'}


def test_attempt_budget_survives_adapter_recreation(tmp_path):
    from app.pdp.judge import OpenAIJudge
    path = tmp_path / 'budget.sqlite3'
    judge = OpenAIJudge(path)
    for index in range(24): judge.claim('review-' + str(index), 'A')
    with pytest.raises(SafeError): OpenAIJudge(path).claim('twenty-fifth', 'B')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0] == 24


@pytest.mark.asyncio
async def test_real_adapter_parameters_and_independent_inputs_without_network(repo, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.pdp import judge as module
    captures = []
    configurations = []

    class SDK:
        def __init__(self, **config):
            configurations.append({k: v for k, v in config.items() if k != 'api_key'})
            self.responses = self
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def create(self, **value):
            captures.append(value)
            return SimpleNamespace(status='completed', output_text='{}',
                output=[SimpleNamespace(type='message', content=[SimpleNamespace(type='output_text')])],
                usage=SimpleNamespace(input_tokens=7, output_tokens=8))

    monkeypatch.setattr(module, 'AsyncOpenAI', SDK)
    monkeypatch.setattr(module, 'secret_file', lambda name: 'review-placeholder-key')
    s = session(repo); read(repo, s)
    _, snapshot = repo.prepare_check(value(s), 'review-fake-sdk')
    adapter = module.OpenAIJudge(tmp_path / 'attempts.sqlite3')
    await adapter.analyze(snapshot)
    views = {json.loads(row['input'][0]['content'])['view']: row for row in captures}
    assert set(views) == {'A', 'B'}
    assert 'sources' not in json.loads(views['A']['input'][0]['content'])
    assert 'sources' in json.loads(views['B']['input'][0]['content'])
    for row in captures:
        assert row['tools'] == [] and row['store'] is False and row['max_output_tokens'] <= 2048
        assert row['input'][0]['role'] == 'user' and row['instructions'] == module.INSTRUCTIONS
    for config in configurations:
        assert config['base_url'] == 'https://api.openai.com/v1' and config['max_retries'] == 0 and config['timeout'] <= 15
    assert len(adapter.usage) == 2 and all(row['status'] == 'COMPLETED' for row in adapter.usage)
    record('fake-sdk-adapter', {'outbound_requests': 0, 'attempt_rows': 2, 'independent_views': sorted(views),
        'tools': [], 'store': False, 'max_retries': 0, 'credential_values_recorded': False})


@pytest.mark.asyncio
@pytest.mark.parametrize('dimension', ['prompt', 'schema', 'model'])
async def test_changed_prompt_version_does_not_execute_old_cached_analysis(repo, monkeypatch, dimension):
    from app.storage import f3
    s = session(repo); read(repo, s)
    v = value(s); judge = Judge()
    check = await repo.check_async(v, judge)
    assert check['decision'] == 'ALLOW'
    if dimension == 'prompt':
        monkeypatch.setattr(f3, 'PROMPT_VERSION', f3.PROMPT_VERSION + '-review-next')
    elif dimension == 'schema':
        monkeypatch.setattr(f3, 'SCHEMA_VERSION', f3.SCHEMA_VERSION + '-review-next')
    else:
        changed = Judge()
        changed.model = 'review-next-model'
    try:
        if dimension == 'model':
            await repo.check_async(v, changed)
        effects = execute(repo, s, v, check)
        blocked = False
    except SafeError as exc:
        effects = 0
        blocked = True
        code = exc.code
    if dimension == 'model':
        assert changed.calls == 0  # Version invalidation must not trigger paid re-analysis.
    record('changed-' + dimension + '-binding', {'blocked': blocked, 'code': code if blocked else None,
        'actual_effects': effects, 'judge_requests': judge.calls, 'analysis_id': check['analysis_id'],
        'scope': 'Configuration/version change on private repository fixture; no paid API'})
    assert blocked and effects == 0
