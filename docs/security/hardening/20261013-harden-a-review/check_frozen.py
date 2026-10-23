import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

root = Path(__file__).resolve().parents[4]
target = root/'artifacts/20261013-harden-a-review'
frozen = root/'artifacts/20261013-harden-a'
manifest = json.loads((frozen/'r1/manifest.json').read_text(encoding='utf-8-sig'))
summary = json.loads((frozen/'r1/summary.json').read_text(encoding='utf-8-sig'))
hashes = lambda items: {item['path']: item['sha256'] for item in items}
current = {item['path']: hashlib.sha256((root/item['path']).read_bytes()).hexdigest() for item in manifest}
bad = [path for path, sha in hashes(manifest).items() if current[path] != sha]
fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
assert not bad and fingerprint == summary['fingerprint']
baseline = json.loads((frozen/'baseline/manifest.json').read_text(encoding='utf-8-sig'))
old = json.loads((root/'artifacts/20261013T073853Z-dev-3980e4/source-manifest-final.json').read_text(encoding='utf-8-sig'))
assert not [item['path'] for item in old if hashes(baseline).get(item['path']) != item['sha256']]
for item in baseline:
    assert hashlib.sha256((frozen/'baseline/source'/item['path']).read_bytes()).hexdigest() == item['sha256']
value = {'fingerprint': fingerprint, 'files': len(manifest), 'mismatches': bad,
         'old_baseline_files': len(old), 'baseline_old_mismatches': [],
         'changed_from_baseline': [p for p,s in current.items() if p in hashes(baseline) and hashes(baseline)[p] != s],
         'new_from_baseline': [p for p in current if p not in hashes(baseline)]}
(target/'frozen-check.json').write_text(json.dumps(value, indent=2))
pages = {'R1':[13,14], 'G1':[35,47], 'G2':[133,135,137,143],
         'G3':[153,164,171,510,511], 'G4':[24,38], 'C1':[14,15,26]}
pdfs = []
folder = target/'guide-pages'
folder.mkdir(exist_ok=True)
for entry in json.loads((root/'references/manifest.json').read_text(encoding='utf-8-sig')):
    if entry['id'] not in pages:
        continue
    path = root/'references/originals'/entry['filename']
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == entry['sha256']
    reader = PdfReader(path)
    for page in pages[entry['id']]:
        (folder/f"{entry['id']}-{page}.txt").write_text(reader.pages[page-1].extract_text(),encoding='utf-8')
    pdfs.append({'id':entry['id'], 'sha256':sha, 'pages':pages[entry['id']]})
(folder/'manifest.json').write_text(json.dumps(pdfs,indent=2))
print(json.dumps({'frozen_files':len(manifest), 'fingerprint':fingerprint,
    'old50_baseline_match':True,'original_pdf_hashes':len(pdfs)}))
