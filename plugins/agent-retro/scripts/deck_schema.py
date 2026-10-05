"""Validate deck structure before rendering. Errors name fields, never their private contents."""
import math
import re
from datetime import datetime

from contracts import AGENTS, SCHEMA_VERSION
from redact import scrub_secrets

TYPES = {'cold', 'bignum', 'lineup', 'ranking', 'quote', 'tally', 'compare', 'timeline', 'heatmap', 'coach', 'archetype', 'outro'}
THEMES = {'ink', 'blue', 'yellow', 'paper', 'pink', 'orange', 'green'}


def fail(path, message):
    raise ValueError(f'{path} {message}')


def number(value, path, maximum=None, integer=False):
    if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
            or (maximum is not None and value > maximum)
            or (integer and int(value) != value)):
        fail(path, 'must be a finite nonnegative ' + ('integer' if integer else 'number')
             + (f' <= {maximum}' if maximum is not None else ''))
    return value


def color(value, path='segment.color'):
    if not isinstance(value, str) or not re.fullmatch(
            r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|var\(--(?:fg|ink|paper|pink|blue|yellow|green|orange|claude|codex|chatgpt|claudeai)\)', value):
        fail(path, 'must be a hex color or a supported palette variable')
    return value


def obj(value, path):
    if not isinstance(value, dict):
        fail(path, 'must be an object')
    return value


def array(value, path, minimum=1, maximum=None):
    if not isinstance(value, list) or len(value) < minimum or (maximum is not None and len(value) > maximum):
        fail(path, f'must be an array with {minimum}' + (f'–{maximum}' if maximum is not None else ' or more') + ' items')
    return value


def text(value, path, maximum=4096):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        fail(path, f'must be nonempty text of at most {maximum} characters')
    return value


def fields(value, names, path):
    for name in names.split():
        text(value.get(name), path + '.' + name)


def scalar(value, path):
    if isinstance(value, str):
        text(value, path)
    else:
        number(value, path)


def quote(value, path):
    text(value, path)
    if len(value.split()) > 12:
        fail(path, 'must contain at most 12 words')
    if re.search(r'\[(?:redacted[^\]]*|email|phone)\]', value, re.I) or scrub_secrets(value) != value:
        fail(path, 'must not contain secrets, personal details, or redaction markers')


def rows(value, path, kind):
    for i, row in enumerate(array(value, path)):
        p = f'{path}[{i}]'
        obj(row, p)
        if kind == 'segment':
            number(row.get('value'), p + '.value')
            if 'color' in row:
                color(row['color'], p + '.color')
            if 'agent' in row and (not isinstance(row['agent'], str) or row['agent'] not in AGENTS):
                fail(p + '.agent', 'must be a supported agent')
        elif kind == 'compare':
            fields(row, 'label', p)
            number(row.get('pct'), p + '.pct', maximum=100)
            if 'n_label' in row:
                text(row['n_label'], p + '.n_label')
        elif kind == 'tally':
            fields(row, 'label', p)
            scalar(row.get('value'), p + '.value')
            if 'suffix' in row and not isinstance(row['suffix'], str):
                fail(p + '.suffix', 'must be text')


def pointer(root, ref, path):
    if not isinstance(ref, str) or not ref.startswith(('/stats/', '/coaching/')):
        fail(path, 'must be a JSON pointer beginning /stats/ or /coaching/')
    if root is None:
        return None
    value = root
    try:
        for key in ref[1:].split('/'):
            key = key.replace('~1', '/').replace('~0', '~')
            value = value[int(key)] if isinstance(value, list) else value[key]
    except (KeyError, IndexError, ValueError, TypeError):
        fail(path, 'does not resolve to measured evidence')
    return value


def validate_slide(slide, path, profile, evidence):
    s = obj(slide, path)
    t = s.get('type')
    if not isinstance(t, str) or t not in TYPES:
        fail(path + '.type', 'must be a supported component')
    if 'bg' in s and (not isinstance(s['bg'], str) or s['bg'] not in THEMES):
        fail(path + '.bg', 'must be a supported theme')
    for name in ('eyebrow', 'headline', 'lede', 'small', 'lens'):
        if name in s:
            text(s[name], path + '.' + name)
    refs = s.get('evidence_refs', [])
    array(refs, path + '.evidence_refs', minimum=1 if t == 'coach' and profile == 'default-12' else 0)
    values = [pointer(evidence, r, path + '.evidence_refs') for r in refs]
    if t == 'cold':
        fields(s, 'big headline', path)
    elif t == 'bignum':
        number(s.get('value'), path + '.value', integer=True)
        for i, bar in enumerate(array(s.get('bars', []), path + '.bars', minimum=0)):
            p = f'{path}.bars[{i}]'
            obj(bar, p)
            if 'label' in bar:
                text(bar['label'], p + '.label')
            rows(bar.get('segments'), p + '.segments', 'segment')
            for j, segment in enumerate(bar['segments']):
                fields(segment, 'label', f'{p}.segments[{j}]')
    elif t == 'lineup':
        fields(s, 'headline', path)
        for i, act in enumerate(array(s.get('acts'), path + '.acts')):
            p = f'{path}.acts[{i}]'
            obj(act, p)
            if not isinstance(act.get('agent'), str) or act['agent'] not in AGENTS:
                fail(p + '.agent', 'must be a supported agent')
            fields(act, 'tokens_label', p)
            number(act.get('prompts'), p + '.prompts', integer=True)
            number(act.get('sessions'), p + '.sessions', integer=True)
            for field in ('role', 'line', 'surfaces'):
                if field in act:
                    text(act[field], p + '.' + field)
    elif t == 'ranking':
        fields(s, 'headline', path)
        for i, row in enumerate(array(s.get('rows'), path + '.rows')):
            p = f'{path}.rows[{i}]'
            obj(row, p)
            fields(row, 'name value_label', p)
            rows(row.get('segments'), p + '.segments', 'segment')
            if 'meta' in row:
                text(row['meta'], p + '.meta')
    elif t in ('quote', 'tally', 'compare'):
        fields(s, 'headline', path)
        if t == 'quote':
            quote(s.get('quote'), path + '.quote')
        if t == 'tally' or 'tally' in s:
            rows(s.get('tally'), path + '.tally', 'tally')
        if t == 'compare':
            rows(s.get('rows'), path + '.rows', 'compare')
    elif t == 'timeline':
        fields(s, 'headline', path)
        for i, item in enumerate(array(s.get('items'), path + '.items')):
            p = f'{path}.items[{i}]'
            obj(item, p)
            fields(item, 'time text', p)
            if 'agent' in item and (not isinstance(item['agent'], str) or item['agent'] not in AGENTS):
                fail(p + '.agent', 'must be a supported agent')
    elif t == 'heatmap':
        fields(s, 'headline alt', path)
        keys = set()
        for i, day in enumerate(array(s.get('days'), path + '.days')):
            p = f'{path}.days[{i}]'
            obj(day, p)
            fields(day, 'key label', p)
            try:
                datetime.strptime(day['key'], '%Y-%m-%d')
            except ValueError:
                fail(p + '.key', 'must be a calendar date')
            if day['key'] in keys:
                fail(p + '.key', 'must be unique')
            keys.add(day['key'])
        hours = array(s.get('hours', list(range(8,23))), path + '.hours')
        for hour in hours:
            number(hour, path + '.hours[]', maximum=23, integer=True)
        for key, counts in obj(s.get('cells'), path + '.cells').items():
            if key not in {f'{day}|{h}' for day in keys for h in hours}:
                fail(path + '.cells', 'contains a cell outside the displayed days/hours')
            for agent, count in obj(counts, path + '.cells[]').items():
                if agent not in AGENTS:
                    fail(path + '.cells[]', 'must use supported agent keys')
                number(count, path + '.cells[] count')
    elif t == 'coach':
        fields(s, 'headline confidence why try', path)
        if s.get('kind') not in ('win', 'tweak'):
            fail(path + '.kind', 'must be win or tweak')
        if not re.fullmatch(r'strong signal|early signal|one moment|small sample · [1-9][0-9]*', s['confidence']):
            fail(path + '.confidence', 'must use a documented confidence label')
        if evidence is not None and s['confidence'] in ('strong signal', 'early signal'):
            allowed = {'strong signal'} if s['confidence'] == 'strong signal' else {'strong signal','early signal'}
            if not any(isinstance(v, dict) and v.get('confidence') in allowed for v in values):
                fail(path + '.confidence', 'is not supported by the referenced comparison groups')
        stat = obj(s.get('stat'), path + '.stat')
        if stat.get('type') == 'compare':
            rows(stat.get('rows'), path + '.stat.rows', 'compare')
        elif stat.get('type') == 'number':
            scalar(stat.get('value'), path + '.stat.value')
            fields(stat, 'label', path + '.stat')
        elif stat.get('type') == 'quote':
            quote(stat.get('quote'), path + '.stat.quote')
            if 'context' in stat:
                text(stat['context'], path + '.stat.context')
        else:
            fail(path + '.stat.type', 'must be compare, number, or quote')
    elif t == 'archetype':
        fields(s, 'name lede', path)
        for i, tile in enumerate(array(s.get('evidence'), path + '.evidence', 3, 3)):
            p = f'{path}.evidence[{i}]'
            obj(tile, p)
            fields(tile, 'label', p)
            scalar(tile.get('value'), p + '.value')
    elif t == 'outro':
        fields(s, 'title', path)
        for i, fact in enumerate(array(s.get('facts'), path + '.facts', 6 if profile == 'default-12' else 1, 6)):
            p = f'{path}.facts[{i}]'
            obj(fact, p)
            fields(fact, 'label', p)
            scalar(fact.get('value'), p + '.value')
        for i, attempt in enumerate(array(s.get('tries', []), path + '.tries', 3 if profile == 'default-12' else 0, 3)):
            text(attempt, f'{path}.tries[{i}]')
        if 'footer' in s:
            text(s['footer'], path + '.footer')


def validate_deck(spec, evidence=None):
    obj(spec, 'deck')
    fields(spec, 'title', 'deck')
    if spec.get('schema_version', SCHEMA_VERSION) != SCHEMA_VERSION:
        fail('schema_version', 'is unsupported')
    profile = spec.get('profile', 'default-12')
    if profile not in ('default-12', 'custom', 'limited'):
        fail('profile', 'must be default-12, custom, or limited')
    if 'seed' in spec and type(spec['seed']) is not int:
        fail('seed', 'must be an integer')
    slides = array(spec.get('slides'), 'slides', maximum=40)
    for i, slide in enumerate(slides):
        validate_slide(slide, f'slides[{i}]', profile, evidence)
    if profile == 'default-12':
        if len(slides) != 12:
            fail('slides', 'must contain exactly 12 slides for default-12')
        slots = {0:'cold',1:'bignum',2:'lineup',3:'coach',4:'ranking',6:'coach',8:'coach',9:'archetype',10:'coach',11:'outro'}
        for i, kind in slots.items():
            if slides[i]['type'] != kind:
                fail(f'slides[{i}].type', f'must be {kind} for default-12')
        coaches = [s for s in slides if s['type'] == 'coach']
        if len(coaches) != 4 or sum(s['kind'] == 'win' for s in coaches) < 2:
            fail('slides', 'must contain four coaching slides with at least two wins')
        if any(attempt not in {s['try'] for s in coaches} for attempt in slides[-1]['tries']):
            fail('slides[11].tries', 'must come from the coaching slides')
        if evidence is not None and slides[1]['value'] != evidence['stats']['tokens']['total']:
            fail('slides[1].value', 'must match stats.tokens.total')
    if profile == 'limited' and any(s['type'] in ('coach','archetype') for s in slides):
        fail('slides', 'must omit coaching claims and archetypes for limited data')
    return spec
