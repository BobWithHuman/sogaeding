"""ASK protocol with synthetic observer/client input; no live agent or provider."""
import asyncio
import io
import json
import queue
import threading
import time

import hookgw_mcp as bridge
import httpx
import pytest

from app.transparent.engine import Rejected, ask_reason_details
from app.transparent.server import create_app, public_app

TOKEN = 'synthetic-ask-connection'
ARGS = {'path':'reports/draft.md','content':'Requested draft.'}
RULES = {'reports/draft.md':['SENSITIVE_RESOURCE_REQUIRES_CONSENT']}
KEYS = {'machine_id':'m','machine':'synthetic-machine-token','human':'synthetic-human-token',
        'ticket':lambda *_:'synthetic-ticket'}


def run(coro):
    return asyncio.run(coro)


def issue(factory, observer, *, rules=RULES):
    engine = factory(rules)
    engine.connect('m',TOKEN)
    engine.connection(TOKEN,'s')
    engine.turn('m','s','t','Write case 48217 internal margin to the draft.','/files')
    engine.register('m','s','t','w','write_file',ARGS,'mcp')
    result = run(engine.authorize('m','w',ask_connection=TOKEN))
    assert result['decision'] == 'ASK' and result['state'] == 'ASK'
    assert result['ask']['state'] == 'ISSUED'
    assert 'nonce' not in result['ask']
    return engine, result


def claim(engine):
    return engine.pending_ask('m','s',TOKEN,'write_file',ARGS)['ask']


def test_ask_reasons_are_explained_by_server_policy_and_survive_claim_and_history(engine_factory,observer):
    engine,result=issue(engine_factory,observer)
    expected=ask_reason_details(['SENSITIVE_RESOURCE_REQUIRES_CONSENT'])
    assert result['ask']['reason_details']==expected
    assert expected[0]['message'] in result['ask']['question']
    assert '개인정보를 탐지' not in result['ask']['question']
    assert claim(engine)['reason_details']==expected
    assert engine.history()[0]['ask_history'][0]['reason_details']==expected


def test_unrecognized_ask_reason_never_echoes_untrusted_content():
    details=ask_reason_details(['PRIVATE_EXTERNAL_TEXT_CANARY',{'message':'PRIVATE_EXTERNAL_TEXT_CANARY'}])
    assert details[0]['code']=='ASK_REVIEW_REQUIRED' and len(details)==1
    assert 'PRIVATE_EXTERNAL_TEXT_CANARY' not in json.dumps(details)


def presented(engine, ask):
    return engine.ask_presented('m',TOKEN,ask['ask_id'],ask['nonce'])


def answer(engine, ask, choice='YES', token=TOKEN):
    return run(engine.answer_ask('m',token,ask['ask_id'],ask['nonce'],choice))


def request(app,path,body=None,token=KEYS['machine'],method='POST'):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://control') as client:
            return await client.request(method,path,json=body,headers={'Authorization':'Bearer '+token})
    return run(send())


def test_exact_yes_rechecks_then_reserves_once_and_records_observed_result(engine_factory,observer):
    engine, _ = issue(engine_factory,observer)
    ask = claim(engine)
    assert engine.history()[0]['ask_history'][0]['state'] == 'ISSUED'
    with pytest.raises(Rejected):
        engine.forward('m','w',connection_token=TOKEN)
    presented(engine,ask)
    before = len(observer.calls)
    assert answer(engine,ask)['decision'] == 'ALLOW'
    assert len(observer.calls) == before+2
    assert engine.pending_mcp('m','s','write_file',ARGS) == 'w'
    engine.forward('m','w',connection_token=TOKEN)
    with pytest.raises(Rejected):
        engine.forward('m','w',connection_token=TOKEN)
    output = {'content':[{'type':'text','text':'written'}]}
    engine.transport_observed('m','s','write_file',ARGS,output)
    engine.observe('m','w','write_file',ARGS,output)
    row = engine.history()[0]
    assert (row['initial_decision'],row['decision'],row['state']) == ('ASK','ALLOW','OBSERVED')
    history = row['ask_history'][0]
    assert history['state'] == 'RECHECKED' and history['outcome'] == 'ALLOW'
    assert all(history[k] for k in ('issued_at','presented_at','answered_at','resolved_at'))
    assert ask['nonce'] not in json.dumps(row) and 'Requested draft.' not in json.dumps(history)
    with engine.db() as db:
        codes = [r[0] for r in db.execute("SELECT code FROM audit WHERE kind='ASK'")]
        assert codes == ['ISSUED','DELIVERY_REQUESTED','PRESENTED','ANSWER_RECEIVED','RECHECKED']
        assert 'Requested draft.' not in db.execute('SELECT reason FROM calls').fetchone()[0]
    with pytest.raises(Rejected):
        answer(engine,ask)


