"""Agent Retro extractor. Version: retro-2026-09-30

Usage: python3 extract.py [out.json]
Reads local Claude Code (~/.claude/projects) and Codex (~/.codex) logs, plus claude.ai / ChatGPT
export zips found in ~/Downloads, and writes normalized rows tagged by agent. Everything stays local.
Projects are named by git repo (worktrees fold into their main repo); `workspace` is the checkout folder.
"""
import json, glob, os, re, sys, time, zipfile, subprocess, collections
from datetime import datetime

HOME = os.path.expanduser('~')
NOW = time.time()
CUT = NOW - int(os.environ.get('RETRO_DAYS', '7')) * 86400
# all = every source found on this machine; or a comma list of agent keys: claude-code, codex, chatgpt, claude-ai
SOURCES = {x.strip() for x in os.environ.get('RETRO_SOURCES', 'all').split(',') if x.strip()} or {'all'}


def wanted(agent):
    return 'all' in SOURCES or agent in SOURCES
OUT = sys.argv[1] if len(sys.argv) > 1 else 'retro_data.json'
EXPORT_PROJECT = {'chatgpt': 'ChatGPT', 'claude-ai': 'claude.ai'}

INJECTED = ('<', '# AGENTS.md', 'The following is the Codex agent history')
TAG_RE = re.compile(r'<(system-reminder|command-[a-z-]+|local-command-[a-z-]+|task-notification|ide_[a-z_]+|pasted_content[^>]*)>.*?</\1[^>]*>', re.S)


