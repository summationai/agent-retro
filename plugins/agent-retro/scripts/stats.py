"""Agent Retro standard stats. Version: retro-2026-10-05

Usage: python3 stats.py <data.json> <out.json>
<data.json> is the extractor output (prompts, usage, sessions, tools). Everything here is deterministic;
the deck-writing step picks which of these to show and writes the copy.
"""
import json, os, re, sys, collections, statistics
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redact import scrub_secrets, scrub_tree, REDACTIONS  # noqa: E402
from contracts import SCHEMA_VERSION, validate_data, identify_prompts
from io_utils import read_json, write_json, write_text


def lt(v):  # local datetime from epoch seconds or ISO
    return (datetime.fromtimestamp(v) if isinstance(v, (int, float)) else datetime.fromisoformat(str(v).replace('Z', '+00:00'))).astimezone()


def measure(d, out):
    REDACTIONS.clear()
    d = validate_data(d)
    P = sorted(identify_prompts([p for p in d['prompts'] if not p.get('is_automation') and p.get('text')]), key=lambda p: (lt(p['ts']), p['id']))
    U = d['usage']; T = d.get('tools', []); S = d.get('sessions', {})
    S = list(S.values()) if isinstance(S, dict) else S
    tok = lambda u: u['fresh_input'] + u['cache_read'] + u['cache_write'] + u['output']
    agents = sorted({p['agent'] for p in P} | {u['agent'] for u in U})

    by_type = collections.Counter()
    for u in U:
        for k in ('fresh_input', 'cache_read', 'cache_write', 'output', 'reasoning'):
            by_type[k] += u[k]
    total = sum(tok(u) for u in U)
    by_agent = {a: dict(tokens=sum(tok(u) for u in U if u['agent'] == a), output=sum(u['output'] for u in U if u['agent'] == a),
                        estimated=any(u.get('estimated') for u in U if u['agent'] == a),
                        usage_status=d.get('diagnostics', {}).get(a, {}).get('status', 'unverified'),
                        prompts=sum(p['agent'] == a for p in P),
                        sessions=len({p['session'] for p in P if p['agent'] == a}),
                        surfaces=dict(collections.Counter(p.get('surface') for p in P if p['agent'] == a)))
                for a in agents}
    models = collections.defaultdict(lambda: collections.Counter())
    for u in U:
        if u.get('model') and u['model'] != '<synthetic>':
            models[u['model']]['tokens'] += tok(u); models[u['model']]['output'] += u['output']

    proj = collections.defaultdict(lambda: dict(tokens=0, by_agent=collections.Counter(), prompts=0, sessions=set()))
    for u in U:
        proj[u['project']]['tokens'] += tok(u); proj[u['project']]['by_agent'][u['agent']] += tok(u)
    for p in P:
        proj[p['project']]['prompts'] += 1; proj[p['project']]['sessions'].add((p['agent'], p['session']))
    projects = sorted((dict(project=k, tokens=v['tokens'], by_agent=dict(v['by_agent']), prompts=v['prompts'], sessions=len(v['sessions']))
                       for k, v in proj.items()), key=lambda x: -x['tokens'])[:10]

    words_typed = sum(len(p['text'].split()) for p in P)
    out_tokens = by_type['output']

    grid_out, grid_p = collections.Counter(), collections.Counter()
    for u in U:
        t = lt(u['ts']); grid_out[f"{t:%Y-%m-%d}|{t.hour}"] += u['output']
    for p in P:
        t = lt(p['ts']); grid_p[f"{t:%Y-%m-%d}|{t.hour}|{p['agent']}"] += 1
    busiest = max(grid_out.items(), key=lambda x: x[1]) if grid_out else None
    prompts_in_busiest = sum(v for k, v in grid_p.items() if busiest and k.startswith(busiest[0] + '|'))
    weekend = sum(lt(p['ts']).weekday() >= 5 for p in P)
    latest = max(P, key=lambda p: (lt(p['ts']).hour - 5) % 24) if P else None
    per_day = collections.Counter(f"{lt(p['ts']):%a %Y-%m-%d}" for p in P)

    norm = lambda t: re.sub(r'\s+', ' ', t.strip().lower())
    rep = collections.Counter(norm(p['text']) for p in P if len(p['text']) >= 20)
    # show the first original wording, redacted: the lowercased key would hide secrets from case-sensitive patterns
    original = lambda t: next(p['text'] for p in P if norm(p['text']) == t)
    repeats = [dict(text=scrub_secrets(original(t))[:200], times=n, agents=sorted({p['agent'] for p in P if norm(p['text']) == t})) for t, n in rep.most_common(5) if n >= 2]

    # Redact before stripping punctuation/case, which can disguise credentials.
    openers = [scrub_secrets(p['text']).split()[0] for p in P if p['text'].split()]
    first = collections.Counter(re.sub(r"[^a-z']", '', word.lower()) for word in openers
                                if not any(marker in word for marker in ('[redacted', '[email]', '[phone]')))
    first.pop('', None)
    voice = {}
    for a in agents:
        ps = [p for p in P if p['agent'] == a]
        if not ps:
            continue
        caps = sum(bool(re.search(r'\b[A-Z]{2,}(?:\s+[A-Z]{2,}){2,}\b', p['text'])) for p in ps)
        voice[a] = dict(n=len(ps), question_share=round(sum('?' in p['text'] for p in ps) / len(ps), 3),
                        median_words=statistics.median(len(p['text'].split()) for p in ps),
                        please_share=round(sum(bool(re.search(r'\bplease\b', p['text'], re.I)) for p in ps) / len(ps), 3),
                        ok_open_share=round(sum(bool(re.match(r'(ok|okay)\b', p['text'].lower())) for p in ps) / len(ps), 3),
                        caps_sentences=caps)
    thanks = sum(bool(re.search(r'\b(thanks|thank you|thx)\b', p['text'], re.I)) for p in P)

    seq = [p['agent'] for p in P]
    handoffs = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i - 1])
    streak, best = 1, (1 if seq else 0, seq[0] if seq else None)
    for i in range(1, len(seq)):
        streak = streak + 1 if seq[i] == seq[i - 1] else 1
        if streak > best[0]:
            best = (streak, seq[i])
    side = sum(tok(u) for u in U if u.get('side'))
    tool_counts = collections.Counter(t['name'] for t in T)
    mcp = collections.Counter(t['name'].split('__')[1] for t in T if t['name'].startswith('mcp__') and t['name'].count('__') >= 2)
    skills = collections.Counter(t.get('skill') for t in T if t.get('skill'))
    files = collections.Counter((t.get('file_path') or '').rsplit('/', 1)[-1] for t in T if t['name'] in ('Edit', 'Write', 'MultiEdit') and t.get('file_path'))
    branches = collections.Counter(u.get('branch') for u in U if u.get('branch') and u['branch'] not in ('HEAD', 'main', 'master'))
    sess_len = sorted(((s.get('last', 0) - s.get('first', 0)) / 3600, s.get('project'), s.get('agent'), s.get('prompts', 0))
                      for s in S if isinstance(s.get('first'), (int, float)))[-3:]

    res = dict(
        schema_version=SCHEMA_VERSION, version='stats-2026-10-05', sources=d.get('sources'), codex_check=d.get('codex_check'),
        diagnostics=d.get('diagnostics', {}), provenance=d.get('provenance', {}),
        self_report=dict(flavor_only=True, content=d['self_report']) if d.get('self_report') else None,
        window=dict(start=str(lt(d['cut'])), end=str(lt(d['generated']))) if 'cut' in d else None,
        tokens=dict(total=total, by_type=dict(by_type), cache_read_share=round(by_type['cache_read'] / max(1, by_type['cache_read'] + by_type['fresh_input'] + by_type['cache_write']), 4)),
        agents=by_agent, models={m: dict(v) for m, v in sorted(models.items(), key=lambda x: -x[1]['tokens'])},
        prompts=len(P), sessions_driven=len({(p['agent'], p['session']) for p in P}),
        words_typed=words_typed, words_back_est=round(out_tokens * 0.75), leverage=round(out_tokens * 0.75 / max(1, words_typed)),
        projects=projects,
        clock=dict(busiest_output_hour=busiest[0] if busiest else None, busiest_output_tokens=busiest[1] if busiest else 0,
                   prompts_in_busiest_hour=prompts_in_busiest, weekend_prompts=weekend,
                   latest_prompt=str(lt(latest['ts'])) if latest else None, prompts_per_day=dict(per_day),
                   grid_output=dict(grid_out), grid_prompts=dict(grid_p)),
        repeats=repeats, first_words=first.most_common(10), voice=voice, thanks=thanks,
        please_total=sum(len(re.findall(r'\bplease\b', p['text'], re.I)) for p in P),
        handoffs=handoffs, longest_streak=dict(prompts=best[0], agent=best[1]),
        subagent_token_share=round(side / max(1, total), 4), top_tools=tool_counts.most_common(12), mcp_servers=mcp.most_common(8),
        skills=skills.most_common(8), most_edited_files=files.most_common(5), branches=branches.most_common(8), longest_sessions=sess_len,
    )
    res = scrub_tree(res)
    # a compact, redacted digest of every prompt, for the deck writer to read. Redact before truncating,
    # so a secret that straddles the cut can't leak its first half.
    digest = []
    for i, p in enumerate(P):
        digest.append(f"[{p['id']}] {lt(p['ts']):%a %m-%d %H:%M} | {scrub_secrets(p['agent'])} | {scrub_secrets(p['project'])} | {len(p['text'].split())}w | {scrub_secrets(p['text'])[:400].replace(chr(10), ' / ')}\n")
    write_text(os.path.join(os.path.dirname(os.path.abspath(out)), 'prompts.txt'), ''.join(digest))
    res['redactions'] = dict(REDACTIONS)
    write_json(out, res)
    print(json.dumps(dict(prompts=res['prompts'], tokens=total, agents={a: (v['prompts'], v['tokens']) for a, v in res['agents'].items()},
                          top_project=res['projects'][0]['project'] if res['projects'] else None, repeats=[(r['times'], r['text'][:50]) for r in repeats],
                          handoffs=handoffs, streak=res['longest_streak'], redactions=res['redactions']), indent=1))

    return res


def main(src, out):
    return measure(read_json(src), out)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
