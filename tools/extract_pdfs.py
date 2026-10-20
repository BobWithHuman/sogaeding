"""Extract supplied references without changing their originals."""
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path('C:/Users/qkaeh/Downloads')
FILES = [
    ('R1', 'SW 공급망 보안 강화 로드맵.pdf'),
    ('C1', '[CM] 2026_소개딩 2라운드 사전교육 자료_vF.pdf'),
    ('P1', '[소개딩] 개발기획서_팀 인과함께_최종.pdf'),
    ('G1', '240525-(전체본)_SW_공급망_보안_가이드라인_최종 수정본.pdf'),
    ('G2', 'Python_시큐어코딩_가이드(2023년_개정본).pdf'),
    ('G3', '소프트웨어_보안약점_진단가이드(2021).pdf'),
    ('G4', '소프트웨어_개발보안_가이드(2021.12.29).pdf'),
]

def main():
    destination = ROOT / 'references' / 'extracted'
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    for key, filename in FILES:
        source = DOWNLOADS / filename
        reader = PdfReader(source)
        pages = []
        for number, page in enumerate(reader.pages, 1):
            content = page.extract_text(extraction_mode='layout')
            pages.append({'pdf_page': number, 'text': content})
        text_path = destination / f'{key}.txt'
        text_path.write_text('\n\n'.join(f'===== {key} PDF PAGE {p["pdf_page"]} =====\n{p["text"]}' for p in pages), encoding='utf-8')
        (destination / f'{key}.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
        item = {'id': key, 'filename': filename, 'source_path': str(source), 'pages': len(pages), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'text_path': str(text_path), 'characters': sum(len(p['text']) for p in pages), 'short_pages': [p['pdf_page'] for p in pages if len(p['text'].strip()) < 100]}
        manifest.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    (ROOT / 'references' / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
