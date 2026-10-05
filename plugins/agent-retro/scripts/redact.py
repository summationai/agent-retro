"""Agent Retro redaction: strips secrets and personal details from prompt text before anything reads it.

Usage: from redact import scrub_secrets, REDACTIONS
"""
import collections, os, re

_HOME = os.path.expanduser('~')
REDACTIONS = collections.Counter()


def _luhn(digits):
    total, alt = 0, False
    for c in reversed(digits):
        d = int(c)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _card(m):
    digits = re.sub(r'\D', '', m.group(0))
    return '[redacted:card]' if 13 <= len(digits) <= 19 and _luhn(digits) else m.group(0)


PATTERNS = ([('home_path', re.compile(re.escape(_HOME) + r'(?![^/\\\s])'), '~')] if len(_HOME) > 1 else []) + [
    ('private_key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)', re.S), '[redacted:private-key]'),
    ('url_credentials', re.compile(r'(?i)\b([a-z][a-z0-9+.-]*://)[^\s:/@]+:[^\s/@]+@'), r'\1[redacted]@'),
    ('webhook', re.compile(r'(?i)https://(?:hooks\.slack\.com/\S+|(?:discord|discordapp)\.com/api/webhooks/\S+)'), '[redacted:webhook]'),
    ('api_key', re.compile(r'\b(?:sk-ant-[\w-]{8,}|sk-[\w-]{16,}|sk-[a-z]+[*•]{3,}\S*|(?:sk|rk|pk)_(?:live|test)_\w{10,}|gh[pousr]_[A-Za-z0-9]{20,}'
                           r'|github_pat_\w{20,}|glpat-[\w-]{20,}|npm_[A-Za-z0-9]{30,}|xox[abprs]-[\w-]{10,}|(?:AKIA|ASIA)[0-9A-Z]{16}|AIza[\w-]{30,})'), '[redacted:key]'),
    ('jwt', re.compile(r'\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{5,}'), '[redacted:token]'),
    ('auth_header', re.compile(r'(?i)\b(bearer|basic)\s+[\w.~+/-]{16,}=*'), r'\1 [redacted]'),
    ('assignment', re.compile(r'(?i)\b([\w-]*(?:token|api[_-]?key|secret|password|passwd|pwd|access[_-]?key|private[_-]?key|credentials?))'
                              r'(["\']?\s*[:=]\s*["\']?)[^\s"\',;]{6,}'), r'\1\2[redacted]'),
    ('url_secret', re.compile(r'(?i)([?&#](?:access_token|refresh_token|id_token|token|api_?key|key|secret|client_secret|code|sig|signature|password|auth)=)[^&#\s]+'), r'\1[redacted]'),
    ('email', re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b'), '[email]'),
    ('user_path', re.compile(r'(?:/Users|/home)/(?!Shared\b)[^/\s]+|\b[A-Za-z]:\\Users\\[^\\\s]+'), '~'),
    ('ssn', re.compile(r'(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])'), '[redacted:ssn]'),
    ('card', re.compile(r'(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])'), _card),
    ('phone', re.compile(r'(?<![\w+])(?:\+?1[ .-]?)?\(?[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)'
                         r'|(?<!\w)\+[2-9]\d{0,2}[ .-]?\d{1,4}(?:[ .-]?\d{2,4}){2,4}(?!\w)'), '[phone]'),
    ('password_like', re.compile(r'(?<!\S)(?=\S*[a-z])(?=\S*[A-Z])(?=\S*\d)(?=\S*[^\w\s])(?!\S*[/<>`()\[\]{}])\S{8,64}(?!\S)'), '[redacted]'),
    ('long_secret', re.compile(r'(?<![\w/.-])(?=[A-Za-z0-9+_-]*\d)(?=[A-Za-z0-9+_-]*[A-Z])[A-Za-z0-9+_-]{32,}={0,2}(?![\w/])'
                               r'|\b[A-Fa-f0-9]{32,}\b|(?<![\w/.-])(?=[A-Za-z0-9+/_-]*\d)[A-Za-z0-9+/_-]{48,}={0,2}(?![\w/])'), '[redacted:long-string]'),
]


def scrub_secrets(text):
    """Replace secrets and personal details in text, counting each kind in REDACTIONS."""
    if not text or not isinstance(text, str):
        return text
    for name, rx, rep in PATTERNS:
        hits = []

        def sub(m, rep=rep, hits=hits):
            out = rep(m) if callable(rep) else m.expand(rep)
            if out != m.group(0):
                hits.append(1)
            return out
        text = rx.sub(sub, text)
        if hits:
            REDACTIONS[name] += len(hits)
    return text


def scrub_tree(value):
    """Sanitize all text at a serialization boundary, including mapping keys.

    Keep colliding redacted labels distinct so privacy never silently drops data.
    Metrics must be computed on raw data before calling this function.
    """
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            safe = scrub_secrets(key)
            label, suffix = safe, 2
            while label in result:
                label = f'{safe} ({suffix})'
                suffix += 1
            result[label] = scrub_tree(item)
        return result
    if isinstance(value, (list, tuple)):
        return [scrub_tree(item) for item in value]
    return scrub_secrets(value)
