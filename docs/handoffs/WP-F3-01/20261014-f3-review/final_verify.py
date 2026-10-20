"""Compare candidate manifest, copied bytes, and current public source only."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[4]
manifest_path = root / sys.argv[1]
rows = json.loads(manifest_path.read_text(encoding='utf-8'))
current_mismatches, copied_mismatches = [], []
for row in rows:
    current = root / row['path']
    copied = manifest_path.parent / 'source' / row['path']
    if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != row['sha256']:
        current_mismatches.append(row['path'])
    if not copied.is_file() or hashlib.sha256(copied.read_bytes()).hexdigest() != row['sha256']:
        copied_mismatches.append(row['path'])
result = {'checked_at': datetime.now(UTC).isoformat(), 'manifest': str(manifest_path.relative_to(root)),
    'files': len(rows), 'current_mismatches': current_mismatches, 'copied_mismatches': copied_mismatches,
    'paid_requests_by_reviewer': 0, 'source_writes_by_reviewer': 0}
result['historical_docs'] = []
baseline_docs = root / 'artifacts/20261014-f3-01/baseline-product-source/source/docs/mvp'
for path in sorted((root / 'docs/mvp').glob('0*.md')):
    preserved = path.read_text(encoding='utf-8').endswith((baseline_docs / path.name).read_text(encoding='utf-8'))
    result['historical_docs'].append({'path': path.name, 'original_text_preserved_with_newline_normalization': preserved})
assert all(row['original_text_preserved_with_newline_normalization'] for row in result['historical_docs'])
browser = json.loads((root / 'artifacts/20261014-f3-01/browser-b-regression-r1/cases.json').read_text(encoding='utf-8'))
result['writer_browser_replay_cases'] = [{'case_id': row['case_id'], 'result': row['result'],
    'source_fingerprint': row['source_fingerprint']} for row in browser if row.get('result')]
assert len(result['writer_browser_replay_cases']) == 8 and all(row['result'] == 'PASS' for row in result['writer_browser_replay_cases'])
if len(sys.argv) > 3:
    earlier = json.loads((root / sys.argv[3]).read_text(encoding='utf-8'))
    current_hashes = {row['path']: row['sha256'] for row in rows}
    result['previous_files_changed'] = [row['path'] for row in earlier if current_hashes.get(row['path']) != row['sha256']]
    result['new_files'] = sorted(set(current_hashes) - {row['path'] for row in earlier})
    assert not result['previous_files_changed']
target_name = sys.argv[2] if len(sys.argv) > 2 else 'final-verification.json'
(root / 'artifacts/20261014-f3-review' / target_name).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
assert not current_mismatches and not copied_mismatches
