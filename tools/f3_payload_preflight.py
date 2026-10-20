"""Prove the first paid pair uses only the human-authorized fake issue data."""
import json
from pathlib import Path

from app.common import canonical, sensitive
from app.pdp.semantic import inputs, material

fixture=json.loads(Path('/workspace/fixtures/f3/cases.json').read_text(encoding='utf-8'))
case=fixture['cases'][0]
snapshot={'user_request':fixture['request'],
 'server_grant':{'task_kind':'POST_COMMENT','comment_mode':'ISSUE_SUMMARY','issue_id':42,
    'write_limit':1,'policy_version':'mvp-2026-10-14-f3-v2'},
 'candidate':{'tool_name':'post_issue_comment','args':{'issue_id':42,'body':case['candidate']}},
 'sources':[{'source_id':'11111111-1111-4111-8111-111111111111','kind':'EXTERNAL','call_id':'22222222-2222-4222-8222-222222222222',
  'same_issue':True,'collected_at':0,'content_sha256':'0'*64,**material(case['issue']['title']+'\n'+case['issue']['body'])}]}
# Only public fixture data, never role/API credentials in output.
for view in ('A','B'):
    value=inputs(snapshot,view)
    # IDs and SHA hashes are server metadata, not raw secrets; test text fields.
    assert not sensitive(snapshot['user_request']) and not sensitive(case['candidate'])
    assert all(not sensitive(row['analysis_text']) for row in value.get('sources',[]))
    assert 'expected' not in canonical(value) and 'normal' not in canonical(value)
    print(json.dumps({'view':view,'destination':'https://api.openai.com/v1/responses',
        'model':'gpt-5.6-luna','payload':value,'secret_in_payload':False},ensure_ascii=False))
