"""Agent Retro extractor. Version: retro-2026-10-05

Usage: python3 extract.py [out.json] [--days N] [--sources codex,chatgpt]
Reads local logs and exports. The output contains raw private data; do not give it to an agent.
Prefer prepare.py, which measures, redacts, and removes raw data automatically.
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from contracts import AGENTS, SCHEMA_VERSION, prompt_id
from redact import scrub_tree
from io_utils import write_json

EXPORT_PROJECT = {'chatgpt': 'ChatGPT', 'claude-ai': 'claude.ai'}
INJECTED = ('<', '# AGENTS.md', 'The following is the Codex agent history')
TAG_RE = re.compile(r'<(system-reminder|command-[a-z-]+|local-command-[a-z-]+|task-notification|ide_[a-z_]+|pasted_content[^>]*)>.*?</\1[^>]*>', re.S)
MAX_EXPORT_BYTES = 256 * 1024 * 1024


class Config(NamedTuple):
    home: str
    now: float
    days: int
    sources: frozenset
    exports: tuple = ()

    @property
    def cut(self):
        return self.now - self.days * 86400


def config(home=None, now=None, days=7, sources='all', exports=()):
    try:
        days = int(days)
    except (ValueError, TypeError):
        raise ValueError('days must be a positive integer') from None
    if days < 1:
        raise ValueError('days must be a positive integer')
    selected = {x.strip() for x in sources.split(',') if x.strip()}
    if not selected or selected - AGENTS - {'all'}:
        raise ValueError('sources must be all or a comma-separated list of: ' + ', '.join(sorted(AGENTS)))
    if 'all' in selected:
        selected = AGENTS
    now = time.time() if now is None else float(now)
    if not math.isfinite(now):
        raise ValueError('now must be a finite epoch timestamp')
    return Config(os.path.abspath(os.path.expanduser(home or '~')), now, days, frozenset(selected), tuple(exports))


def timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('invalid timestamp')
    return float(value)


def clean(text):
    return TAG_RE.sub('', text).strip()


def _git(path, *args):
    try:
        result = subprocess.run(['git', '-C', path, *args], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


class Extractor:
    def __init__(self, settings):
        self.cfg = settings
        self.prompts, self.automations, self.usage, self.tools = [], [], [], []
        self.sessions, self.sources, self.provenance = {}, {}, {}
        self.self_report = None
        self.diagnostics = {a: dict(files_discovered=0, files_read=0, malformed_records=0,
                                   usable_prompts=0, usage_rows=0, issues={}, status='absent')
                            for a in sorted(settings.sources)}
        self._projects, self._prompts, self._tools = {}, set(), set()
        self.codex_checks = []

    def issue(self, agent, code):
        issues = self.diagnostics[agent]['issues']
        issues[code] = issues.get(code, 0) + 1

    def malformed(self, agent):
        self.diagnostics[agent]['malformed_records'] += 1

    def in_window(self, when):
        return self.cfg.cut <= when <= self.cfg.now

    def jsonl(self, path, agent, count=True):
        diag = self.diagnostics[agent]
        if count:
            diag['files_discovered'] += 1
        try:
            with open(path, encoding='utf-8') as f:
                if count:
                    diag['files_read'] += 1
                for line in f:
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError('not an object')
                        yield row
                    except (ValueError, TypeError):
                        if count:
                            self.malformed(agent)
        except (OSError, UnicodeError):
            if count:
                self.issue(agent, 'unreadable_file')

    def locate(self, cwd):
        cwd = cwd.removeprefix('file://').rstrip('/') if isinstance(cwd, str) else ''
        if not cwd:
            return 'unknown', None
        if cwd in self._projects:
            return self._projects[cwd]
        if cwd == self.cfg.home or 'scratch-workspaces' in cwd or cwd.startswith(self.cfg.home + '/Documents/Codex'):
            result = 'No-folder sessions', None
        elif cwd.startswith(('/private/tmp/', '/tmp/', '/var/folders/')):
            result = 'Background automations', None
        else:
            probe = cwd
            while probe and not os.path.isdir(probe):
                parent = os.path.dirname(probe)
                if parent == probe:
                    break
                probe = parent
            top = _git(probe, 'rev-parse', '--show-toplevel') if probe else ''
            common = _git(probe, 'rev-parse', '--path-format=absolute', '--git-common-dir') if top else ''
            if top:
                workspace = os.path.basename(top)
                c = common.rstrip('/')
                project = os.path.basename(os.path.dirname(c)) if c.endswith('/.git') else os.path.basename(c)
                result = project or workspace, workspace
            else:
                rest = os.path.relpath(cwd, probe).split(os.sep) if probe and probe != cwd else [os.path.basename(cwd)]
                result = rest[0], rest[0]
        self._projects[cwd] = result
        return result

    def session(self, agent, sid, when, cwd, surface, auto=False):
        key = f'{agent}:{sid}'
        s = self.sessions.setdefault(key, dict(agent=agent, sid=sid, first=when, last=when,
                                              cwd=cwd, surface=surface, prompts=0,
                                              project=self.locate(cwd)[0] if agent in ('codex', 'claude-code') else EXPORT_PROJECT[agent],
                                              title=None, auto=auto))
        s['first'], s['last'] = min(s['first'], when), max(s['last'], when)
        return s

    def prompt(self, agent, sid, when, text, cwd=None, surface=None, auto=False, **extra):
        if not isinstance(text, str) or not text.strip() or not self.in_window(when):
            return
        project, workspace = self.locate(cwd) if agent in ('codex', 'claude-code') else (EXPORT_PROJECT[agent], None)
        row = dict(ts=when, agent=agent, session=str(sid), text=text.strip(), project=project,
                   workspace=workspace, surface=surface, is_automation=auto, branch=None, **extra)
        row['id'] = prompt_id(row)
        if row['id'] in self._prompts:
            return
        self._prompts.add(row['id'])
        (self.automations if auto else self.prompts).append(row)
        s = self.session(agent, str(sid), when, cwd, surface, auto)
        if not auto:
            s['prompts'] += 1

    def add_tool(self, row, identity):
        if identity not in self._tools:
            self.tools.append(row)
            self._tools.add(identity)

    def usage_row(self, agent, sid, when, cwd, u, model=None, effort=None, side=False, branch=None,
                  estimated=False, method='response'):
        fields = ('input_tokens', 'cached_input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens',
                  'cache_write_input_tokens', 'output_tokens', 'reasoning_output_tokens')
        if not isinstance(u, dict) or any(type(u.get(k, 0)) not in (int, float) or not math.isfinite(u.get(k, 0)) or u.get(k, 0) < 0 for k in fields):
            self.issue(agent, 'invalid_usage')
            return
        cached = u.get('cached_input_tokens', 0) if agent == 'codex' else u.get('cache_read_input_tokens', 0)
        fresh = u.get('input_tokens', 0) - (cached if agent == 'codex' else 0)
        if fresh < 0:
            self.issue(agent, 'invalid_usage')
            return
        project, workspace = self.locate(cwd) if agent in ('codex', 'claude-code') else (EXPORT_PROJECT[agent], None)
        self.usage.append(dict(ts=when, agent=agent, session=str(sid), project=project, workspace=workspace,
                               model=model, effort=effort, side=side, branch=branch, estimated=estimated,
                               measurement=method, fresh_input=fresh, cache_read=cached,
                               cache_write=u.get('cache_creation_input_tokens', 0) + u.get('cache_write_input_tokens', 0),
                               output=u.get('output_tokens', 0), reasoning=u.get('reasoning_output_tokens', 0)))

    def claude_code(self):
        agent = 'claude-code'
        base = Path(self.cfg.home) / '.claude/projects'
        if not base.is_dir():
            return
        seen = set()
        for path in sorted(base.rglob('*.jsonl')):
            for d in self.jsonl(path, agent):
                try:
                    t, sid = d.get('type'), d.get('sessionId')
                    if t not in ('user', 'assistant'):
                        continue
                    when = timestamp(d.get('timestamp'))
                    if not self.in_window(when):
                        continue
                    if not sid or not isinstance(d.get('message'), dict):
                        raise ValueError('missing message or session')
                    cwd, surface, m = d.get('cwd'), d.get('entrypoint'), d['message']
                    self.session(agent, str(sid), when, cwd, surface)
                    if t == 'assistant':
                        mid = m.get('id') or d.get('uuid') or json.dumps(d, sort_keys=True)
                        for b in m.get('content') or []:
                            if isinstance(b, dict) and b.get('type') == 'tool_use':
                                inp = b.get('input') or {}
                                self.add_tool(dict(ts=when, agent=agent, name=b.get('name', ''), file_path=inp.get('file_path'),
                                                   skill=inp.get('skill') if b.get('name') == 'Skill' else None, session=str(sid)),
                                              (agent, sid, b.get('id') or json.dumps(b, sort_keys=True)))
                        if (sid, mid) in seen:
                            continue
                        seen.add((sid, mid))
                        u = dict(m.get('usage') or {})
                        u['reasoning_output_tokens'] = (u.get('output_tokens_details') or {}).get('thinking_tokens', 0)
                        self.usage_row(agent, sid, when, cwd, u, m.get('model'), d.get('effort'),
                                       bool(d.get('isSidechain')), d.get('gitBranch'))
                        continue
                    if d.get('isSidechain'):
                        continue
                    content = m.get('content') or ''
                    if isinstance(content, list):
                        if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content):
                            continue
                        content = '\n'.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
                    if not isinstance(content, str):
                        raise ValueError('invalid content')
                    if '[Request interrupted by user' in content:
                        continue
                    text = clean(content)
                    origin = (d.get('origin') or {}).get('kind')
                    auto = text.startswith(('<', 'Base directory for this skill', 'Caveat:', 'Another Claude session sent')) or origin in ('task-notification', 'coordinator', 'peer')
                    # Older transcripts lack origin/promptSource; a plain user message is the fallback.
                    self.prompt(agent, sid, when, text, cwd, surface, auto)
                except (ValueError, TypeError, KeyError, AttributeError):
                    self.malformed(agent)
        self.sources[agent] = 'local Claude Code transcripts'

    def codex(self):
        agent = 'codex'
        base = Path(self.cfg.home) / '.codex'
        if not base.is_dir():
            return
        history = collections.defaultdict(list)
        if (base / 'history.jsonl').exists():
            for h in self.jsonl(base / 'history.jsonl', agent):
                try:
                    when = timestamp(h.get('ts'))
                    if not isinstance(h.get('session_id'), str) or not isinstance(h.get('text'), str):
                        raise ValueError('invalid history row')
                    if self.in_window(when):
                        history[h['session_id']].append(dict(ts=when, text=h['text']))
                except (ValueError, TypeError):
                    self.malformed(agent)
        # Index files by session first; only one session's events are retained at a time.
        paths, metadata = collections.defaultdict(list), {}
        for path in sorted((base / 'sessions').rglob('*.jsonl')):
            meta = next((r.get('payload') for r in self.jsonl(path, agent, count=False) if r.get('type') == 'session_meta'), None)
            if not isinstance(meta, dict) or not (meta.get('id') or meta.get('session_id')):
                list(self.jsonl(path, agent))  # account for unreadable/malformed files
                self.issue(agent, 'missing_session_metadata')
                continue
            sid = str(meta.get('id') or meta['session_id'])
            paths[sid].append(path)
            metadata[sid] = meta
        for sid in sorted(set(paths) | set(history)):
            meta = metadata.get(sid, {})
            events, seen = [], set()
            for path in paths[sid]:
                for d in self.jsonl(path, agent):
                    try:
                        when = timestamp(d.get('timestamp'))
                        p = d.get('payload', {})
                        if not isinstance(p, dict):
                            raise ValueError('invalid payload')
                        fingerprint = json.dumps(d, sort_keys=True)
                        if fingerprint not in seen:
                            events.append((when, d.get('type'), p))
                            seen.add(fingerprint)
                    except (ValueError, TypeError):
                        self.malformed(agent)
            events.sort(key=lambda e: e[0])
            src = meta.get('source')
            auto = isinstance(src, dict) or meta.get('thread_source') == 'guardian_review' or (meta.get('originator') == 'codex_exec' and not history[sid])
            surface = {'codex-tui': 'cli', 'Codex Desktop': 'desktop', 'codex_exec': 'exec'}.get(meta.get('originator'), meta.get('originator'))
            if src == 'vscode' and surface == 'cli':
                surface = 'vscode'
            cwd, model, effort = meta.get('cwd'), None, None
            contexts, candidates, responses, counters = [], [], [], []
            response_ids = set()
            for when, kind, p in events:
                if kind == 'turn_context':
                    cwd, model, effort = p.get('cwd') or cwd, p.get('model'), p.get('effort')
                    contexts.append((when, cwd))
                if kind == 'event_msg' and p.get('type') == 'token_count' and isinstance(p.get('info'), dict):
                    counters.append((when, p['info'], cwd, model, effort))
                if not self.in_window(when):
                    continue
                if kind == 'token_usage_record':
                    rid = p.get('response_id') or json.dumps((when, p), sort_keys=True)
                    if rid not in response_ids:
                        responses.append((when, p.get('usage') or {}, cwd, model, effort))
                        response_ids.add(rid)
                elif kind == 'response_item' and p.get('type') in ('function_call', 'custom_tool_call'):
                    self.add_tool(dict(ts=when, agent=agent, name=p.get('name', ''), file_path=None, skill=None, session=sid),
                                  (agent, sid, p.get('call_id') or json.dumps((when, p), sort_keys=True)))
                elif kind == 'response_item' and p.get('type') == 'message' and p.get('role') == 'user':
                    content = p.get('content') or []
                    if not isinstance(content, list):
                        self.malformed(agent)
                        continue
                    text = ' '.join(c.get('text', '') for c in content if isinstance(c, dict) and isinstance(c.get('text', ''), str)).strip()
                    if text and not text.startswith(INJECTED):
                        candidates.append(dict(ts=when, text=text, cwd=cwd))
            # History is authoritative for typed text; match occurrences rather than dropping all rollout turns.
            unmatched = list(candidates)
            for h in sorted(history[sid], key=lambda h: h['ts']):
                matches = [p for p in unmatched if p['text'].strip() == h['text'].strip() and abs(p['ts'] - h['ts']) <= 5]
                match = min(matches, key=lambda p: abs(p['ts'] - h['ts'])) if matches else None
                hcwd = meta.get('cwd')
                for ts, location in contexts:
                    if ts <= h['ts']:
                        hcwd = location
                if match:
                    unmatched.remove(match)
                    hcwd = match['cwd']
                self.prompt(agent, sid, h['ts'], h['text'], hcwd, surface, auto)
            for p in unmatched:
                self.prompt(agent, sid, p['ts'], p['text'], p['cwd'], surface, auto)
            if history[sid] and not paths[sid]:
                self.issue(agent, 'history_without_rollout')
            before = len(self.usage)
            if responses:
                for when, u, cwd, model, effort in responses:
                    self.usage_row(agent, sid, when, cwd, u, model, effort, auto or model == 'codex-auto-review')
                    self.session(agent, sid, when, cwd, surface, auto)
            # Cumulative counters provide a window delta, never a lifetime total mislabeled as weekly usage.
            previous = None
            fallback_total = 0
            comparable = True
            for when, info, cwd, model, effort in counters:
                current = info.get('total_token_usage')
                if not isinstance(current, dict):
                    self.issue(agent, 'invalid_token_counter')
                    comparable = False
                    continue
                fields = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens')
                if any(type(current.get(k, 0)) not in (int, float) or not math.isfinite(current.get(k, 0)) or current.get(k, 0) < 0 for k in fields):
                    self.issue(agent, 'invalid_token_counter')
                    comparable = False
                    continue
                delta = None
                if previous is not None:
                    delta = {k: current.get(k, 0) - previous.get(k, 0) for k in fields}
                    if any(v < 0 for v in delta.values()):
                        delta = None
                        comparable = False
                        if self.in_window(when):
                            self.issue(agent, 'token_counter_reset')
                elif self.in_window(when):
                    # First observed counter: only its last response can safely be attributed to this window.
                    delta = info.get('last_token_usage')
                    if not isinstance(delta, dict):
                        comparable = False
                        self.issue(agent, 'missing_counter_baseline')
                    elif any(current.get(k, 0) != delta.get(k, 0) for k in fields):
                        comparable = False
                        self.issue(agent, 'partial_counter_baseline')
                previous = current
                if not self.in_window(when) or not isinstance(delta, dict) or not any(delta.values()):
                    continue
                if any(type(delta.get(k, 0)) not in (int, float) or not math.isfinite(delta.get(k, 0)) or delta.get(k, 0) < 0 for k in fields):
                    self.issue(agent, 'invalid_token_counter')
                    comparable = False
                    continue
                fallback_total += delta.get('input_tokens', 0) + delta.get('output_tokens', 0)
                if not responses:
                    self.usage_row(agent, sid, when, cwd, delta, model, effort, auto,
                                   method='counter_delta')
                    self.session(agent, sid, when, cwd, surface, auto)
            actual = sum(u['fresh_input'] + u['cache_read'] + u['output'] for u in self.usage[before:])
            if responses and counters and comparable and actual != fallback_total:
                self.issue(agent, 'usage_cross_check_mismatch')
            if len(self.usage) == before and (history[sid] or candidates):
                self.issue(agent, 'usage_unavailable')
            self.codex_checks.append(dict(session=sid, measured=actual, counter_window=fallback_total if comparable and counters else None))
        self.sources[agent] = 'local Codex transcripts and typed history'

    def export_data(self, path):
        if path.suffix.lower() == '.zip':
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist() if n.rsplit('/', 1)[-1] == 'conversations.json']
                if not names:
                    return None, None
                member = z.getinfo(names[0])
                if member.file_size > MAX_EXPORT_BYTES:
                    raise ValueError('export too large')
                coverage = None
                coverage_path = names[0].rsplit('/', 1)[0] + '/coverage.json' if '/' in names[0] else 'coverage.json'
                if coverage_path in z.namelist():
                    if z.getinfo(coverage_path).file_size > 1024 * 1024:
                        raise ValueError('coverage too large')
                    coverage = json.loads(z.read(coverage_path))
                return json.loads(z.read(member)), coverage
        if path.stat().st_size > MAX_EXPORT_BYTES:
            raise ValueError('export too large')
        with path.open(encoding='utf-8') as f:
            return json.load(f), None

    def exports(self):
        agents = self.cfg.sources & {'chatgpt', 'claude-ai'}
        if not agents:
            return
        downloads = Path(self.cfg.home) / 'Downloads'
        candidates = [Path(p).expanduser() for p in self.cfg.exports] if self.cfg.exports else list(downloads.glob('*.zip')) + list(downloads.glob('*.json'))
        # Newest readable export per agent; only one parsed export is held at a time.
        candidates = sorted(candidates, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        for path in candidates:
            if path.name == 'chatgpt-self-report.json':
                continue
            for agent in agents:
                self.diagnostics[agent]['files_discovered'] += 1
            try:
                data, coverage = self.export_data(path)
                if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                    continue
                agent = 'chatgpt' if 'mapping' in data[0] else 'claude-ai' if 'chat_messages' in data[0] else None
                if agent not in agents or agent in self.sources:
                    continue
                self.diagnostics[agent]['files_read'] += 1
                self.sources[agent] = path.name
                self.provenance[agent] = dict(coverage=coverage, label='app history, may be incomplete' if coverage is not None else 'export; completeness unverified',
                                             branch_policy='active path; separate leaf paths when current_node is unavailable')
                for conv in data:
                    try:
                        self.conversation(agent, conv)
                    except (ValueError, TypeError, AttributeError, KeyError):
                        self.malformed(agent)
            except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, RuntimeError):
                # Type is unknown until the file parses, so report discovery problems to requested export sources.
                for agent in agents:
                    self.issue(agent, 'unreadable_export_candidate')
        flavor = downloads / 'chatgpt-self-report.json'
        if 'chatgpt' in agents and flavor.exists():
            self.diagnostics['chatgpt']['files_discovered'] += 1
            try:
                if flavor.stat().st_mtime >= self.cfg.cut:
                    with flavor.open(encoding='utf-8') as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError('invalid self-report')
                    self.self_report = data
                    self.diagnostics['chatgpt']['files_read'] += 1
            except (ValueError, OSError, UnicodeError):
                self.issue('chatgpt', 'invalid_self_report')

    def conversation(self, agent, conv):
        cid = conv.get('id') or conv.get('conversation_id') or conv.get('uuid')
        if not cid:
            # Titles aren't unique; use content identity as a fallback.
            import hashlib
            cid = 'export_' + hashlib.sha256(json.dumps(conv, sort_keys=True).encode()).hexdigest()[:20]
        if agent == 'claude-ai':
            for m in conv.get('chat_messages') or []:
                try:
                    self.export_message(agent, str(cid), timestamp(m.get('created_at')), m.get('text') or '',
                                        'user' if m.get('sender') == 'human' else 'assistant', None)
                except (ValueError, TypeError, AttributeError):
                    self.malformed(agent)
            return
        mapping = conv.get('mapping') or {}
        if not isinstance(mapping, dict):
            raise ValueError('invalid mapping')
        current = conv.get('current_node')
        if current in mapping:
            leaves = [current]
        elif any(isinstance(n, dict) and ('parent' in n or 'children' in n) for n in mapping.values()):
            parents = {n.get('parent') for n in mapping.values() if isinstance(n, dict)}
            leaves = [k for k in mapping if k not in parents]
            if not leaves:
                raise ValueError('cyclic conversation graph')
            self.issue(agent, 'active_branch_unknown')
        else:
            # Flat app exports have no branch information.
            leaves = [None]
        counted = set()
        for leaf in leaves:
            keys, visited, key = [], set(), leaf
            if leaf is None:
                keys = list(mapping)
            else:
                while key is not None:
                    if key in visited or key not in mapping:
                        raise ValueError('invalid conversation graph')
                    visited.add(key)
                    keys.append(key)
                    key = mapping[key].get('parent')
                keys.reverse()
            sid = str(cid) if len(leaves) == 1 else f'{cid}/branch/{leaf}'
            for key in keys:
                try:
                    m = mapping[key].get('message')
                    if not m or (m.get('metadata') or {}).get('is_visually_hidden_from_conversation'):
                        continue
                    text = '\n'.join(p for p in (m.get('content') or {}).get('parts') or [] if isinstance(p, str)).strip()
                    role = (m.get('author') or {}).get('role')
                    when = timestamp(m.get('create_time') or conv.get('create_time') or 0)
                    # Shared ancestors belong to the first path only, avoiding duplicate counts and cross-branch reactions.
                    if key not in counted:
                        self.export_message(agent, sid, when, text, role, (m.get('metadata') or {}).get('model_slug'))
                        counted.add(key)
                except (ValueError, TypeError, AttributeError):
                    self.malformed(agent)

    def export_message(self, agent, sid, when, text, role, model):
        if not self.in_window(when) or not isinstance(text, str) or not text or role not in ('user', 'assistant'):
            return
        surface = 'export'
        self.session(agent, sid, when, None, surface)
        if role == 'user':
            self.prompt(agent, sid, when, text, surface=surface)
        self.usage_row(agent, sid, when, None, dict(input_tokens=len(text) // 4 if role == 'user' else 0,
                                                   output_tokens=len(text) // 4 if role == 'assistant' else 0),
                       model=model, estimated=True, method='characters_divided_by_four')

    def run(self):
        for agent, reader in [('claude-code', self.claude_code), ('codex', self.codex)]:
            if agent in self.cfg.sources:
                try:
                    reader()
                except OSError:
                    self.issue(agent, 'unreadable_source')
        try:
            self.exports()
        except OSError:
            for agent in self.cfg.sources & {'chatgpt', 'claude-ai'}:
                self.issue(agent, 'unreadable_source')
        for agent, diag in self.diagnostics.items():
            diag['usable_prompts'] = sum(p['agent'] == agent for p in self.prompts)
            diag['usage_rows'] = sum(u['agent'] == agent for u in self.usage)
            activity = diag['usable_prompts'] or diag['usage_rows']
            diag['status'] = 'partial' if diag['issues'] or diag['malformed_records'] else 'ok' if activity else 'empty' if agent in self.sources else 'absent'
        return dict(schema_version=SCHEMA_VERSION, generated=self.cfg.now, cut=self.cfg.cut,
                    sources=self.sources, provenance=self.provenance, diagnostics=self.diagnostics,
                    codex_check=dict(sessions=self.codex_checks), self_report=self.self_report,
                    prompts=sorted(self.prompts, key=lambda r: (r['ts'], r['id'])), automations=self.automations,
                    usage=self.usage, sessions=self.sessions, tools=self.tools)


def extract(settings):
    return Extractor(settings).run()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', nargs='?', default='retro_data.json')
    parser.add_argument('--home')
    parser.add_argument('--now', type=float)
    parser.add_argument('--days', default=os.environ.get('RETRO_DAYS', '7'))
    parser.add_argument('--sources', default=os.environ.get('RETRO_SOURCES', 'all'))
    parser.add_argument('--export', action='append', default=[])
    args = parser.parse_args(argv)
    try:
        settings = config(args.home, args.now, args.days, args.sources, args.export)
    except ValueError as exc:
        parser.error(str(exc))
    data = extract(settings)
    write_json(args.out, data)
    print(json.dumps(scrub_tree(dict(sources=data['sources'], diagnostics=data['diagnostics'])), indent=1))


if __name__ == '__main__':
    main()
