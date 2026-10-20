"""Preserved failed attempt and RO history. TLS end-to-end lives in artifacts."""
import json
import sqlite3

import pytest
from test_core_auto_runner import core as core
from test_core_auto_runner import normal_calls
from test_v5_demo_integration import legacy_prepared as legacy_prepared


@pytest.fixture
def failed(core,monkeypatch):
    f,b,root,directory,approvals,_,_=core
    normal_calls(core,True)
    normal=f.core_normal_gate(root,b)
    manifest=json.loads((directory/'manifest.json').read_text())
    monkeypatch.setattr(f,'CORE_ORIGINAL_SHA',b.sha(directory/'manifest.json'))
    monkeypatch.setattr(f,'core_post_allowed',lambda:{name:manifest['source_hashes'][name] for name in (*f.CORE_RUNNER_BEFORE,'tools/mvp_demo_probe.py')})
    with sqlite3.connect(directory/'control-data/control.sqlite3') as db,sqlite3.connect(directory/'upstream-data/attempts.sqlite3') as upstream:
        db.execute('CREATE TABLE sources (call TEXT)')
        db.execute('CREATE TABLE transport (call TEXT)')
        db.executemany('INSERT INTO sources VALUES (?)', [('0',),('2',),('3',)])
        db.executemany('INSERT INTO transport VALUES (?)', [(str(n),) for n in range(4)])
        db.execute("INSERT INTO turns VALUES ('core-fixed-risk-engine','risk-turn','fixture')")
        spec=f.core_risk_spec(root,b)
        for suffix,state,decision,candidate,reasons,index in (
            ('read','UNKNOWN','ALLOW',{'route':'mcp','tool':'read_file','args':{'path':spec['source_path']}},['PUBLIC_ENROLLED_READ'],10),
            ('write','DENIED','DENY',spec['candidate'],['PRIOR_RESULT_UNOBSERVED'],12)):
            ident='core-fixed-risk-engine:risk-'+suffix
            reason=json.dumps({'policy':b.DECISION_POLICY,'reasons':reasons})
            db.execute("INSERT INTO calls VALUES (?,'core-fixed-risk-engine','risk-turn',?,'mcp',?,?,?,?)",(ident,f.core_digest(candidate),state,decision,reason,index))
        ident='core-fixed-risk-engine:risk-read'
        db.execute('INSERT INTO transport VALUES (?)',(ident,))
        db.execute('INSERT INTO demo_rpc_bindings VALUES (?,?)',(ident,'a'*64))
        upstream.execute("INSERT INTO attempts VALUES (?,?,'OBSERVED',11)",(ident,'b'*64))
    (directory/f.CORE_RESUME_FILE).write_text('{"previous":true}')
    monkeypatch.setattr(f,'CORE_PREVIOUS_RESUME_SHA',b.sha(directory/f.CORE_RESUME_FILE))
    b.write_new(directory/'verify-block.claim',{'consumed':True})
    b.write_new(directory/'verify-block-result.json',{'status':'NOT_VERIFIED_OR_UNKNOWN_STOP','normal':normal})
    rows=f.core_rows(b,directory,'control-data/control.sqlite3','SELECT id,session,turn,path,state,decision,created,reason FROM calls ORDER BY created,rowid')
    for row in rows:
        context=json.loads(row.pop('reason'))
        row.update(reasons=context.get('reasons'),execution_error=context.get('execution_error'))
    evidence={'calls':rows,'upstream':f.core_rows(b,directory,'upstream-data/attempts.sqlite3','SELECT call,state,at FROM attempts ORDER BY at,rowid'),
        'transport_call_ids':sorted(row['call'] for row in f.core_rows(b,directory,'control-data/control.sqlite3','SELECT call FROM transport')),
        'source_call_ids':['0','2','3'],'risk_claim_sha256':b.sha(directory/'verify-block.claim'),'risk_result_sha256':b.sha(directory/'verify-block-result.json')}
    path=root/f.CORE_FAILURE_EVIDENCE
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(evidence))
    monkeypatch.setattr(f,'CORE_FAILURE_EVIDENCE_SHA',b.sha(path))
    prepared=f.core_post_prepare(root)
    approvals.update(risk_attempt=f.CORE_POST_ATTEMPT,attempt_manifest_sha256=prepared['attempt_manifest_sha256'])
    return core,prepared


