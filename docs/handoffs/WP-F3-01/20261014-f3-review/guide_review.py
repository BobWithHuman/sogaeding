"""Reuse recorded page extraction, verify original hashes; no re-extraction claim."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[4]
target = root / 'artifacts/20261014-f3-review/guides'
target.mkdir(parents=True, exist_ok=False)
pages = {'R1': [13, 14], 'G1': [35, 47], 'G2': [123, 125, 133, 135],
         'G3': [66, 69, 110, 112, 406, 509, 511], 'G4': [24, 37, 38]}
manifest = json.loads((root / 'references/manifest.json').read_text(encoding='utf-8'))
results = []
for identifier, selected in pages.items():
    original = next(row for row in manifest if row['id'] == identifier)
    path = root / 'references/originals' / original['filename']
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == original['sha256']
    extracted = json.loads((root / f'references/extracted/{identifier}.json').read_text(encoding='utf-8'))
    chosen = [row for row in extracted if row['pdf_page'] in selected]
    assert len(chosen) == len(selected)
    (target / (identifier + '-pages.json')).write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding='utf-8')
    results.append({'id': identifier, 'original_sha256': sha, 'pages': selected,
                    'extraction': 'Existing repository extraction, original SHA256 matched'})
    for row in chosen:
        print(f"{identifier} PDF{row['pdf_page']}\n{row['text'][:1600]}\n")
(target / 'verification.json').write_text(json.dumps({'captured_at': datetime.now(UTC).isoformat(),
    'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
