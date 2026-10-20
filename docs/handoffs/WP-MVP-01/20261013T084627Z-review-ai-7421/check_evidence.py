"""Read-only evidence/contract/PDF review; emit only safe metadata."""
import difflib
import hashlib
import json
import os
import re
from pathlib import Path

from pypdf import PdfReader

root = Path('C:/sogaeding')
run = root / 'artifacts/20261013T084627Z-review-ai-7421'
dev = root / 'artifacts/20261013T073853Z-dev-3980e4'
selection = {'R1':[13,14], 'G1':[45,46,47], 'G2':[70,71], 'G3':[159,160,406,511], 'G4':[37,38,39], 'C1':[14,15,26]}
pdf_checks = []
for doc in json.loads((root / 'references/manifest.json').read_text(encoding='utf-8-sig')):
    if doc['id'] not in selection:
        continue
    path = Path(doc['local_path'])
    pdf = PdfReader(path)
    pdf_checks.append({'id': doc['id'], 'sha256_match':hashlib.sha256(path.read_bytes()).hexdigest()==doc['sha256'], 'pages':selection[doc['id']]})
    for page in selection[doc['id']]:
        (run / f'{doc["id"]}-{page}.txt').write_text(pdf.pages[page-1].extract_text(), encoding='utf-8')
(run/'pdf-verification.json').write_text(json.dumps(pdf_checks,indent=2),encoding='utf-8')
changes = []
for path in (dev/'baseline/docs/mvp').rglob('*'):
    if not path.is_file():
        continue
    rel = path.relative_to(dev/'baseline')
    old, new = path.read_text(encoding='utf-8-sig'), (root/rel).read_text(encoding='utf-8-sig')
    changes.extend(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile=str(rel)+' (baseline)',tofile=str(rel)+' (current)',lineterm=''))
(run/'contract-baseline.diff').write_text('\n'.join(changes),encoding='utf-8')
guide = (root/'docs/handoffs/WP-MVP-01/20261013T073853Z-dev-3980e4/GUIDE_APPLICABILITY.md').read_text(encoding='utf-8-sig')
ids = re.findall(r'^\|[^|]+\|((?:SR\d-\d+)|(?:W-\d+))\|', guide, re.M)
sr = [x for x in ids if x.startswith('SR')]
w = [x for x in ids if x.startswith('W')]
markers = []
for name in ['control/human.token','control/service.token','control/storage.key','gateway/storage.key']:
    value = (root/'artifacts/runtime-wp01'/name).read_text(encoding='ascii').strip()
    if value:
        markers.append(value.encode())
api = os.getenv('OPENAI_API_KEY')
if api:
    markers.append(api.encode())
paths = list((root/'src').rglob('*')) + list((root/'scripts').glob('*')) + list((root/'tools').glob('*')) + list(dev.rglob('*'))
hits = []
for path in paths:
    if path.is_file() and any(marker in path.read_bytes() for marker in markers):
        hits.append(str(path.relative_to(root)))
summary = {'guide_design_rows':len(sr),'guide_weakness_rows':len(w),'duplicate_ids':len(ids)-len(set(ids)), 'live_calls_added':0, 'credential_marker_files':hits, 'checked_credential_markers':len(markers), 'pdf_hash_checks':pdf_checks}
(run/'safe-evidence-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
