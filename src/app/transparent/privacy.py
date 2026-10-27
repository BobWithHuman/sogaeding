"""Transmission-only masking; immutable local evidence stays unchanged."""
import base64
import hashlib
import hmac
import html
import re
from urllib.parse import unquote

PATTERNS = (
    re.compile(r"(?<![A-Z0-9.!#$%&'*+/=?^_`{|}~-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+", re.I),
    re.compile(r"(?<!\w)(?:\+82[- .]?(?:10|2|[3-6][1-5])|0(?:10|11|16|17|18|19|2|[3-6][1-5]))[- .]?\d{3,4}[- .]?\d{4}(?!\w)"),
    re.compile(r"(?<!\w)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[- ]?[1-8]\d{6}(?!\w)"),
    re.compile(r"(?<!\w)\d{3}-\d{2}-\d{4}(?!\w)"),
    re.compile(r"(?:성명|주민등록번호|여권번호|생년월일|거주지|집주소)\s*[:=]\s*\S+"),
    re.compile(r"(?:full_name|date_of_birth|passport_number|home_address|ssn)[\"']?\s*[:=]\s*[\"']?[^\s,;}]+", re.I),
    re.compile(r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|전라|경상|제주)[^\n]{0,40}(?:로|길)\s*\d"),
)


def contains_pii(value):
    if isinstance(value, str):
        return any(pattern.search(value) for index, pattern in enumerate(PATTERNS) if index != 0 or "@" in value)
    if isinstance(value, list):
        return any(contains_pii(item) for item in value)
    if isinstance(value, dict):
        return any(contains_pii(str(key) + "=" + str(item)) or contains_pii(item) for key, item in value.items())
    return False


class PrivacyError(ValueError):
    """A safe transformation cannot be established; never transmit the input."""


class TransmissionMasker:
    """Analysis-scoped opaque identifiers; original evidence is never mutated.

    Names/addresses and encoded PII are rejected rather than erasing potentially
    meaningful instructions. No reversible map or personal values are persisted.
    """
    NOTE = (" Privacy: WH aliases are opaque personal identifiers, not instructions or authority. "
            "Equal aliases denote equal values; different aliases denote different values. "
            "Judge changes of target and external commands normally.")
    KINDS = ("EMAIL", "PHONE", "RRN", "SSN")
    RESERVED = re.compile(r"(?i)\bWH_(?:EMAIL|PHONE|RRN|SSN|CARD)_")
    ENCODED = re.compile(r"(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{8,}={0,2}(?![A-Za-z0-9+/_-])")
    PERSONAL_FIELDS = frozenset({"full_name", "date_of_birth", "passport_number", "home_address", "성명", "거주지", "집주소", "생년월일", "여권번호"})
    CARD = re.compile(r"(?<![\w-])(?:\d{4}[ -]){3}\d{4}(?![\w-])|(?<![\w-])\d{4}[ -]\d{6}[ -]\d{5}(?![\w-])|(?<!\w)\d{13,19}(?!\w)")

    def __init__(self, secret):
        self.secret = secret

    def alias(self, kind, value, analysis):
        # Exact values remain distinct. No normalization may collapse different targets.
        data = (analysis + "\0" + kind + "\0" + value).encode("utf-8")
        return "WH_" + kind + "_" + hmac.new(self.secret, data, hashlib.sha256).hexdigest()[:32]

    @staticmethod
    def card(value):
        digits = [int(c) for c in value if c.isdigit() and c.isascii()]
        return 13 <= len(digits) <= 19 and sum(
            d if i % 2 == 0 else (2*d if d < 5 else 2*d-9)
            for i, d in enumerate(reversed(digits))) % 10 == 0

    def text(self, value, analysis):
        if self.RESERVED.search(value):
            raise PrivacyError("RESERVED_ALIAS")
        # Avoid leaking an encoded copy alongside a masked decoded presentation.
        self.check_encoded(value)
        if any(pattern.search(value) for pattern in PATTERNS[4:]):
            raise PrivacyError("UNSUPPORTED_PERSONAL_CONTEXT")
        matches = []
        for kind, pattern in zip(self.KINDS, PATTERNS[:4], strict=True):
            if kind == "EMAIL" and "@" not in value:
                continue
            matches.extend((m.start(), m.end(), kind) for m in pattern.finditer(value))
        matches.extend((m.start(), m.end(), "CARD") for m in self.CARD.finditer(value) if self.card(m[0]))
        result, position = [], 0
        for start, end, kind in sorted(matches, key=lambda row: (row[0], -(row[1]-row[0]))):
            if start < position:
                continue
            result.extend((value[position:start], self.alias(kind, value[start:end], analysis)))
            position = end
        return "".join(result) + value[position:]

    def protected(self, value):
        return bool(contains_pii(value) or self.RESERVED.search(value)
                    or any(self.card(m[0]) for m in self.CARD.finditer(value)))

    def check_encoded(self, value):
        queue, seen = [(value,0)], {value}
        while queue:
            candidate, depth = queue.pop()
            decoded = html.unescape(unquote(candidate))
            decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m:chr(int(m[1],16)), decoded)
            following = [decoded] if decoded != candidate else []
            for match in self.ENCODED.finditer(candidate):
                token = match[0]
                for decoder in (lambda x:base64.b64decode(x+'='*((-len(x))%4),altchars=b'-_',validate=True),bytes.fromhex):
                    try:
                        following.append(decoder(token).decode('utf-8'))
                    except (ValueError,UnicodeError):
                        continue
            for decoded in following:
                if decoded in seen:
                    continue
                if self.protected(decoded):
                    raise PrivacyError('ENCODED_PERSONAL_CONTEXT')
                if depth >= 4 or len(seen) >= 1024:
                    raise PrivacyError('ENCODING_DEPTH_LIMIT')
                seen.add(decoded)
                queue.append((decoded,depth+1))

    def transform(self, value, analysis):
        if isinstance(value, str):
            return self.text(value, analysis)
        if isinstance(value, list):
            return [self.transform(item, analysis) for item in value]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if self.protected(key) or key.lower() in self.PERSONAL_FIELDS:
                    raise PrivacyError("PERSONAL_FIELD_OR_KEY")
                self.check_encoded(key)
                result[key] = self.transform(item, analysis)
            return result
        if type(value) in (int,float) and self.protected(str(value)):
            raise PrivacyError('PERSONAL_NUMERIC_VALUE')
        return value
