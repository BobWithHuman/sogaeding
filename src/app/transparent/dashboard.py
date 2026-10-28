"""Read-only dashboard projection. Never return prompts, payloads or ASK nonces."""
import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from cryptography.fernet import InvalidToken
from fastapi import Request
from fastapi.responses import JSONResponse

from app.common import SafeError, canonical, digest, mask, strict_json
from app.transparent.privacy import PrivacyError, TransmissionMasker

DECISIONS = ('ALLOW','DENY','ASK','UNKNOWN')
OUTCOMES = ('SUCCEEDED','REPORTED_ERROR','NOT_EXECUTED','IN_PROGRESS','UNKNOWN')
ASKS = ('ISSUED','PRESENTED','ANSWER_RECEIVED','RECHECKED','DECLINED','EXPIRED','CANCELLED')
ORIGINS = ('STRUCTURAL_RULE','JEV_SEMANTIC','USER_DECLINED','ANALYSIS_FAILURE','OTHER','UNATTRIBUTED')
FILTERS = {'session_id','agent','tool','initial_decision','decision','execution_outcome','denial_origin','reason_code','routing'}
MASKER = TransmissionMasker(secrets.token_bytes(32))


class DashboardError(ValueError):
    def __init__(self, code='INVALID_FILTER', status=400):
        self.code, self.status = code, status


def stamp(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value,UTC).isoformat().replace('+00:00','Z')


def code(value, default='UNKNOWN'):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',value) else default


def display(value, limit=160):
    if not isinstance(value,str):
        return None
    try:
        return MASKER.text(mask(value),'dashboard-display')[:limit]
    except PrivacyError:
        return '[비공개]'


def query(request, *, security=False):
    pairs = list(request.query_params.multi_items())
    q = dict(pairs)
    allowed = {'from','to','timezone','limit','cursor','bucket'} | ({'kind','alert_code'} if security else FILTERS)
    if len(q) != len(pairs) or set(q)-allowed:
        raise DashboardError()
    try:
        start, end = (datetime.fromisoformat(q[name].replace('Z','+00:00')) for name in ('from','to'))
        if start.tzinfo is None or end.tzinfo is None or not 0 < (end-start).total_seconds() <= 604800:
            raise ValueError()
        if q.get('timezone','Asia/Seoul') not in ('Asia/Seoul','UTC') or q.get('bucket','hour') not in ('hour','day'):
            raise ValueError()
        limit = int(q.get('limit','50'))
        if not 1 <= limit <= 100 or any(len(v)>2048 for v in q.values()):
            raise ValueError()
    except (ValueError,KeyError,TypeError,OverflowError):
        raise DashboardError() from None
    return q, start.timestamp(), end.timestamp(), limit


def outcome(state):
    if state == 'OBSERVED':
        return 'SUCCEEDED'
    if state == 'OBSERVED_ERROR':
        return 'REPORTED_ERROR'
    if state in ('UNKNOWN','EXECUTING'):
        return 'UNKNOWN' if state == 'UNKNOWN' else 'IN_PROGRESS'
    if state in ('ANALYZING','PENDING','READY','APPROVED'):
        return 'IN_PROGRESS'
    return 'NOT_EXECUTED'


def execution_projection(engine, db, row, tool):
    """Read typed exit status from the bound trusted transport, never tool text claims.

    OBSERVED records delivery, including an npm process reporting nonzero exit.
    Only the exit code leaves this projection; stdout/stderr remain private.
    """
    result={'outcome':outcome(row['state'])}
    if tool!='run_npm_install' or row['state']!='OBSERVED':
        return result
    result['outcome']='UNKNOWN'
    transport=db.execute('SELECT body FROM transport WHERE call=?',(row['id'],)).fetchone()
    if transport is None:
        return result
    try:
        wire=engine.open(transport[0])
        if not isinstance(wire,dict):
            return result
        blocks=wire.get('content')
        if (wire.get('isError') or not isinstance(blocks,list) or len(blocks)!=1
                or not isinstance(blocks[0],dict) or blocks[0].get('type')!='text'):
            return result
        value=strict_json(blocks[0]['text'])
        exit_code=value['exit_code']
        if type(exit_code) is not int or not -(2**31)<=exit_code<2**31:
            return result
    except (ValueError,TypeError,KeyError,IndexError,InvalidToken,SafeError):
        return result
    return {'outcome':'SUCCEEDED' if exit_code==0 else 'REPORTED_ERROR','exit_code':exit_code}


