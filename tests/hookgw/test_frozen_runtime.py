"""Continuation launcher boundaries, with no actor or network."""
import shutil

import pytest
from test_v5_demo_integration import PROJECT, followup
from test_v5_demo_integration import legacy_prepared as legacy_prepared


@pytest.fixture
def frozen(legacy_prepared,monkeypatch):
    b,root,_,calls,old=legacy_prepared
    for name in ('tools/mvp_semantic_followup.py','scripts/hookgw_connect.ps1','compose.mvp-demo.hands-on-1.yaml','compose.mvp-demo.frozen-demo-1.yaml'):
        (root/name).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(PROJECT/name,root/name)
    shutil.copytree(PROJECT/'artifacts/management-frozen-demo-20261017',root/'artifacts/management-frozen-demo-20261017')
    f=followup()
    compose=b.compose
    monkeypatch.setattr(f,'base',lambda _:b)
    monkeypatch.setattr(f,'behavior_compose',lambda project,base,args,image=None,timeout=60:compose(project,args,image,timeout))
    parent={'historical_requests':33,'bundle_sha256':'OLD_REVIEWED_BUNDLE'}
    monkeypatch.setattr(f,'frozen_parent',lambda *_:parent.copy())
    configured=f.frozen_base(root)
    monkeypatch.setattr(f,'frozen_base',lambda _:configured)
    report=f.frozen_prepare(root)
    return f,b,root,report,parent,calls,old


def test_disabled_original_shared_budget_and_new_cli_only(frozen):
    f,b,root,report,_,_,old=frozen
    m=b.verified(root)
    assert report['paid_requests']==0 and m['limits']['requests']==4 and b.EPISODE_START==7
    assert b.policy(False)=={'enabled':False,'model':'jev-1.13.0','request_limit':8,'input_token_limit':512000,'policy_id':'mvp-demo-hands-on-1'}
    assert m['shared_budget']['runtime'].endswith('hands-on-1/ledger/typesafe-budget.sqlite3')
    assert not (b.runtime(root)/'ledger/typesafe-budget.sqlite3').exists()
    assert old.read_bytes()==b'PUBLIC-OLD-DB-UNCHANGED'
    with pytest.raises(ValueError,match='NO_OVERWRITE'):
        f.frozen_prepare(root)


@pytest.mark.parametrize('change',['source','grant','profile','document','bundle','parent','limit','shared_ownership'])
def test_frozen_drift_never_claims_or_starts(frozen,change):
    _,b,root,_,parent,_,_=frozen
    directory=b.runtime(root)
    paths={'source':root/'scripts/hookgw_connect.ps1','grant':directory/'control/grant.json','profile':directory/'host/profile.json','document':directory/'workspace/docs/review.md','bundle':directory/'bundle/manifest.json'}
    if change in paths:
        with paths[change].open('a') as file:
            file.write(' ')
    elif change=='parent':
        parent['historical_requests']=32
    else:
        import json
        m=json.loads((directory/'manifest.json').read_text())
        if change=='limit':
            m['limits']['requests']=8
        else:
            m['shared_budget']['policy_id']='new-budget'
        (directory/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):
        b.verified(root)
    assert not list((directory/'episodes').iterdir())


def test_frozen_exact_selection_and_single_claim(frozen,monkeypatch):
    f,b,root,report,_,_,_=frozen
    calls=[]
    monkeypatch.setattr(b,'start',lambda *args:calls.append(args) or {})
    for confirm,select,model in [(False,True,f.HANDS_MODEL),(True,False,f.HANDS_MODEL),(True,True,'other')]:
        with pytest.raises(ValueError,match='SELECTION'):
            f.frozen_start(root,'local-cli',model,confirm,report['manifest_sha256'],select)
    f.frozen_start(root,'local-cli',f.HANDS_MODEL,True,report['manifest_sha256'],True)
    assert calls[0][-5:]==(4,256000,1,'frozen-demo-1',1800)
    b.write_new(b.runtime(root)/'episodes/episode-7.claim',{})
    with pytest.raises(ValueError,match='NO_RETRY'):
        f.frozen_start(root,'local-cli',f.HANDS_MODEL,True,report['manifest_sha256'],True)
