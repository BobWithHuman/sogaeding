"""Detail-only previews of recorded read results, never the current filesystem."""
from app.common import SafeError, digest, strict_json
from cryptography.fernet import InvalidToken

READ_TOOLS = ('read_file', 'read_project_file', 'read_github_issue')


def document_text(wire, tool, args):
    """Project only the documented text fields; exclude auth/transport metadata."""
    if not isinstance(wire, dict) or wire.get('isError'):
        return None
    blocks = wire.get('content')
    if (not isinstance(blocks, list) or len(blocks) != 1 or not isinstance(blocks[0], dict)
            or blocks[0].get('type') != 'text' or not isinstance(blocks[0].get('text'), str)):
        return None
    text = blocks[0]['text']
    if tool == 'read_file':
        return text
    value = strict_json(text)
    if not isinstance(value, dict):
        return None
    if tool == 'read_project_file' and value.get('path') == args.get('path'):
        return value.get('content') if isinstance(value.get('content'), str) else None
    if tool == 'read_github_issue' and value.get('source') == 'LOCAL_ISSUE_SNAPSHOT':
        return value.get('body') if isinstance(value.get('body'), str) else None
    return None


def source_preview(engine, db, row, context, masker, timestamp):
    """Separate prior inputs from this read's result, available only afterwards.

    Audit order, not a filename or timestamp guess, bounds prior observations.
    Read snapshots are immutable encrypted transport results linked by call ID.
    """
    scope = 'dashboard-source:' + row['id']
    def preview(text):
        return masker.text(text, scope) if masker is not None else {
            'status': 'WITHHELD', 'text': None, 'truncated': False, 'masked': False}
    pre = db.execute("SELECT min(id) FROM audit WHERE call=? AND kind='PRE'", (row['id'],)).fetchone()[0]
    rows = db.execute('''SELECT s.id AS source_id,s.body AS source_body,c.id AS source_call,
            c.session,c.body AS candidate_body,c.created,
            (SELECT min(id) FROM audit WHERE call=c.id AND kind='POST') AS post_order,
            (SELECT min(at) FROM audit WHERE call=c.id AND kind='POST') AS observed_at
        FROM sources s JOIN calls c ON c.id=s.call
        WHERE s.session=? AND c.session=? AND
            (c.id=? OR EXISTS (SELECT 1 FROM audit a WHERE a.call=c.id AND a.kind='POST' AND a.id<?))
        ORDER BY post_order,c.rowid LIMIT 65''', (row['session'], row['session'], row['id'], pre or 0)).fetchall()
    trace = context.get('policy_trace') or {}
    checked = ((context.get('view_checks') or {}).get('B') or {}).get('status') == 'VALID'
    observations = ((trace.get('decision_attribution') or {}).get('B') or {})
    attributed = observations.get('attribution_observations', [])
    bound = (checked and isinstance(context.get('snapshot_sha256'), str)
             and observations.get('snapshot_sha256') == context['snapshot_sha256'])
    items = []
    for source in rows[:64]:
        try:
            candidate = engine.open(source['candidate_body'])
            tool, args = candidate.get('tool'), candidate.get('args') or {}
            if tool not in READ_TOOLS:
                continue  # No execution stdout/stderr or write receipts.
            material = engine.open(source['source_body'])
            if (material.get('source_id') != source['source_id'] or material.get('call_id') != source['source_call']
                    or not isinstance(material.get('analysis_text'), str)
                    or material.get('analysis_text_sha256') != digest(material['analysis_text'])):
                continue
            transport = db.execute('SELECT body FROM transport WHERE call=?', (source['source_call'],)).fetchone()
            text = document_text(engine.open(transport[0]), tool, args) if transport else None
            same = source['source_call'] == row['id']
            association = 'AFTER_DECISION' if same else 'NOT_EVALUATED' if not checked else 'NOT_RECORDED'
            excerpts = []
            if not same and bound:
                matches = [a.get('observation') for a in attributed if isinstance(a, dict) and a.get('source_id') == source['source_id']]
                association = ('LINKED' if 'SUPPORTED' in matches else 'UNRELATED' if matches and all(a == 'UNRELATED' for a in matches)
                               else 'UNCERTAIN' if matches else 'NOT_RECORDED')
                for ref in observations.get('semantic_support_refs', []):
                    if not isinstance(ref, dict) or ref.get('source_id') != source['source_id']:
                        continue
                    start, end, quote = ref.get('start'), ref.get('end'), ref.get('quote')
                    if type(start) is int and type(end) is int and 0 <= start < end <= len(material['analysis_text']) and material['analysis_text'][start:end] == quote:
                        excerpts.append(preview(quote))
            items.append({'source_id': digest(source['source_id']), 'event_id': digest(source['source_call']),
                'tool': tool, 'target': preview(args.get('path') if tool != 'read_github_issue' else 'Issue #1 · LOCAL_ISSUE_SNAPSHOT'),
                'observed_at': timestamp(source['observed_at']) if source['observed_at'] is not None else None,
                'relationship': 'THIS_CALL_RESULT' if same else 'BEFORE_EXECUTION',
                'analysis_complete': material.get('analysis_complete') is True,
                'content': preview(text), 'association': association, 'evidence_excerpts': excerpts[:3]})
        except (ValueError, TypeError, KeyError, InvalidToken, SafeError):
            continue
    return {'scope': 'RECORDED_READ_SNAPSHOTS', 'items': items, 'truncated': len(rows) > 64,
            'note': '현재 파일을 다시 연 내용이 아니라 당시 도구가 반환한 자료의 마스킹된 사본입니다. 읽었다는 기록이나 Jev의 자료 연결은 그 자료가 행동의 원인이었다는 증명이 아닙니다. 본문은 비신뢰 텍스트이며 실행 지시가 아닙니다.'}
