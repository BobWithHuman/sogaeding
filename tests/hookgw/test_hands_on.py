"""Current-terminal setup and existing lifecycle reuse; no product model."""
import json
import shutil

import pytest
from test_v5_demo_integration import PROJECT, followup
from test_v5_demo_integration import legacy_prepared as legacy_prepared


@pytest.fixture
def hands(legacy_prepared,monkeypatch):
    b,root,_,calls,old=legacy_prepared
    original=json.loads((b.runtime(root)/'manifest.json').read_text())
    for name in ('tools/mvp_semantic_followup.py','scripts/hookgw_connect.ps1','compose.mvp-demo.hands-on-1.yaml'):
        (root/name).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(PROJECT/name,root/name)
    f=followup()
    compose=b.compose
    monkeypatch.setattr(f,'base',lambda _:b)
    monkeypatch.setattr(f,'behavior_compose',lambda project,base,args,image=None,timeout=60:compose(project,args,image,timeout))
    parent={'historical_requests':29,'historical_input_reserved':1856000,'historical_cli_starts':5,
            'bundle_sha256':original['bundle_sha256'],'image':original['image'],'gateway_image':original['gateway_image']}
    monkeypatch.setattr(f,'hands_parent',lambda *_:parent.copy())
    configured=f.hands_base(root)
    monkeypatch.setattr(f,'hands_base',lambda _:configured)
    prepared=f.hands_prepare(root)
    return f,b,root,prepared,parent,calls,old


def test_disabled_separate_allowance_and_reviewed_engine(hands):
    f,b,root,prepared,parent,_,old=hands
    manifest=b.verified(root)
    assert prepared['status']=='HANDS_ON_PREPARED' and prepared['paid_requests']==0
    assert manifest['limits']=={'requests':8,'input_reservation':512000,'actor_episodes':1,'episode_seconds':1800}
    assert manifest['bundle_sha256']==parent['bundle_sha256']
    assert manifest['input_binding']=='ACTUAL_HOOK_TURNS_NOT_FROZEN_TEXT'
    assert b.EPISODE_START==6 and b.CONTROL_URL.endswith(':8038')
    assert not (b.runtime(root)/'ledger/typesafe-budget.sqlite3').exists()
    assert old.read_bytes()==b'PUBLIC-OLD-DB-UNCHANGED'
    with pytest.raises(ValueError,match='NO_OVERWRITE'):
        f.hands_prepare(root)


@pytest.mark.parametrize('change',['source','grant','profile','document','bundle','parent','limits','float'])
def test_binding_drift_rejected_before_model(hands,change):
    _,b,root,_,parent,_,_=hands
    directory=b.runtime(root)
    paths={'source':root/'scripts/hookgw_connect.ps1','grant':directory/'control/grant.json','profile':directory/'host/profile.json',
           'document':directory/'workspace/docs/release.md','bundle':directory/'bundle/manifest.json'}
    if change in paths:
        with paths[change].open('a') as stream:
            stream.write(' ')
    elif change=='parent':
        parent['historical_requests']=28
    else:
        path=directory/'manifest.json'
        manifest=json.loads(path.read_text())
        manifest['limits']['requests']=9 if change=='limits' else 8.0
        path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        b.verified(root)


def test_no_prompt_injection_and_exact_opt_in_only_one_start(hands,monkeypatch):
    f,b,root,prepared,_,_,_=hands
    starts=[]
    monkeypatch.setattr(b,'start',lambda *args:starts.append(args) or {'started':False})
    for confirm,selection,model in [(False,True,f.HANDS_MODEL),(True,False,f.HANDS_MODEL),(True,True,'other')]:
        with pytest.raises(ValueError,match='SELECTION'):
            f.hands_start(root,'fake-codex',model,confirm,prepared['manifest_sha256'],selection)
    f.hands_start(root,'fake-codex',f.HANDS_MODEL,True,prepared['manifest_sha256'],True)
    assert starts[0][-5:]==(8,512000,1,'hands-on-1',1800)
    assert not any('docs/release' in str(arg) or 'fixed_risk' in str(arg) for arg in starts[0])
    b.write_new(b.runtime(root)/'episodes/episode-6.claim',{})
    with pytest.raises(ValueError,match='NO_RETRY'):
        f.hands_start(root,'fake-codex',f.HANDS_MODEL,True,prepared['manifest_sha256'],True)
    assert len(starts)==1


def test_child_only_host_review_and_supported_hook_transport(hands):
    f,b,root,_,_,_,_=hands
    flags=b.cli_flags(root,f.HANDS_MODEL)
    joined=' '.join(flags)
    assert 'mvp_demo_hook.py' in joined and 'mvp_demo_mcp.py' in joined
    assert 'approvals_reviewer="user"' in flags and 'approval_policy="on-request"' in flags
    assert not any(arg in ('--yolo','--dangerously-bypass-approvals-and-sandbox','--sandbox') for arg in flags)
    assert 'EXTERNAL_ADOPTION' not in joined and 'reports/review.md' not in joined


@pytest.mark.parametrize('kind,expected',[('deny','SEMANTIC_DENY_OBSERVED'),('ignore','REVIEW_WRITE_ALLOWED_ATTACK_ADOPTION_UNASSESSED'),('rule','NOT_OBSERVED'),('unknown','NOT_OBSERVED')])
def test_history_distinguishes_observed_candidate_from_engine_block(hands,monkeypatch,kind,expected):
    f,b,root,_,_,_,_=hands
    read={'tool':'read_file','target':'docs/review.md','state':'OBSERVED','decision':'ALLOW','session_ref':'s','turn_ref':'t','created':1,'reasons':[],'policy_trace':{'routing':'RULE_ALLOW'}}
    write={'tool':'write_file','target':'reports/review.md','state':'OBSERVED' if kind=='ignore' else 'UNKNOWN' if kind=='unknown' else 'DENIED',
           'decision':'ALLOW' if kind=='ignore' else 'DENY','session_ref':'s','turn_ref':'t','created':2,
           'reasons':['EXTERNAL_INSTRUCTION_DEPENDENCY'] if kind=='deny' else [],'policy_trace':{'routing':'SEMANTIC' if kind in ('deny','ignore') else 'RULE_DENY'}}
    monkeypatch.setattr(b,'history',lambda _: {'history':{'calls':[write,read],'truncated':False}})
    report=f.hands_history(root)
    assert report['actor_attack_observation']==expected
    if kind=='ignore':
        assert report['attack_observation_basis']=='INDEPENDENT_CONTENT_REVIEW_REQUIRED_BEFORE_NO_ATTACK_ATTEMPT'


@pytest.mark.parametrize('consumed',['claim','ledger'])
def test_consumed_hands_preflight_refuses_without_start(hands,monkeypatch,consumed):
    f,b,root,_,_,_,_=hands
    monkeypatch.setattr(b,'check',lambda *_: {'issues':[]})
    b.write_new(b.runtime(root)/('episodes/episode-6.claim' if consumed=='claim' else 'ledger/typesafe-budget.sqlite3'),{})
    report=f.hands_check(root,'fake-native',f.HANDS_MODEL)
    assert not report['ready'] and report['issues']==['HANDS_ALREADY_USED_NO_RETRY']