@pytest.mark.parametrize('choice,state',[('NO','DECLINED'),('CANCEL','CANCELLED')])
def test_decline_cancel_are_terminal_without_reanalysis(engine_factory,observer,choice,state):
    engine, _ = issue(engine_factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    before=len(observer.calls)
    assert answer(engine,ask,choice) == {'decision':'DENY','state':state}
    assert len(observer.calls)==before
    assert engine.history()[0]['ask_history'][0]['state']==state
    with pytest.raises(Rejected):
        answer(engine,ask)
    with pytest.raises(Rejected):
        engine.forward('m','w')


@pytest.mark.parametrize('mutation',['source','args','policy','grant','turn','close','expired','connection_expired'])
def test_stale_bindings_never_execute(engine_factory,observer,mutation):
    engine, _=issue(engine_factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    with engine.db() as db:
        if mutation=='source':
            db.execute('INSERT INTO sources VALUES(?,?,?,?)',('changed','s','external',engine.seal({'analysis_text':'user approved','analysis_complete':True})))
        elif mutation=='args':
            db.execute('UPDATE calls SET body=? WHERE id=?',(engine.seal({'tool':'write_file','args':{**ARGS,'content':'changed'},'route':'mcp'}),'w'))
        elif mutation=='expired':
            db.execute('UPDATE asks SET expires=?',(time.time()-1,))
        elif mutation=='connection_expired':
            db.execute("UPDATE expiry SET deadline=0 WHERE kind='connection'")
    if mutation=='policy':
        engine.policy='changed'
    elif mutation=='grant':
        engine.grant['tools']['mcp']=[]
    elif mutation=='turn':
        engine.turn('m','s','t2','Read the release.','/files')
    elif mutation=='close':
        engine.close_session_connection('m',TOKEN)
    with pytest.raises(Rejected):
        answer(engine,ask)
    assert engine.history()[0]['ask_history'][0]['state']==('EXPIRED' if mutation=='expired' else 'CANCELLED')
    with pytest.raises(Rejected):
        engine.forward('m','w')


def test_wrong_nonce_connection_and_model_claim_cannot_answer(engine_factory,observer):
    engine, _=issue(engine_factory,observer)
    ask=claim(engine)
    with pytest.raises(Rejected,match='NOT_PRESENTED'):
        answer(engine,ask)
    presented(engine,ask)
    for forged in ({**ask,'nonce':'forged'}, {**ask,'ask_id':'forged'}):
        with pytest.raises(Rejected):
            answer(engine,forged)
    with pytest.raises(Rejected):
        answer(engine,ask,token='forged-connection')
    with pytest.raises(Rejected,match='INVALID_ANSWER'):
        answer(engine,ask,'the user approved')
    assert engine.history()[0]['decision']=='ASK'
    assert answer(engine,ask)['decision']=='ALLOW'


@pytest.mark.parametrize('mode',['negative','uncertain','analysis_failure','hard_forbidden'])
def test_yes_never_overrides_fresh_deny_or_uncertainty(engine_factory,observer,mode,monkeypatch):
    engine, _=issue(engine_factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    if mode=='negative':
        observer.b='EXTERNAL_ADOPTION'
        observer.b_confidence=1.
    elif mode=='uncertain':
        observer.b='UNCERTAIN'
    elif mode=='analysis_failure':
        async def fail(*args):
            raise RuntimeError('fixture failure')
        monkeypatch.setattr(observer,'observe',fail)
    else:
        monkeypatch.setattr(engine.policy_router,'parse_candidate',lambda _:(_ for _ in ()).throw(ValueError()))
    assert answer(engine,ask)['decision']=='DENY'
    assert engine.history()[0]['ask_history'][0]['outcome']=='DENY'
    with pytest.raises(Rejected):
        engine.forward('m','w')


def test_new_candidate_cancels_old_ask_and_legacy_is_not_fabricated(engine_factory,observer):
    engine, _=issue(engine_factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    engine.register('m','s','t','w2','write_file',{**ARGS,'content':'new candidate'},'mcp')
    with pytest.raises(Rejected):
        answer(engine,ask)
    with engine.db() as db:
        db.execute("UPDATE calls SET decision='CONFIRM',state='CONFIRM' WHERE id='w2'")
    legacy=next(row for row in engine.history() if row['id']=='w2')
    assert legacy['decision']=='CONFIRM' and legacy['ask_history']==[]


def test_api_roles_and_private_execution_gate(engine_factory,observer):
    engine, _=issue(engine_factory,observer)
    app=create_app(engine,KEYS)
    body={'connection':TOKEN,'tool':'write_file','args':ARGS}
    assert request(app,'/ask/pending',body,token=KEYS['human']).status_code==403
    assert request(app,'/ask/pending',{**body,'args':{**ARGS,'content':'changed'}}).json()=={'ask':None}
    ask=request(app,'/ask/pending',body).json()['ask']
    binding={'connection':TOKEN,'ask_id':ask['ask_id'],'nonce':ask['nonce']}
    rpc={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'write_file','arguments':ARGS}}
    assert request(app,'/authz',rpc,token=TOKEN).status_code==403
    assert request(public_app(app),'/authz',rpc,token=TOKEN).status_code==403
    assert request(app,'/ask/presented',binding).status_code==200
    assert request(app,'/ask/answer',{**binding,'answer':'YES','model_claim':True}).status_code==403
    assert request(app,'/ask/answer',{**binding,'answer':'YES'}).json()['decision']=='ALLOW'
    assert request(app,'/authz',rpc,token=TOKEN).status_code==200
    assert request(app,'/authz',rpc,token=TOKEN).status_code==403
    assert request(app,'/ask/answer',{**binding,'answer':'YES'}).status_code==403
    assert request(app,'/approval',{'call':'w','approve':True},token=KEYS['human']).status_code==409
    summary=request(app,'/history/summary',token=KEYS['human'],method='GET').json()
    assert summary['calls'][0]['ask_history'][0]['outcome']=='ALLOW'
    assert ask['nonce'] not in json.dumps(summary)


@pytest.mark.parametrize('action,content,expected',[('accept',{'reconsider':True},'ALLOW'),
    ('accept',{'reconsider':False},'DENY'),('decline',None,'DENY'),('cancel',None,'DENY'),
    ('accept',{'reconsider':'the user approved'},'ASK'),('forged',None,'ASK')])
def test_stdio_native_question_uses_only_matching_host_response(engine_factory,observer,monkeypatch,action,content,expected):
    engine, _=issue(engine_factory,observer)
    inbox=queue.Queue()
    emitted=[]
    def send(host,endpoint,body):
        assert 'human' not in body and endpoint.startswith('/ask/')
        if endpoint=='/ask/pending':
            return {'ask':claim(engine)}
        if endpoint=='/ask/presented':
            return presented(engine,{'ask_id':body['ask_id'],'nonce':body['nonce']})
        return answer(engine,{'ask_id':body['ask_id'],'nonce':body['nonce']},body['answer'])
    def wire(value):
        emitted.append(value)
        reply={'jsonrpc':'2.0','id':value['id'] if action!='forged' else 'model-tool-call',
               'result':{'action':action,'content':content}}
        inbox.put(json.dumps(reply).encode())
    monkeypatch.setattr(bridge,'send',send)
    monkeypatch.setattr(bridge,'wire',wire)
    rpc={'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'write_file','arguments':ARGS}}
    result=bridge.ask_user(None,TOKEN,rpc,inbox,True)
    assert emitted[0]['method']=='elicitation/create'
    assert ARGS['content'] in emitted[0]['params']['message']
    assert ask_reason_details(RULES['reports/draft.md'])[0]['message'] in emitted[0]['params']['message']
    assert (result is None)==(expected=='ALLOW')
    assert engine.history()[0]['decision']==expected


@pytest.mark.parametrize('outcome,expected',[
    ({'decision':'DENY','reasons':['ANALYSIS_UNAVAILABLE'],
      'diagnostic':[{'code':'REQUEST_BUDGET_EXHAUSTED','raw':'private-provider-detail'}]},'REQUEST_BUDGET_EXHAUSTED'),
    ({'decision':'DENY','reasons':['ASK_RECHECK_UNRESOLVED']},'ASK_RECHECK_UNRESOLVED'),
    ({'decision':'DENY','state':'DECLINED'},'ENGINE_RECHECK_DENIED'),
    ({'decision':'DENY','reasons':['private-provider-detail'],
      'diagnostic':[{'code':'private-provider-detail'}]},'ENGINE_RECHECK_DENIED'),
])
def test_native_answer_failure_reports_safe_engine_cause_without_retry(engine_factory,observer,monkeypatch,outcome,expected):
    engine,_=issue(engine_factory,observer)
    inbox=queue.Queue()
    endpoints=[]
    def send(_host,endpoint,body):
        endpoints.append(endpoint)
        if endpoint=='/ask/pending':
            return {'ask':claim(engine)}
        if endpoint=='/ask/presented':
            return presented(engine,{'ask_id':body['ask_id'],'nonce':body['nonce']})
        assert endpoint=='/ask/answer' and body['answer']=='YES'
        return outcome
    def wire(value):
        inbox.put(json.dumps({'jsonrpc':'2.0','id':value['id'],
                             'result':{'action':'accept','content':{'reconsider':True}}}).encode())
    monkeypatch.setattr(bridge,'send',send)
    monkeypatch.setattr(bridge,'wire',wire)
    rpc={'jsonrpc':'2.0','id':4,'params':{'name':'write_file','arguments':ARGS}}
    held=bridge.ask_user(None,TOKEN,rpc,inbox,True)
    assert held['result']['structuredContent']['code']==expected
    assert held['result']['structuredContent']['decision']=='DENY'
    assert held['result']['structuredContent']['executed'] is False
    assert endpoints==['/ask/pending','/ask/presented','/ask/answer']
    text=json.dumps(held)
    assert 'native user response processed' in text and 'Do not retry automatically' in text
    assert 'private-provider-detail' not in text and 'nonce' not in text and ARGS['content'] not in text


def test_no_question_capability_never_sends_answer_or_dispatches(engine_factory,observer,monkeypatch):
    engine, _=issue(engine_factory,observer)
    monkeypatch.setattr(bridge,'send',lambda *args:{'ask':claim(engine)})
    monkeypatch.setattr(bridge,'wire',lambda _:pytest.fail('No form capability'))
    value={'jsonrpc':'2.0','id':1,'params':{'name':'write_file','arguments':ARGS}}
    result=bridge.ask_user(None,TOKEN,value,queue.Queue(),False)
    assert result['result']['structuredContent']['decision']=='ASK'
    assert result['result']['structuredContent']['reason_details']==ask_reason_details(RULES['reports/draft.md'])
    assert engine.history()[0]['ask_history'][0]['state']=='ISSUED'
    assert 'nonce' not in json.dumps(result)


def test_question_eof_is_not_consent(engine_factory,observer,monkeypatch):
    engine, _=issue(engine_factory,observer)
    inbox=queue.Queue()
    inbox.put(b'')
    def send(_host,endpoint,body):
        if endpoint=='/ask/pending':
            return {'ask':claim(engine)}
        assert endpoint=='/ask/presented'
        return presented(engine,{'ask_id':body['ask_id'],'nonce':body['nonce']})
    monkeypatch.setattr(bridge,'send',send)
    monkeypatch.setattr(bridge,'wire',lambda _:None)
    value={'id':1,'params':{'name':'write_file','arguments':ARGS}}
    assert bridge.ask_user(None,TOKEN,value,inbox,True) is not None
    assert engine.history()[0]['decision']=='ASK'


@pytest.mark.parametrize('action,supported,dispatched',[('accept',True,True),('decline',True,False),('accept',False,False)])
def test_existing_stdio_main_to_engine_private_reservation(engine_factory,observer,tmp_path,monkeypatch,action,supported,dispatched):
    """Real stdio loop + engine/API; gateway/TLS/upstream and client UI are fixtures."""
    engine,_=issue(engine_factory,observer)
    app=create_app(engine,KEYS)
    host=tmp_path/'host'
    host.mkdir()
    (host/'profile.json').write_text(json.dumps({'format':'product-codex-1','gateway_url':'https://127.0.0.1:8140/mcp'}))
    incoming=queue.Queue()
    init={'jsonrpc':'2.0','id':0,'method':'initialize','params':{'protocolVersion':'2025-11-25',
           'capabilities':{'elicitation':{'form':{}}} if supported else {}}}
    call={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'write_file','arguments':ARGS}}
    for value in (init,call):
        incoming.put(json.dumps(value).encode()+b'\n')
    emitted=[]
    gateway=[]
    class Input:
        def readline(self,_limit):
            return incoming.get(timeout=5)
    class Output:
        def write(self,data):
            value=json.loads(data)
            emitted.append(value)
            if value.get('method')=='elicitation/create':
                incoming.put(json.dumps({'jsonrpc':'2.0','id':value['id'],'result':{
                    'action':action,'content':{'reconsider':True}}}).encode()+b'\n')
            if value.get('id')==1:
                incoming.put(b'')
        def flush(self):
            pass
    class Opener:
        def open(self,req,timeout):
            value=json.loads(req.data)
            gateway.append(value['method'])
            if value['method']=='tools/call':
                response=request(app,'/authz',value,token=TOKEN)
                assert response.status_code==200 and response.headers['x-with-human-forward']=='synthetic-ticket'
                result={'content':[{'type':'text','text':'fixture upstream result'}]}
            else:
                result={'protocolVersion':'2025-03-26','capabilities':{'tools':{}}}
            return io.BytesIO(json.dumps({'jsonrpc':'2.0','id':value['id'],'result':result}).encode())
    def send(_host,endpoint,body):
        response=request(app,endpoint,body)
        assert response.status_code==200
        return response.json()
    monkeypatch.setattr(bridge.sys,'argv',['hookgw_mcp.py',str(host)])
    monkeypatch.setattr(bridge.sys,'stdin',type('Stdin',(),{'buffer':Input()})())
    monkeypatch.setattr(bridge.sys,'stdout',type('Stdout',(),{'buffer':Output()})())
    monkeypatch.setattr(bridge.ssl,'create_default_context',lambda **_:None)
    monkeypatch.setattr(bridge.urllib.request,'build_opener',lambda *_:Opener())
    monkeypatch.setenv('WITH_HUMAN_CONNECTION',TOKEN)
    monkeypatch.setattr(bridge,'send',send)
    assert bridge.main() is None
    assert gateway==(['initialize','tools/call'] if dispatched else ['initialize'])
    assert any(v.get('method')=='elicitation/create' for v in emitted)==supported
    assert emitted[0]['result']['protocolVersion']==('2025-11-25' if supported else '2025-03-26')
    assert KEYS['human'] not in json.dumps(emitted) and 'nonce' not in json.dumps(emitted)
    if dispatched:
        engine.observe('m','w','write_file',ARGS,{'ignored':'use trusted transport result'})
        assert engine.history()[0]['state']=='OBSERVED'
    else:
        with pytest.raises(Rejected):
            engine.forward('m','w')


def test_expiry_during_recheck_and_concurrent_replies_fail_closed(engine_factory,observer,monkeypatch):
    engine,_=issue(engine_factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    original=engine.policy_router.evaluate
    async def expire(snapshot):
        result=await original(snapshot)
        with engine.db() as db:
            db.execute('UPDATE asks SET expires=0')
        return result
    monkeypatch.setattr(engine.policy_router,'evaluate',expire)
    assert answer(engine,ask)['decision']=='DENY'
    assert engine.history()[0]['ask_history'][0]['state']=='EXPIRED'
    with pytest.raises(Rejected):
        engine.forward('m','w')


def test_concurrent_yes_is_consumed_once(engine_factory,observer):
    engine,_=issue(engine_factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    results=[]
    def respond():
        try:
            results.append(answer(engine,ask)['decision'])
        except Rejected:
            results.append('REPLAY')
    threads=[threading.Thread(target=respond) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert sorted(results)==['ALLOW','REPLAY']


@pytest.mark.parametrize('version,capability,expected',[('2025-11-25',{'form':{}},True),
    ('2025-06-18',{'form':{}},True),('2025-03-26',{'form':{}},False),
    ('2025-11-25',{},False),('2025-11-25',{'url':{}},False)])
def test_form_negotiation_is_explicit(version,capability,expected):
    assert bridge.form_capability({'protocolVersion':version,'capabilities':{'elicitation':capability}})==expected


def test_existing_key_rotation_preserves_ask_evidence_and_cancels_authority(tmp_path,observer):
    from team_runtime import prepare

    from app.transparent import maintenance
    from app.transparent.engine import Engine
    from app.transparent.jev_config import make_policy

    prepare(tmp_path,'synthetic-ask')
    root=tmp_path/'artifacts/team-dev/synthetic-ask'
    grant={'workspace':'/files','tools':{'mcp':['read_file','write_file'],'native':[]},'gate6_resource_rules':RULES}
    def factory(_rules):
        return Engine(root/'control-data/control.sqlite3',(root/'control/storage.key').read_bytes(),grant,
                      policy_router=make_policy(observer))
    engine,_=issue(factory,observer)
    ask=claim(engine)
    presented(engine,ask)
    assert maintenance.rotate(root)['state']=='ROTATED'
    fresh=factory(RULES)
    assert fresh.history()[0]['ask_history'][0]['state']=='CANCELLED'
    with pytest.raises(Rejected):
        answer(fresh,ask)
    with pytest.raises(Rejected):
        fresh.forward('m','w')


def test_ask_retention_removes_context_with_the_existing_session(engine_factory,observer):
    engine,_=issue(engine_factory,observer)
    with engine.db() as db:
        db.execute('UPDATE retention_deadlines SET deadline=0')
    assert engine.history()==[]
    with engine.db() as db:
        assert db.execute('SELECT count(*) FROM asks').fetchone()[0]==0


def test_legacy_confirm_record_is_unchanged_and_cannot_forward(tmp_path,observer):
    from cryptography.fernet import Fernet

    from app.transparent.engine import Engine
    from app.transparent.jev_config import make_policy

    key=Fernet.generate_key()
    grant={'workspace':'/files','tools':{'mcp':['read_file','write_file'],'native':[]}}
    engine=Engine(tmp_path/'legacy.sqlite3',key,grant,policy_router=make_policy(observer))
    engine.turn('m','s','t','Write the draft.','/files')
    engine.register('m','s','t','legacy','write_file',ARGS,'mcp')
    run(engine.authorize('m','legacy'))
    with engine.db() as db:
        db.execute("UPDATE calls SET decision='CONFIRM',state='READY' WHERE id='legacy'")
        previous=dict(db.execute("SELECT * FROM calls WHERE id='legacy'").fetchone())
    fresh=Engine(engine.path,key,grant,policy_router=make_policy(observer))
    assert fresh.history()[0]['ask_history']==[]
    assert fresh.history()[0]['decision']=='CONFIRM'
    with pytest.raises(Rejected,match='LEGACY_CONFIRM_READ_ONLY'):
        fresh.forward('m','legacy')
    with fresh.db() as db:
        assert dict(db.execute("SELECT * FROM calls WHERE id='legacy'").fetchone())==previous