def ts(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


_proj_cache = {}
def _git(path, *args):
    try:
        return subprocess.run(['git', '-C', path, *args], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ''


def locate(cwd):
    """(project, workspace) for a working directory. project = repo (worktrees fold into their main repo);
    workspace = the worktree/checkout folder. Never a full path."""
    cwd = (cwd or '').replace('file://', '').rstrip('/')
    if not cwd:
        return ('unknown', None)
    if cwd in _proj_cache:
        return _proj_cache[cwd]
    if cwd == HOME or 'scratch-workspaces' in cwd or cwd.startswith(HOME + '/Documents/Codex'):
        res = ('No-folder sessions', None)
    elif cwd.startswith(('/private/tmp', '/tmp', '/var/folders')):
        res = ('Background automations', None)
    else:
        probe = cwd
        while probe and not os.path.isdir(probe):  # folder may have been deleted since (old worktrees)
            probe = os.path.dirname(probe)
        top = _git(probe, 'rev-parse', '--show-toplevel') if probe else ''
        common = _git(probe, 'rev-parse', '--path-format=absolute', '--git-common-dir') if top else ''
        if top:
            workspace = os.path.basename(top)
            c = common.rstrip('/')
            project = os.path.basename(os.path.dirname(c)) if (c.endswith('/.git') or os.path.basename(c).startswith('.')) else os.path.basename(c)
            project = project or workspace
        else:
            rest = os.path.relpath(cwd, probe).split(os.sep) if probe and probe != cwd else [os.path.basename(cwd)]
            workspace = project = rest[0] or os.path.basename(cwd)
        res = (project, workspace)
    _proj_cache[cwd] = res
    return res


def project_of(cwd):
    return locate(cwd)[0]


def clean(text):
    return TAG_RE.sub('', text).strip()


prompts, automations, usage, tools = [], [], [], []
sessions, cost, titles, sources = {}, {}, {}, {}


def sess(agent, sid, when, cwd, surface=None):
    key = f'{agent}:{sid}'
    s = sessions.setdefault(key, dict(agent=agent, sid=sid, first=when, last=when, cwd=cwd, surface=surface, prompts=0))
    s['first'] = min(s['first'], when); s['last'] = max(s['last'], when)
    s['cwd'] = s['cwd'] or cwd
    s['surface'] = s['surface'] or surface
    return s


# ---------------- Claude Code ----------------
def claude_code():
    seen, n = set(), 0
    for f in glob.glob(HOME + '/.claude/projects/**/*.jsonl', recursive=True):
        if os.path.getmtime(f) < CUT:
            continue
        n += 1
        for line in open(f, errors='ignore'):
            try:
                d = json.loads(line)
            except Exception:
                continue
            t, sid = d.get('type'), d.get('sessionId')
            if t == 'cost-state':
                cost[sid] = d; continue
            if t in ('custom-title', 'agent-name'):
                titles['claude-code:' + str(sid)] = d.get('customTitle') or d.get('agentName'); continue
            if t not in ('user', 'assistant') or 'timestamp' not in d:
                continue
            try:
                when = ts(d['timestamp'])
            except Exception:
                continue
            if when < CUT:
                continue
            cwd = d.get('cwd')
            s = sess('claude-code', sid, when, cwd, d.get('entrypoint'))
            if t == 'assistant':
                m = d['message']
                mid = m.get('id') or d.get('uuid')
                for b in m.get('content') or []:
                    if isinstance(b, dict) and b.get('type') == 'tool_use':
                        inp = b.get('input') or {}
                        tools.append(dict(ts=when, agent='claude-code', name=b.get('name', ''), file_path=inp.get('file_path'),
                                          skill=inp.get('skill') if b.get('name') == 'Skill' else None, session=sid))
                if mid in seen:  # one API response spans several records
                    continue
                seen.add(mid)
                u = m.get('usage') or {}
                usage.append(dict(ts=when, agent='claude-code', model=m.get('model'), effort=d.get('effort'),
                                  project=project_of(cwd), workspace=locate(cwd)[1], session=sid, side=bool(d.get('isSidechain')), branch=d.get('gitBranch'),
                                  fresh_input=u.get('input_tokens', 0) or 0, cache_read=u.get('cache_read_input_tokens', 0) or 0,
                                  cache_write=u.get('cache_creation_input_tokens', 0) or 0, output=u.get('output_tokens', 0) or 0,
                                  reasoning=(u.get('output_tokens_details') or {}).get('thinking_tokens', 0) or 0, estimated=False))
                continue
            if d.get('isSidechain'):
                continue
            c = d['message'].get('content')
            if isinstance(c, list):
                if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
                    continue
                text = '\n'.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
            else:
                text = c or ''
            if '[Request interrupted by user' in text:
                continue
            text = clean(text)
            if not text:
                continue
            origin = (d.get('origin') or {}).get('kind')
            human = origin == 'human' or d.get('promptSource') in ('typed', 'queued')
            auto = text.startswith(('<', 'Base directory for this skill', 'Caveat:', 'Another Claude session sent')) or origin in ('task-notification', 'coordinator', 'peer')
            row = dict(ts=when, agent='claude-code', surface=d.get('entrypoint'), project=project_of(cwd), workspace=locate(cwd)[1], session=sid,
                       text=text, is_automation=not (human and not auto), branch=d.get('gitBranch'))
            (automations if row['is_automation'] else prompts).append(row)
            if not row['is_automation']:
                s['prompts'] += 1
    sources['claude-code'] = f'{n} transcript files in ~/.claude/projects'


# ---------------- Codex ----------------
def codex():
    base = HOME + '/.codex'
    typed = collections.defaultdict(list)  # history.jsonl holds only what I typed; ts is epoch seconds
    for line in (open(base + '/history.jsonl', errors='ignore') if os.path.exists(base + '/history.jsonl') else []):
        try:
            h = json.loads(line)
        except Exception:
            continue
        if h.get('ts', 0) >= CUT:
            typed[h['session_id']].append(h)
    idx = {}
    if os.path.exists(base + '/session_index.jsonl'):
        for line in open(base + '/session_index.jsonl', errors='ignore'):
            try:
                r = json.loads(line); idx[r['id']] = r.get('thread_name')
            except Exception:
                pass
    cum, seen, n = {}, set(), 0
    for f in glob.glob(base + '/sessions/**/*.jsonl', recursive=True):
        if os.path.getmtime(f) < CUT:
            continue
        n += 1
        rows = []
        for l in open(f, errors='ignore'):
            try:
                rows.append(json.loads(l))
            except Exception:
                pass
        meta = next((d['payload'] for d in rows if d.get('type') == 'session_meta'), {})
        sid = meta.get('id') or meta.get('session_id')
        src = meta.get('source')
        guardian = isinstance(src, dict) or meta.get('thread_source') == 'guardian_review'
        exec_auto = meta.get('originator') == 'codex_exec' and not typed.get(sid)
        auto_session = guardian or exec_auto
        surface = {'codex-tui': 'cli', 'Codex Desktop': 'desktop', 'codex_exec': 'exec'}.get(meta.get('originator'), meta.get('originator'))
        if src == 'vscode' and surface == 'cli':
            surface = 'vscode'
        cwd = (meta.get('cwd') or '').replace('file://', '')
        titles['codex:' + str(sid)] = idx.get(sid)
        turn_model, cur = {}, (None, None)
        for d in rows:
            t, p = d.get('type'), d.get('payload') or {}
            if t == 'turn_context':
                cur = (p.get('model'), p.get('effort'))
                turn_model[p.get('turn_id')] = cur
                cwd = (p.get('cwd') or cwd).replace('file://', '')
            try:
                when = ts(d['timestamp'])
            except Exception:
                continue
            if when < CUT:
                continue
            if t == 'token_usage_record':
                rid = p.get('response_id')
                if rid in seen:
                    continue
                seen.add(rid)
                u = p.get('usage') or {}
                model, effort = turn_model.get(p.get('turn_id'), cur)
                inp, cached = u.get('input_tokens', 0) or 0, u.get('cached_input_tokens', 0) or 0
                # OpenAI input_tokens INCLUDES cached tokens; Anthropic reports them separately.
                usage.append(dict(ts=when, agent='codex', model=model, effort=effort, project=project_of(cwd), workspace=locate(cwd)[1], session=sid,
                                  side=auto_session or model == 'codex-auto-review', branch=None,
                                  fresh_input=inp - cached, cache_read=cached, cache_write=u.get('cache_write_input_tokens', 0) or 0,
                                  output=u.get('output_tokens', 0) or 0, reasoning=u.get('reasoning_output_tokens', 0) or 0, estimated=False))
                sess('codex', sid, when, cwd, surface)['auto'] = auto_session
            elif t == 'event_msg' and p.get('type') == 'token_count' and p.get('info'):
                cum[sid] = p['info'].get('total_token_usage')
            elif t == 'response_item' and p.get('type') in ('custom_tool_call', 'function_call'):
                tools.append(dict(ts=when, agent='codex', name=p.get('name', ''), file_path=None, skill=None, session=sid))
        # Codex Desktop doesn't write history.jsonl; take its typed turns from the rollout, minus injected context.
        if not typed.get(sid) and not auto_session:
            for d in rows:
                p = d.get('payload') or {}
                if d.get('type') == 'response_item' and p.get('type') == 'message' and p.get('role') == 'user':
                    text = ' '.join(c.get('text', '') for c in p.get('content') or [] if isinstance(c, dict)).strip()
                    if text and not text.startswith(INJECTED):
                        try:
                            typed[sid].append(dict(ts=ts(d['timestamp']), text=text))
                        except Exception:
                            pass
            typed[sid] = [h for h in typed[sid] if h['ts'] >= CUT]
        for h in typed.get(sid, []):
            s = sess('codex', sid, h['ts'], cwd, surface)
            s['auto'] = auto_session
            row = dict(ts=h['ts'], agent='codex', surface=surface, project=project_of(cwd), workspace=locate(cwd)[1], session=sid,
                       text=h.get('text', '').strip(), is_automation=auto_session, branch=None)
            (automations if auto_session else prompts).append(row)
            if not auto_session:
                s['prompts'] += 1
    sources['codex'] = f'{n} rollout files in ~/.codex/sessions + ~/.codex/history.jsonl'
    return cum


# ---------------- ChatGPT / claude.ai exports ----------------
def exports():
    found = []
    for f in sorted(glob.glob(HOME + '/Downloads/*.zip') + glob.glob(HOME + '/Downloads/*.json'), key=os.path.getmtime, reverse=True):
        if os.path.getmtime(f) < CUT:
            continue
        try:
            if f.endswith('.zip'):
                z = zipfile.ZipFile(f)
                names = [x for x in z.namelist() if x.endswith('conversations.json')]
                if not names:
                    continue
                data = json.loads(z.read(names[0]))
            else:
                data = json.load(open(f))
        except Exception:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict):  # identify by structure, not filename
            if 'mapping' in data[0]:
                found.append(('chatgpt', f, data))
            elif 'chat_messages' in data[0]:
                found.append(('claude-ai', f, data))
    for agent, f, data in found:
        if agent in sources or not wanted(agent):
            continue  # newest export of each kind wins
        sources[agent] = os.path.basename(f)
        proj = EXPORT_PROJECT[agent]
        for conv in data:
            cid = conv.get('id') or conv.get('conversation_id') or conv.get('uuid') or conv.get('title')
            titles[f'{agent}:{cid}'] = conv.get('title') or conv.get('name')
            if agent == 'chatgpt':
                items = []
                for node in (conv.get('mapping') or {}).values():
                    m = node.get('message')
                    if not m or (m.get('metadata') or {}).get('is_visually_hidden_from_conversation'):
                        continue
                    parts = (m.get('content') or {}).get('parts') or []
                    items.append(((m.get('author') or {}).get('role'), '\n'.join(p for p in parts if isinstance(p, str)).strip(),
                                  m.get('create_time') or conv.get('create_time') or 0, (m.get('metadata') or {}).get('model_slug')))
            else:
                items = []
                for m in conv.get('chat_messages') or []:
                    try:
                        items.append(('user' if m.get('sender') == 'human' else 'assistant', (m.get('text') or '').strip(), ts(m.get('created_at')), None))
                    except Exception:
                        pass
            for role, text, when, model in items:
                if when < CUT or not text or role not in ('user', 'assistant'):
                    continue
                s = sess(agent, cid, when, None, 'desktop' if agent == 'chatgpt' else 'web')
                human = role == 'user'
                if human:
                    prompts.append(dict(ts=when, agent=agent, surface=s['surface'], project=proj, session=cid, text=text, is_automation=False, branch=None))
                    s['prompts'] += 1
                usage.append(dict(ts=when, agent=agent, model=model, effort=None, project=proj, session=cid, side=False, branch=None,
                                  fresh_input=len(text) // 4 if human else 0, cache_read=0, cache_write=0,
                                  output=0 if human else len(text) // 4, reasoning=0, estimated=True))
    flavor = HOME + '/Downloads/chatgpt-self-report.json'
    return json.load(open(flavor)) if wanted('chatgpt') and os.path.exists(flavor) and os.path.getmtime(flavor) >= CUT else None


if wanted('claude-code') and os.path.isdir(HOME + '/.claude/projects'):
    claude_code()
codex_cum = codex() if wanted('codex') and os.path.isdir(HOME + '/.codex') else {}
self_report = exports() if wanted('chatgpt') or wanted('claude-ai') else None

for key, s in sessions.items():
    s['project'] = project_of(s['cwd']) if s['agent'] in ('claude-code', 'codex') else EXPORT_PROJECT[s['agent']]
    s['title'] = titles.get(key)
    if s['agent'] == 'claude-code':
        s['cost'] = (cost.get(s['sid']) or {}).get('totalCostUSD')

# Codex cross-check: summed per-response usage vs. last cumulative total per session
summed = sum(u['fresh_input'] + u['cache_read'] + u['output'] for u in usage if u['agent'] == 'codex')
cum_total = sum((v or {}).get('total_tokens', 0) for v in codex_cum.values())
check = dict(summed_per_response=summed, session_cumulative=cum_total)

json.dump(dict(generated=NOW, cut=CUT, sources=sources, codex_check=check, self_report=self_report,
               prompts=sorted(prompts, key=lambda r: r['ts']), automations=automations, usage=usage,
               sessions=sessions, tools=tools), open(OUT, 'w'))
print('sources', sources)
print('prompts by agent', dict(collections.Counter(p['agent'] for p in prompts)), 'automations', len(automations),
      'usage rows', len(usage), 'sessions', len(sessions))
print('codex check', check)
