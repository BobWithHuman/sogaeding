"""Page-based lookup, index and visual rendering for competition references."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
POPPLER = Path('C:/Users/qkaeh/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')

def manifest():
    return json.loads((ROOT / 'references/manifest.json').read_text(encoding='utf-8'))

def page_data(key):
    return json.loads((ROOT / f'references/extracted/{key}.json').read_text(encoding='utf-8'))

def prepare():
    items = manifest()
    target = ROOT / 'references/originals'
    target.mkdir(parents=True, exist_ok=True)
    index = ['# 원문 페이지 인덱스', '', '번호는 PDF 뷰어의 1부터 시작하는 페이지 번호다. 아래 미리보기는 기계 추출이며 요약이나 판정이 아니다.', '']
    for item in items:
        dest = target / item['filename']
        shutil.copy2(item['source_path'], dest)
        item['local_path'] = str(dest)
        index.extend([f'## {item["id"]} - {item["filename"]} ({item["pages"]}쪽)', ''])
        for page in page_data(item['id']):
            lines = [line.strip() for line in page['text'].splitlines() if line.strip()]
            preview = ' / '.join(lines[:4]).replace('|', '/')[:250]
            index.append(f'- PDF p.{page["pdf_page"]}: {preview or "[텍스트 없음: 시각 검토 필요]"}')
        index.append('')
    (ROOT / 'references/manifest.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'references/PAGE_INDEX.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
    print(f'Copied {len(items)} sources; indexed {sum(i["pages"] for i in items)} pages.')

def render(key, numbers, contact):
    item = next(i for i in manifest() if i['id'] == key)
    target = ROOT / f'references/visuals/{key}'
    target.mkdir(parents=True, exist_ok=True)
    images = []
    for number in numbers:
        dest = target / f'page-{number:03}'
        subprocess.run([str(POPPLER), '-f', str(number), '-l', str(number), '-singlefile', '-scale-to', '1800', '-png', item.get('local_path', item['source_path']), str(dest)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        images.append((number, dest.with_suffix('.png')))
    if contact:
        width = 1200
        thumb_width = width // 2
        thumbs = []
        for number, path in images:
            img = Image.open(path).convert('RGB')
            img.thumbnail((thumb_width, 850))
            thumbs.append((number, img))
        row_height = max(img.height for _, img in thumbs) + 35
        sheet = Image.new('RGB', (width, row_height * ((len(thumbs) + 1)//2)), 'white')
        draw = ImageDraw.Draw(sheet)
        for idx, (number, img) in enumerate(thumbs):
            x, y = (idx % 2)*thumb_width, (idx//2)*row_height
            draw.text((x + 10, y + 5), f'{key} PDF p.{number}', fill='black')
            sheet.paste(img, (x, y + 30))
        output = target / 'contact.png'
        sheet.save(output)
        print(output)
    else:
        for _, path in images:
            print(path)

def main():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'pages', 'search', 'render'])
    parser.add_argument('--id')
    parser.add_argument('--pages')
    parser.add_argument('--query')
    parser.add_argument('--contact', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'render':
        render(args.id, [int(n) for n in args.pages.split(',')], args.contact)
    else:
        for page in page_data(args.id):
            include = args.action == 'search' and args.query.casefold() in page['text'].casefold()
            if args.action == 'pages':
                start, _, end = args.pages.partition('-')
                include = int(start) <= page['pdf_page'] <= int(end or start)
            if include:
                print(f'===== {args.id} PDF PAGE {page["pdf_page"]} =====\n{page["text"]}')

if __name__ == '__main__':
    main()