def origin(decision, reasons, routing, asks):
    if decision != 'DENY':
        return None
    if any(a['state']=='DECLINED' for a in asks):
        return 'USER_DECLINED'
    if routing=='ANALYSIS_FAILED' or any('UNAVAILABLE' in r or 'BUDGET' in r or 'ANALYSIS_STOP' in r for r in reasons):
        return 'ANALYSIS_FAILURE'
    if routing=='RULE_DENY' or routing=='UNKNOWN' and reasons:
        return 'STRUCTURAL_RULE'
    if routing=='SEMANTIC':
        return 'JEV_SEMANTIC'
    return 'UNATTRIBUTED'


class Projection:
    def __init__(self, engine, machine):
        self.engine, self.machine = engine, machine
        self.cursor_key = secrets.token_bytes(32)

    def events(self, start, end):
        e = self.engine
        with e.db() as db:
            # Exclude expired raw context even before the periodic purge executes.
            rows = db.execute('''SELECT c.* FROM calls c JOIN sessions s ON s.id=c.session
                JOIN retention_deadlines r ON r.session=c.session
                WHERE s.machine=? AND c.created>=? AND c.created<? AND r.deadline>?
                ORDER BY c.created DESC,c.id DESC LIMIT 20001''',(self.machine,start,end,time.time())).fetchall()
            if len(rows)>20000:
                raise DashboardError('QUERY_LIMIT',503)
            result=[]
            for row in rows:
                ctx=e.read_reason(row['reason']) if row['reason'] else {}
                body=e.open(row['body'])
                trace=ctx.get('policy_trace') or {}
                routing=trace.get('routing') if trace.get('routing') in ('RULE_ALLOW','RULE_DENY','SEMANTIC','ANALYSIS_FAILED') else 'UNKNOWN'
                reasons=[code(r) for r in ctx.get('reasons',[])[:8]]
                asks=[]
                for a in e.ask_history(db,row['id']):
                    asks.append({k:(stamp(v) if k.endswith('_at') and isinstance(v,(int,float)) else display(v) if k in ('question_redacted','answer_summary') else v)
                                 for k,v in a.items() if k in {'ask_id','state','question_redacted','answer_summary','issued_at','presented_at','answered_at','resolved_at','expires_at','outcome','terminal_reason','hold_reasons','reason_details'}})
                audits=db.execute('SELECT at,kind,code FROM audit WHERE call=? ORDER BY at,id LIMIT 200',(row['id'],)).fetchall()
                times=[row['created'],*[a['at'] for a in audits]]
                for a in asks:
                    times.extend(datetime.fromisoformat(v.replace('Z','+00:00')).timestamp() for k,v in a.items() if k in ('issued_at','presented_at','answered_at','resolved_at') and isinstance(v,str))
                decision=row['decision'] if row['decision'] in DECISIONS else 'UNKNOWN'
                args=body.get('args',{})
                execution=execution_projection(e,db,row,body.get('tool'))
                # Agent identity is not recorded by the current trusted connector.
                # Never guess it from a session name or from model/tool arguments.
                item={'event_id':digest(row['id']),'call_id':digest(row['id']),'session_id':digest(row['session']),
                      'turn_id':digest(row['turn']),'created_at':stamp(row['created']),'updated_at':stamp(max(times)),
                      'agent':'unknown','tool':code(body.get('tool')),'target_display':display(args.get('path')),
                      'initial_decision':'ASK' if asks else decision,'decision':decision,'engine_state':code(row['state']),
                      'execution':{**execution,
                                   'started_at':next((stamp(a['at']) for a in audits if a['kind']=='EXECUTE'),None),
                                   'observed_at':stamp(max(times)) if row['state'] in ('OBSERVED','OBSERVED_ERROR') else None},
                      'routing':routing,'denial_origin':origin(decision,reasons,routing,asks),
                      'reasons':[{'code':r,'label':r} for r in reasons], 'policy':code(ctx.get('policy'),self.engine.policy),
                      'ask':{k:asks[-1].get(k) for k in ('ask_id','state','outcome')} if asks else None,
                      'redacted':True,'context_status':'AVAILABLE_REDACTED',
                      'user_request_summary':'[원문 요청 비공개]',
                      'candidate_summary':{'action':{'write_file':'write','edit_project_file':'write','read_file':'read','read_project_file':'read','read_github_issue':'read','run_npm_install':'execute'}.get(body.get('tool'),'unknown'),
                          'target':display(args.get('path')),'arguments_redacted':{'path':display(args.get('path')),**{key:'[본문 비공개]' for key in ('content','old_text','new_text') if key in args}}},
                      'sources':[], 'checks':[{'name':'JEV_'+v,'result':'COMPLETED' if (ctx.get('view_checks',{}).get(v) or {}).get('status')=='VALID' else 'NOT_RUN' if (ctx.get('view_checks',{}).get(v) or {}).get('status') in (None,'NOT_RUN','NOT_RUN_RULE') else 'UNKNOWN'} for v in ('A','B')],
                      'ask_history':asks,
                      'timeline':[{'at':stamp(row['created']),'type':'CANDIDATE_REGISTERED','label':'실행 후보 등록'},
                                  *[{'at':stamp(a['at']),'type':code(a['kind'])+'_'+code(a['code']),'label':code(a['kind'])+' / '+code(a['code'])} for a in audits]]}
                for source in db.execute('''SELECT s.id FROM sources s JOIN calls c ON c.id=s.call
                        WHERE s.session=? AND c.created<=? LIMIT 64''',(row['session'],row['created'])):
                    # No raw source or tool result is read into the browser DTO.
                    item['sources'].append({'source_id':digest(source['id']),'label':'서버 관측 자료','origin':'TOOL_OBSERVATION','integrity':'UNKNOWN','completeness':'UNKNOWN','excerpt_redacted':None})
                result.append(item)
        return sorted(result,key=lambda i:(i['created_at'],i['event_id']),reverse=True)

    @staticmethod
    def filtered(items,q):
        def matches(i):
            for name in FILTERS:
                if not q.get(name):
                    continue
                value=i['execution']['outcome'] if name=='execution_outcome' else [r['code'] for r in i['reasons']] if name=='reason_code' else i.get(name)
                if q[name] not in value if isinstance(value,list) else q[name]!=value:
                    return False
            return True
        return [i for i in items if matches(i)]

    def page(self,items,q,limit, *, kind='events'):
        binding=digest(canonical({k:v for k,v in q.items() if k not in ('cursor','limit')} )+kind)
        if q.get('cursor'):
            try:
                token,sig=q['cursor'].split('.')
                if not hmac.compare_digest(hmac.new(self.cursor_key,token.encode(),hashlib.sha256).hexdigest(),sig):
                    raise ValueError()
                cursor=json.loads(base64.urlsafe_b64decode(token+'='*((-len(token))%4)))
                if cursor['binding']!=binding:
                    raise ValueError()
                items=[i for i in items if (i['created_at'],str(i['event_id']))<tuple(cursor['after'])]
            except (ValueError,KeyError,TypeError):
                raise DashboardError() from None
        selected=items[:limit]
        cursor=None
        if len(items)>limit:
            last=selected[-1]
            token=base64.urlsafe_b64encode(canonical({'binding':binding,'after':[last['created_at'],str(last['event_id'])]}).encode()).decode().rstrip('=')
            cursor=token+'.'+hmac.new(self.cursor_key,token.encode(),hashlib.sha256).hexdigest()
        return selected,cursor

    def ledger(self):
        empty={k:None for k in ('requests','input_tokens_actual','output_tokens_actual','input_tokens_reserved','request_limit','requests_remaining','input_reservation_limit','input_reservation_remaining')}
        value={**empty,'scope':'RUNTIME_LEDGER','status':'UNAVAILABLE'}
        settings=getattr(getattr(self.engine.policy_router,'client',None),'settings',None)
        value.update(unlimited=getattr(settings,'unlimited',False),
                     request_limit=getattr(settings,'request_limit',None),
                     input_reservation_limit=getattr(settings,'input_token_limit',None))
        path=getattr(settings,'budget_path',None)
        if path is None or Path(path).is_symlink() or not Path(path).is_file():
            return value
        try:
            with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=1) as db:
                rows=db.execute('SELECT input_reserved,usage FROM jev_attempts').fetchall()
            value.update(requests=len(rows),input_tokens_reserved=sum(r[0] for r in rows),request_limit=settings.request_limit,
                         requests_remaining=None if settings.request_limit is None else max(0,settings.request_limit-len(rows)),input_reservation_limit=settings.input_token_limit,
                         input_reservation_remaining=None if settings.input_token_limit is None else max(0,settings.input_token_limit-sum(r[0] for r in rows)),
                         unlimited=getattr(settings,'unlimited',False),status='AVAILABLE')
            usage=[json.loads(r[1]) if r[1] else {} for r in rows]
            for name in ('input_tokens','output_tokens'):
                if rows and all(type(u.get(name)) is int and u[name]>=0 for u in usage):
                    value[name+'_actual']=sum(u[name] for u in usage)
        except (sqlite3.Error,ValueError,TypeError):
            return {**empty,'scope':'RUNTIME_LEDGER','status':'UNAVAILABLE'}
        return value

    def summary(self,items,q,start,end):
        def counts(values,labels):
            c=Counter(values)
            return {k:c[k] for k in labels}
        ask=[a for i in items for a in i['ask_history']]
        zone=timezone(timedelta(hours=9)) if q.get('timezone','Asia/Seoul')=='Asia/Seoul' else UTC
        groups={}
        for item in items:
            d=datetime.fromisoformat(item['created_at'].replace('Z','+00:00')).astimezone(zone)
            d=d.replace(minute=0,second=0,microsecond=0,**({'hour':0} if q.get('bucket')=='day' else {}))
            groups.setdefault(d.timestamp(),[]).append(item)
        return {'scope':'FILTERED_RETAINED_CALLS','generated_at':stamp(),'range':{'from':stamp(start),'to':stamp(end),'timezone':q.get('timezone','Asia/Seoul')},
                'total_calls':len(items),'initial_decisions':counts((i['initial_decision'] for i in items),DECISIONS),
                'effective_decisions':counts((i['decision'] for i in items),DECISIONS),
                'execution_outcomes':counts((i['execution']['outcome'] for i in items),OUTCOMES),
                'asks':{'total_requests':len(ask),**counts((a['state'] for a in ask),ASKS)},
                'denials':counts((i['denial_origin'] for i in items),ORIGINS),'jev':self.ledger(),
                'series':[{'bucket_start':stamp(at),'total_calls':len(values),**{'initial_'+k:v for k,v in counts((i['initial_decision'] for i in values),DECISIONS).items()}} for at,values in sorted(groups.items())],
                'reasons':[{'code':k,'count':v} for k,v in Counter(r['code'] for i in items for r in i['reasons']).most_common()]}


