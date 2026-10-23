"""Frozen public wire reconstruction and new-question synthetic enforcement."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from test_decision_attribution import SyntheticV5

from app.common import canonical, digest
from app.pdp.diagnostics import AnalysisFailure
from app.pdp.semantic import material
from app.transparent.jev import MODEL, JevClient, JevSettings, validate_response

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/'artifacts/management-frozen-demo-20261017'


class SyntheticCurrent(SyntheticV5):
    async def observe(self,view,state,questions,analysis_id):
        answers={}
        self.requests[view]=(state,questions)
        for name,question in questions.items():
            logical='behavior' if name=='current_behavior' else name
            picked=self.scope if logical=='task_relation' else self.behavior if logical=='behavior' else self.attribution
            options=question['criteria']
            probabilities={key:float(key==picked) for key in options}
            confidence=1.
            if logical in self.low:
                probabilities[picked]=.8
                probabilities[next(key for key in options if key!=picked)]=.2
                confidence=(.8*len(options)-1)/(len(options)-1)
            answers[name]={'type':'choice','choice':picked,'probabilities':probabilities,'confidence':confidence}
        return validate_response({'model':MODEL,'answers':answers,'usage':{'input_tokens':10,'output_tokens':2}},questions)[0]


def frozen_snapshot(focused=False):
    scenario=json.loads((CAP/'scenario.json').read_text())
    reference=json.loads((CAP/'source-reference.json').read_text())
    texts=[(CAP/'public-capture'/name).read_bytes().decode() for name in ('docs/release.md','reports/normal.md','docs/review.md')]
    texts.insert(1,'File write observed.')
    sources=[]
    events=[]
    for i,(text,ref) in enumerate(zip(texts,reference['validated_input_sources'],strict=True)):
        raw=canonical({'content':[{'type':'text','text':text}],'isError':False})
        assert digest(raw)==ref['analysis_text_sha256']
        sid=ref['source_id']
        sources.append({'source_id':sid,'call_id':reference['source_call_links'][sid],'origin':'mcp','same_issue':False,**material(raw)})
        events.append({'source_id':sid,'call_id':sources[-1]['call_id'],'turn_index':int(i==3),'route':'mcp',
                       'tool':'write_file' if i==1 else 'read_file','target':['docs/release.md','reports/normal.md','reports/normal.md','docs/review.md'][i],
                       'result_role':'WRITE_COMPLETION' if i==1 else 'READ_RESULT'})
    candidate=json.loads((CAP/'safe-review-candidate.json').read_text())
    assert digest(canonical(candidate))==scenario['current_safe_candidate_hash']
    snap={'analysis_id':'PUBLIC_RECONSTRUCTION_UNKNOWN_ORIGINAL_ID','user_request':canonical({'actual_user_turns_chronological':scenario['prompts'],'latest_turn':1}),
          'server_grant':{'workspace':'C:\\repo','comment_mode':'DEVELOPMENT'},'candidate':candidate,'sources':sources}
    if focused:
        snap['observation_context']={'current_turn':1,'actual_turns':scenario['prompts'],'source_events':events}
    return snap


    # Original analysis_id/grant/other missing fields stay UNKNOWN. Raw source
    # envelopes and candidate are exact, the entire original snapshot is not.










def test_shared_original_eight_request_ledger_old_and_new_contend_only_four_more(tmp_path):
    key=tmp_path/'jev.api-key'
    key.write_text('PUBLIC-FAKE')
    settings=JevSettings(True,key_path=key,budget_path=tmp_path/'typesafe-budget.sqlite3',request_limit=8,input_token_limit=512000,policy_id='mvp-demo-hands-on-1')
    original,new=JevClient(settings),JevClient(settings)
    for i in range(4):
        original._claim('old'+str(i),'A')
    def claim(i):
        try:
            (new if i%2 else original)._claim('contender'+str(i),'B')
            return True
        except AnalysisFailure:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(claim,range(12)))==4
    with pytest.raises(AnalysisFailure):
        new._claim('no-refund','A')
