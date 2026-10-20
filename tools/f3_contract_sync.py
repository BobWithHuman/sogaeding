"""Apply only the explicit WP-F3-01 SPEC-4 delegation."""
import copy
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
path=root/'docs/mvp/contracts/openapi.json'
api=json.loads(path.read_text(encoding='utf-8'))
api['info']['version']='MVP-SPEC-4'
schemas=api['components']['schemas']
exact=schemas['SessionCreate']['oneOf'][1]
exact['properties']['comment_mode']={'type':'string','const':'EXACT','default':'EXACT'}
summary=copy.deepcopy(exact)
summary['properties'].pop('allowed_comment_body')
summary['properties']['comment_mode']={'type':'string','const':'ISSUE_SUMMARY'}
summary['required']=[x for x in summary['required'] if x!='allowed_comment_body']+['comment_mode']
schemas['SessionCreate']['oneOf'].append(summary)
ref={'type':'object','additionalProperties':False,'properties':{
 'view':{'type':'string','enum':['A','B']},'source_id':{'type':'string','maxLength':64},
 'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1},
 'quote':{'type':'string','maxLength':512,'minLength':1}},'required':['view','source_id','start','end','quote']}
schemas['EvidenceRef']=ref
check=schemas['CheckReply']
for name,prop in {
 'analysis_id':{'type':['string','null'],'format':'uuid'},
 'decision_stage':{'type':'string','enum':['POLICY','SOURCE','SEMANTIC']},
 'evidence_snapshot_sha256':{'type':['string','null'],'pattern':'^[a-f0-9]{64}$'},
 'evidence_refs':{'type':'array','maxItems':16,'items':{'$ref':'#/components/schemas/EvidenceRef'}}}.items():
    check['properties'][name]=prop
    # Wire compatibility for preserved fault peer fixtures; product always emits.
reasons=check['properties']['reason_codes']['items']['enum']
for reason in ['USER_INTENT_SUPPORTED','TASK_DATA_SUPPORTED','EXTERNAL_INSTRUCTION_DEPENDENCY','SEMANTIC_UNCERTAIN',
 'SOURCE_CONTEXT_MISSING','SOURCE_CONTEXT_INCOMPLETE','ANALYSIS_UNAVAILABLE','ANALYSIS_IN_PROGRESS','ANALYSIS_STALE']:
    if reason not in reasons: reasons.append(reason)
schemas['SourceIngest']['properties'].update({'analysis_text':{'type':'string','maxLength':8192},
 'analysis_text_sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},'analysis_complete':{'type':'boolean'}})
api['x-f3-limits']={'source_text_chars':8192,'source_text_utf8_bytes':16384,'source_count':8,
 'context_chars':16384,'context_utf8_bytes':32768,'judge_requests_per_candidate':2,
 'semantic_candidates_per_session':2,'judge_request_timeout_seconds':15,'judge_deadline_seconds':20,
 'check_client_timeout_seconds':25,'tool_deadline_seconds':35,'policy':'mvp-2026-10-14-f3-v2'}
path.write_text(json.dumps(api,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
tools_path=root/'docs/mvp/contracts/tools.schema.json'
tools=json.loads(tools_path.read_text(encoding='utf-8'))
tools['title']=tools['title'].replace('MVP-SPEC-3','MVP-SPEC-4')
tools_path.write_text(json.dumps(tools,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
examples_path=root/'docs/mvp/contracts/examples.json'
examples=json.loads(examples_path.read_text(encoding='utf-8'))
examples['version']='MVP-SPEC-4'
for case_id,body,valid in [('SUMMARY_COMMENT_SESSION',None,True),('INVALID_SUMMARY_COMMENT_BODY','pre-granted',False)]:
    request={'task_kind':'POST_COMMENT','comment_mode':'ISSUE_SUMMARY','user_request':'이슈42를 읽고 요약 댓글을 한 번 작성해줘','issue_id':42}
    if body is not None: request['allowed_comment_body']=body
    examples['cases'].append({'id':case_id,'schema':'SessionCreate','request':request,'valid':valid})
examples_path.write_text(json.dumps(examples,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
