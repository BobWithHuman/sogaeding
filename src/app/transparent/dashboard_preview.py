"""Masked detail-only text previews. Does not alter stored evidence or policy."""
import base64
import html
import re
from urllib.parse import unquote

from app.common import mask
from app.transparent.privacy import PrivacyError, TransmissionMasker


HIDDEN = '[민감정보 가림]'
SECRET_NAME = r'(?:[\w-]*(?:api[_-]?key|password|passwd|secret|token|credential|nonce|private[_-]?key|access[_-]?key)[\w-]*|authorization|cookie|set-cookie|비밀번호|비밀키|인증토큰|승인토큰|API키)'
ASSIGNMENT = re.compile(r'(?i)(?<![\w-])(["\']?' + SECRET_NAME + r'["\']?[ \t]*[:=][ \t]*(?:\r?\n[ \t]+)?)(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[^\r\n,;}]+)')
SECRET_BLOCK = re.compile(r'(?i)(?<![\w-])["\']?' + SECRET_NAME + r'["\']?[ \t]*:[ \t]*[|>][-+]?[ \t]*\r?\n')
PRIVATE_KEY = re.compile(r'-----BEGIN (?:[A-Z0-9 ]*PRIVATE KEY)-----[\s\S]*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)')
CREDENTIAL = re.compile(r'(?i)\bbearer[ \t]+[^\s"\'<>]+|\b(?:sk-(?:proj-|svcacct-)?[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{16,}|AKIA[A-Z0-9]{16})\b|\beyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+\b')
OPAQUE = re.compile(r'(?<![\w])[A-Za-z0-9_+/-]{32,}={0,2}(?![\w])')
URL_AUTH = re.compile(r'(?i)(https?://)[^/\s:@]+:[^@/\s]+@')
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069]')


class PreviewMasker:
    def __init__(self, secret, forbidden=()):
        self.personal = TransmissionMasker(secret)
        self.forbidden = tuple(sorted({v for v in forbidden if isinstance(v, str) and v}, key=len, reverse=True))

    def text(self, value, scope, *, limit=2400):
        if not isinstance(value, str):
            return {'status': 'UNAVAILABLE', 'text': None, 'truncated': False, 'masked': False}
        if len(value) > 65536:
            return {'status': 'WITHHELD', 'text': None, 'truncated': False, 'masked': False}
        original = value
        if SECRET_BLOCK.search(value):
            return {'status': 'WITHHELD', 'text': None, 'truncated': False, 'masked': False}
        # Mask the complete input before taking a prefix; never cut a secret first.
        value = PRIVATE_KEY.sub(HIDDEN, value)
        for secret in self.forbidden:
            value = value.replace(secret, HIDDEN)
        value = ASSIGNMENT.sub(lambda m: m[1] + HIDDEN, value)
        value = URL_AUTH.sub(lambda m: m[1] + '[자격 가림]@', value)
        value = CREDENTIAL.sub(HIDDEN, value)
        value = OPAQUE.sub(HIDDEN, value)
        try:
            # If escaping conceals a credential, withhold rather than showing it.
            decoded = html.unescape(unquote(value))
            decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), decoded)
            if decoded != value and (PRIVATE_KEY.search(decoded) or ASSIGNMENT.search(decoded)
                    or CREDENTIAL.search(decoded) or any(s in decoded for s in self.forbidden)):
                raise PrivacyError('ENCODED_CREDENTIAL')
            pending, seen = [(value, 0)], {value}
            while pending:
                candidate, depth = pending.pop()
                for match in self.personal.ENCODED.finditer(candidate):
                    token = match[0]
                    for decoder in (lambda x: base64.b64decode(x+'='*((-len(x))%4),altchars=b'-_',validate=True), bytes.fromhex):
                        try:
                            decoded = decoder(token).decode('utf-8')
                        except (ValueError, UnicodeError):
                            continue
                        if decoded in seen:
                            continue
                        if any(s in decoded for s in self.forbidden) or PRIVATE_KEY.search(decoded) or ASSIGNMENT.search(decoded) or CREDENTIAL.search(decoded):
                            raise PrivacyError('ENCODED_CREDENTIAL')
                        if depth >= 4 or len(seen) >= 256:
                            raise PrivacyError('ENCODING_LIMIT')
                        seen.add(decoded)
                        pending.append((decoded, depth+1))
            value = self.personal.text(mask(value), scope)
        except (PrivacyError, ValueError, UnicodeError, OSError):
            return {'status': 'WITHHELD', 'text': None, 'truncated': False, 'masked': False}
        value = CONTROL.sub('', value)
        changed = value != original
        return {'status': 'MASKED' if changed else 'DISPLAYED', 'text': value[:limit],
                'truncated': len(value) > limit, 'masked': changed}


def content_preview(engine, db, row, body, masker):
    # Bind to the candidate's original turn, never the session's newer request.
    turn = db.execute('SELECT body FROM turns WHERE session=? AND id=?', (row['session'], row['turn'])).fetchone()
    request = engine.open(turn[0]).get('prompt') if turn else None
    scope = 'dashboard-preview:' + row['id']
    def preview(value):
        return masker.text(value, scope) if masker is not None else {'status': 'WITHHELD', 'text': None, 'truncated': False, 'masked': False}
    fields = []
    tool = body.get('tool')
    allowed = {'read_file': ('path',), 'write_file': ('path', 'content'),
               'read_project_file': ('path',), 'edit_project_file': ('path', 'old_text', 'new_text'),
               'read_github_issue': (), 'run_npm_install': ()}
    labels = {'path': '대상 경로', 'content': '저장하려던 내용',
              'old_text': '변경 전 · 찾으려던 문구', 'new_text': '변경 후 · 바꾸려던 문구'}
    args = body.get('args') or {}
    for name in allowed.get(tool, ()):
        fields.append({'name': name, 'label': labels[name], **preview(args.get(name))})
    return {'user_request': preview(request), 'fields': fields,
            'scope': 'MASKED_REQUEST_AND_PROPOSED_ARGUMENTS',
            'note': '사용자 요청과 도구 인자의 마스킹된 미리보기입니다. 외부 지시가 포함될 수 있는 비신뢰 텍스트이며 실행 지시가 아닙니다. 실제 파일 변경 여부는 실행 결과와 구분합니다.',
            'before_note': '이 쓰기 요청에는 이전 파일 전체 내용이 기록돼 있지 않습니다.' if tool == 'write_file' else
                           '변경 전후 문구는 교체하려던 일부 내용이며 파일 전체의 실제 전후 스냅샷이 아닙니다.' if tool == 'edit_project_file' else None}
