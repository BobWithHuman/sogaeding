"""Dashboard contract and privacy tests; synthetic engine, no model requests."""
import asyncio
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.common import digest
from app.dashboard_local import create_app as relay_app
from app.transparent.server import create_app, public_app

KEYS={'machine_id':'m','machine':'synthetic-machine','human':'synthetic-human','ticket':lambda *_:'not-used'}


def interval():
    end=datetime.now(UTC)+timedelta(seconds=5)
    return {'from':(end-timedelta(hours=24)).isoformat(),'to':end.isoformat()}


def get(app,path,params=None,token=KEYS['human']):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://control') as c:
            return await c.get(path,params=params,headers={'Authorization':'Bearer '+token} if token else {})
    return asyncio.run(send())


def populate(engine,count=3):
    engine.turn('m','session-private','t','PRIVATE_PROMPT_CANARY','/files')
    for i in range(count):
        engine.register('m','session-private','t',str(i),'write_file',{'path':'reports/a.md','content':'PRIVATE_PAYLOAD_CANARY'},'mcp')


def test_summary_counts_entire_range_not_current_page_and_redacts_detail(engine):
    populate(engine,121)
    engine.turn('other-machine','other-session','t','CROSS_MACHINE_CANARY','/files')
    engine.register('other-machine','other-session','t','other','read_file',{'path':'docs/hidden.md'},'mcp')
    app=public_app(create_app(engine,KEYS))
    q=interval()
    summary=get(app,'/dashboard/v1/summary',q)
    assert summary.status_code==200 and summary.json()['total_calls']==121
    first=get(app,'/dashboard/v1/events',{**q,'limit':50}).json()
    assert first['total']==121 and len(first['items'])==50 and first['next_cursor']
    second=get(app,'/dashboard/v1/events',{**q,'limit':50,'cursor':first['next_cursor']}).json()
    assert not {i['event_id'] for i in first['items']} & {i['event_id'] for i in second['items']}
    detail=get(app,'/dashboard/v1/events/'+first['items'][0]['event_id'])
    assert detail.status_code==200
    assert all(s not in detail.text for s in ('PRIVATE_PROMPT_CANARY','PRIVATE_PAYLOAD_CANARY','CROSS_MACHINE_CANARY','synthetic-human'))
    assert detail.json()['agent']=='unknown'
    assert detail.json()['execution']['outcome']=='IN_PROGRESS'
    assert get(app,'/dashboard/v1/events/'+digest('other')).status_code==404


@pytest.mark.parametrize('changes',[{'limit':0},{'limit':101},{'from':'bad'},{'timezone':'untrusted'}, {'from':'2020-01-01T00:00:00Z'}, {'unsupported':'yes'}])
def test_invalid_filters_do_not_become_unfiltered_query(engine,changes):
    app=public_app(create_app(engine,KEYS))
    assert get(app,'/dashboard/v1/events',{**interval(),**changes}).status_code==400


def test_cursor_is_bound_to_filters_and_rejects_tampering(engine):
    populate(engine)
    app=public_app(create_app(engine,KEYS))
    q=interval()
    cursor=get(app,'/dashboard/v1/events',{**q,'limit':1}).json()['next_cursor']
    assert get(app,'/dashboard/v1/events',{**q,'limit':1,'cursor':cursor+'x'}).status_code==400
    assert get(app,'/dashboard/v1/events',{**q,'limit':1,'decision':'DENY','cursor':cursor}).status_code==400


def test_expired_context_is_excluded_even_before_purge(engine):
    populate(engine)
    with engine.db() as db:
        db.execute('UPDATE retention_deadlines SET deadline=?',(time.time()-1,))
    app=public_app(create_app(engine,KEYS))
    assert get(app,'/dashboard/v1/summary',interval()).json()['total_calls']==0
    assert get(app,'/dashboard/v1/events/'+digest('0')).status_code==404


def test_machine_and_invalid_token_cannot_read_dashboard(engine):
    app=public_app(create_app(engine,KEYS))
    for token in (None,'wrong-token',KEYS['machine']):
        assert get(app,'/dashboard/v1/status',token=token).status_code==403
    state=get(app,'/dashboard/v1/status').json()
    assert state['services']['gateway']=='UNKNOWN' and state['services']['upstream']=='UNKNOWN'
    assert state['capabilities']['raw_context'] is False


def test_real_ask_projection_contains_no_nonce(engine_factory,observer):
    from test_ask import claim, issue
    engine,_=issue(engine_factory,observer)
    pending=claim(engine)
    app=public_app(create_app(engine,KEYS))
    summary=get(app,'/dashboard/v1/summary',interval()).json()
    assert summary['initial_decisions']['ASK']==1 and summary['asks']['ISSUED']==1
    detail=get(app,'/dashboard/v1/events/'+digest('w'))
    assert detail.status_code==200 and pending['nonce'] not in detail.text


def test_bff_session_origin_read_only_proxy_and_token_stays_server_side(engine):
    upstream=public_app(create_app(engine,KEYS))
    app=relay_app('https://control',KEYS['human'],transport=httpx.ASGITransport(app=upstream))
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1:8150') as c:
            assert (await c.get('/dashboard/v1/status')).status_code==401
            page=await c.get('/')
            assert page.status_code==200 and 'HttpOnly' in page.headers['set-cookie']
            response=await c.get('/dashboard/v1/status')
            assert response.status_code==200 and KEYS['human'] not in response.text
            assert (await c.get('/dashboard/v1/status',headers={'Origin':'https://attacker.invalid'})).status_code==403
            assert (await c.get('/dashboard/v1/approval')).status_code==404
            assert (await c.post('/dashboard/v1/events')).status_code==405
    asyncio.run(send())