def register(app,engine,machine,auth):
    projection=Projection(engine,machine)

    @app.exception_handler(DashboardError)
    async def invalid(_req,exc):
        return JSONResponse({'error':{'code':exc.code,'message':exc.code,'retryable':exc.status>=500}},status_code=exc.status)

    @app.get('/dashboard/v1/status')
    async def status(request: Request):
        auth(request,'human','history:read')
        client=getattr(engine.policy_router,'client',None)
        settings=getattr(client,'settings',None)
        authorized=settings is not None and settings.authorized()
        with engine.db() as db:
            row=db.execute('''SELECT min(c.created),max(c.created) FROM calls c JOIN sessions s ON s.id=c.session
                JOIN retention_deadlines r ON r.session=c.session WHERE s.machine=? AND r.deadline>?''',(machine,time.time())).fetchone()
        return {'contract_version':'dashboard-v1','observed_at':stamp(),'data_mode':'ENGINE_FIXTURE' if getattr(client,'is_fixture',False) else 'ENGINE',
                'engine':{'state':'ONLINE','policy':engine.policy,'decision_contract':'ASK_V1'},
                'services':{'gateway':'UNKNOWN','upstream':'UNKNOWN','jev':'CONFIGURED_NOT_TESTED' if authorized else 'DISABLED'},
                'capabilities':{'ask_history':True,'security_events':True,'alert_ack':False,'raw_context':False},
                'retention':{'session_seconds':engine.retention.session_seconds,'history_seconds':engine.retention.history_seconds,'security_seconds':604800},
                'data_window':{'earliest_available_at':stamp(row[0]) if row[0] is not None else None,'latest_available_at':stamp(row[1]) if row[1] is not None else None}}

    @app.get('/dashboard/v1/summary')
    async def summary(request: Request):
        auth(request,'human','history:read')
        q,start,end,_=query(request)
        return projection.summary(projection.filtered(projection.events(start,end),q),q,start,end)

    @app.get('/dashboard/v1/events')
    async def events(request: Request):
        auth(request,'human','history:read')
        q,start,end,limit=query(request)
        items=projection.filtered(projection.events(start,end),q)
        selected,cursor=projection.page(items,q,limit)
        # Details remain available on the detail route; no source/payload in lists.
        public=[{k:v for k,v in i.items() if k not in ('sources','checks','timeline','user_request_summary','candidate_summary','ask_history')} for i in selected]
        return {'scope':'FILTERED_RETAINED_CALLS','generated_at':stamp(),'total':len(items),'items':public,'next_cursor':cursor}

    @app.get('/dashboard/v1/events/{event_id}')
    async def detail(event_id:str,request: Request):
        auth(request,'human','history:read')
        if not re.fullmatch(r'[a-f0-9]{64}',event_id):
            raise DashboardError('EVENT_NOT_FOUND',404)
        return next((i for i in projection.events(time.time()-604800,time.time()+1) if i['event_id']==event_id),None) or missing()

    @app.get('/dashboard/v1/security')
    async def security(request: Request):
        auth(request,'human','security:read')
        q,start,end,limit=query(request,security=True)
        with engine.db() as db:
            rows=db.execute('SELECT * FROM security_events WHERE at>=? AND at<? AND at>? ORDER BY at DESC,id DESC',(start,end,time.time()-604800)).fetchall()
            items=[]
            for row in rows:
                value=engine.open(row['body'])
                if (value['at'],value['kind'],value['result'])!=(row['at'],row['kind'],row['result']):
                    raise DashboardError('SECURITY_RECORD_INVALID',503)
                if q.get('kind') and q['kind']!=value['kind']:
                    continue
                items.append({'id':row['id'],'event_id':str(row['id']),'created_at':stamp(row['at']),'at':stamp(row['at']),
                              'kind':code(value['kind']),'actor_hash':code(value['actor_hash']),'resource_hash':code(value['resource_hash']),'result':code(value['result'])})
            alerts=[{'id':r['id'],'at':stamp(r['at']),'code':code(r['code']),'severity':'INFO' if r['code']=='CREDENTIALS_ROTATED' else 'WARNING',
                     'event_id':r['event'],'acknowledged':bool(r['acknowledged'])} for r in db.execute('SELECT * FROM security_alerts WHERE at>=? AND at<? AND at>? ORDER BY at DESC,id DESC LIMIT 512',(start,end,time.time()-604800)) if not q.get('alert_code') or r['code']==q['alert_code']]
            if q.get('alert_code'):
                related={a['event_id'] for a in alerts}
                items=[i for i in items if i['id'] in related]
        items.sort(key=lambda i:(i['created_at'],i['event_id']),reverse=True)
        selected,cursor=projection.page(items,q,limit,kind='security')
        return {'scope':'FILTERED_RETAINED_SECURITY_EVENTS','generated_at':stamp(),'total':len(items),'items':selected,'alerts':alerts,'next_cursor':cursor}


def missing():
    raise DashboardError('EVENT_NOT_FOUND',404)
