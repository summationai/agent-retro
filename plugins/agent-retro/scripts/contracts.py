"""Versioned records shared by extraction, measurement, and run preparation."""
import hashlib
from typing import Optional, TypedDict

SCHEMA_VERSION = 1
AGENTS = frozenset(('claude-code', 'codex', 'chatgpt', 'claude-ai'))
TOKEN_FIELDS = ('fresh_input', 'cache_read', 'cache_write', 'output', 'reasoning')


class Prompt(TypedDict):
    id: str
    ts: float
    agent: str
    session: str
    project: str
    surface: Optional[str]
    text: str
    is_automation: bool


def prompt_id(row):
    # Stable across source-file copies and measurement order. Never expose raw text in IDs.
    parts = (row['agent'], row['session'], str(row['ts']), row['text'])
    return 'p_' + hashlib.sha256('\0'.join(parts).encode()).hexdigest()[:20]


def identify_prompts(rows):
    return [dict(row, id=row.get('id') or prompt_id(row)) for row in rows]


def validate_data(data):
    if data.get('schema_version', SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ValueError('unsupported extraction schema_version')
    for field in ('prompts', 'usage'):
        if not isinstance(data.get(field), list):
            raise ValueError(f'{field} must be an array')
    return data