def test_original_six_calls_and_unused_pair_bind_to_separate_attempt(failed):
    (f,b,root,directory,_,_,sent),prepared=failed
    _,record=f.core_post_bound(root,b,prepared['attempt_manifest_sha256'],True)
    assert record['normal']['calls']==4 and record['remaining_requests']==2
    assert not sent and not (directory/'verify-block-post-complete-1.claim').exists()
    assert json.loads((directory/'verify-block-result.json').read_text())['status']=='NOT_VERIFIED_OR_UNKNOWN_STOP'


@pytest.mark.parametrize('change',['unknown_promoted','missing_call','extra_call','upstream_write','missing_transport','fake_source','old_claim','old_result','normal','ledger','new_claim','source','bundle','attempt_hash'])
def test_changed_failed_evidence_never_claims_or_sends(failed,change):
    (f,_,root,directory,approvals,usage,sent),_=failed
    with sqlite3.connect(directory/'control-data/control.sqlite3') as db,sqlite3.connect(directory/'upstream-data/attempts.sqlite3') as upstream:
        if change=='unknown_promoted':
            db.execute("UPDATE calls SET state='OBSERVED' WHERE state='UNKNOWN'")
        elif change=='missing_call':
            db.execute("DELETE FROM calls WHERE id='core-fixed-risk-engine:risk-write'")
        elif change=='extra_call':
            db.execute("INSERT INTO calls SELECT 'extra',session,turn,hash,path,state,decision,reason,created+1 FROM calls LIMIT 1")
        elif change=='upstream_write':
            upstream.execute("INSERT INTO attempts VALUES ('core-fixed-risk-engine:risk-write',?,'OBSERVED',20)",('c'*64,))
        elif change=='missing_transport':
            db.execute("DELETE FROM transport WHERE call='core-fixed-risk-engine:risk-read'")
        elif change=='fake_source':
            db.execute("INSERT INTO sources VALUES ('core-fixed-risk-engine:risk-read')")
    files={'old_claim':'verify-block.claim','old_result':'verify-block-result.json','normal':'workspace/reports/normal.md','bundle':'bundle/manifest.json'}
    if change in files:
        with (directory/files[change]).open('a') as stream:
            stream.write(' ')
    elif change=='ledger':
        usage['requests_attempted']=3
    elif change=='new_claim':
        (directory/'verify-block-post-complete-1.claim').write_text('{}')
    elif change=='source':
        with (root/'src/app/fake.py').open('a') as stream:
            stream.write(' ')
    elif change=='attempt_hash':
        approvals['attempt_manifest_sha256']='0'*64
    with pytest.raises((ValueError,OSError)):
        f.core_verify_block(root,**approvals)
    assert not sent
    assert (directory/'verify-block-post-complete-1.claim').exists()==(change=='new_claim')


def test_historical_collection_uses_no_execution_compose_or_source_gate(core,monkeypatch):
    f,b,root,directory,_,_,_=core
    path=directory/'episodes/events/episode-5/finish.json'
    value=json.loads(path.read_text())
    value.update(event='FINISHED',episode=5)
    path.write_text(json.dumps(value))
    with (root/'tools/mvp_demo.py').open('a') as stream:
        stream.write('\n')
    def forbidden(*args,**kw):
        raise AssertionError('history invoked execution transport')
    monkeypatch.setattr(b,'compose',forbidden)
    monkeypatch.setattr(b,'command',forbidden)
    report=f.behavior_history(root,True)
    assert report['current_source_matches_frozen_run'] is False and report['upstream']['attempts']==2
