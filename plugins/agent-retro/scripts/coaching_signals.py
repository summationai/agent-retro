"""Agent Retro coaching signals. Version: retro-2026-10-05

Usage: python3 coaching_signals.py <data.json> <out.json>
  <data.json>: the extractor output (retro_data.json).
  Works from prompts alone (agent, session, ts, text, is_automation).

For every prompt I typed, it reads how my *next* message in the same session reacted:
  praise     explicit delight ("perfect", "love it", "awesome")
  proceed    accepted and moved on ("OK. now…", "let's build that", "go ahead", "yes")
  correct    course-correction ("that's not…", "why didn't you", "still broken", "stop", ALL CAPS)
  retry      the same ask sent again
  infra      outage/limits/resume chatter ("continue", "rate limited", "are you there")
  end        last prompt of the session (no reaction to read)
and tags what the prompt contained (context, the why, success criteria, plan-first, examples, steps...).
These are proxies for "worked well" — a correction means an extra round-trip, not a bad prompt.
"""
import json, os, re, sys, collections
from datetime import datetime
from bisect import bisect_left, bisect_right

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redact import scrub_secrets, scrub_tree
from io_utils import read_json, write_json
from contracts import SCHEMA_VERSION, validate_data, identify_prompts  # noqa: E402


R = lambda p: re.compile(p, re.I)
PRAISE = R(r"\b(perfect|awesome|amazing|fantastic|excellent|beautiful|brilliant|love (it|this)|great( work| job)?|nice( work)?|nailed it|exactly( right)?|works( now| great)?|that works|this works|thanks|thank you|thx|🎉|so good|wonderful)\b")
PROCEED = R(r"^(ok(ay)?|cool|yes|yep|yeah|sure|sounds good|got it|lgtm|good|alright|great)\b|^(let'?s|lets) (build|do|go|implement|ship|make|fix|continue with|try|move)|\bgo ahead\b|\b(commit|push|merge|open a pr|ship it)\b")
CORRECT = R(r"^(no|nope|nah|wrong|stop|wait|hmm+|ugh)\b|that'?s not|not what i|why (didn'?t|did|would|are) you|you didn'?t|still (doesn'?t|isn'?t|not|broken|failing|seeing|getting)|(didn'?t|doesn'?t|won'?t|isn'?t) work|\bbroke(n)?\b|\bregressed\b|\b(this is|you introduced) a regression\b|\bthe whole point\b|\bas i said\b|\bi said\b|\bagain[,:]|\bnot the point\b|\bundo\b|\brevert\b|\bthat was(n'?t)?\b.*\bwrong\b|confus")
INFRA = R(r"\b(rate[- ]?limit(ed)?|hit (its|the|my) limit|reconnect|re-?auth|resume|are you there|hello\?|say hello|timed? ?out|expired|capacity|lost connection|disconnected)\b|^(continue|please continue|keep going|done|done!|signed in|i'?m in)\b\.?$|^(whoops|oops)")

FEATURES = {
    'gives_context': lambda t: bool(re.search(r"(`[^`]+`|/[\w.-]+/[\w.-]+|https?://|\berror\b|\btraceback\b|\bline \d+|\.(py|ts|tsx|js|md|json|go|rs)\b)", t, re.I)),
    'explains_why': lambda t: bool(re.search(r"\b(because|so that|the goal|the point|ideally|i want|i'd like|we need|in order to|the issue|the problem|so we)\b", t, re.I)),
    'defines_done': lambda t: bool(re.search(r"\b(make sure|confirm|verify|test(s|ed)?\b|until|should (be|return|show|work)|deliverable|success|pass(es|ing)?\b|check that|acceptance)\b", t, re.I)),
    'sets_constraints': lambda t: bool(re.search(r"\b(don'?t|do not|without|only|must|never|avoid|no more than|keep it)\b", t, re.I)),
    'plan_first': lambda t: bool(re.search(r"(no code|don'?t (write|execute|build|implement)|without writing|plan (it|this|out)?|just (product )?thinking|before (we|you) (build|write|code)|what would it (take|entail))", t, re.I)),
    'gives_example': lambda t: bool(re.search(r"\b(e\.g\.|for example|for instance|such as|something like|along the lines of|like this)\b", t, re.I)),
    'numbered_steps': lambda t: bool(re.search(r"(^|\s)(1[.)]|1\)|step 1|first,).*(2[.)]|2\)|then|second)", t, re.I | re.S)),
    'one_at_a_time': lambda t: bool(re.search(r"\b(one at a time|one by one|in (small )?(batches|tranches)|incremental|step by step|piece by piece)\b", t, re.I)),
    'delegates_parallel': lambda t: bool(re.search(r"\b(fan out|in parallel|subagents?|spin up|several agents|an agent to)\b", t, re.I)),
    'pastes_evidence': lambda t: len(t) > 400 and bool(re.search(r"(error|exception|failed|status \d{3}|\bat [\w.]+ \(|^\s{2,}\S)", t, re.I | re.M)),
    'terse': lambda t: len(t.split()) <= 5,
    'long_brief': lambda t: len(t.split()) >= 120,
}


def to_ts(v):
    if isinstance(v, (int, float)):
        return float(v)
    return datetime.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()


def norm(t):
    return re.sub(r'\W+', ' ', (t or '').lower()).strip()


def reaction(text):
    t = (text or '').strip()
    if not t:
        return 'unknown'
    if INFRA.search(t) and len(t.split()) <= 14:
        return 'infra'
    caps = len(re.findall(r'\b[A-Z]{2,}(?:\s+[A-Z]{2,}){2,}\b', t))  # a run of 3+ ALL-CAPS words
    if CORRECT.search(t[:160]) or caps:
        return 'correct'
    if PRAISE.search(t[:120]) or t.startswith('🎉'):
        return 'praise'
    if PROCEED.search(t[:80]):
        return 'proceed'
    return 'new-ask'


def correction_chains(normalized, reactions):
    """Count corrections/retries after each ask without rescanning long correction runs."""
    n = len(normalized)
    boundaries = [i for i, r in enumerate(reactions) if r not in ('correct', 'infra')]
    ends = list(range(len(boundaries)))
    for j in range(len(boundaries) - 2, -1, -1):
        if normalized[boundaries[j]] == normalized[boundaries[j + 1]]:
            ends[j] = ends[j + 1]
    corrections = [0]
    matches = collections.defaultdict(list)
    for i, r in enumerate(reactions):
        corrections.append(corrections[-1] + (r == 'correct'))
        if r != 'correct':
            matches[normalized[i]].append(i)
    result = []
    for i, text in enumerate(normalized):
        j = bisect_right(boundaries, i)
        if j < len(boundaries) and normalized[boundaries[j]] == text:
            j = ends[j] + 1
        end = boundaries[j] if j < len(boundaries) else n
        repeated = matches[text]
        result.append(corrections[end] - corrections[i + 1]
                      + bisect_left(repeated, end) - bisect_right(repeated, i))
    return result


def measure(d, out):
    d = validate_data(d)
    P = identify_prompts([p for p in d.get('prompts', []) if not p.get('is_automation') and p.get('text')])
    sessions = collections.defaultdict(list)
    for p in P:
        sessions[(p['agent'], p['session'])].append(p)
    rows = []
    for (agent, sid), ps in sessions.items():
        ps.sort(key=lambda r: (to_ts(r['ts']), r['id']))
        normalized = [norm(p['text']) for p in ps]
        reactions = [reaction(p['text']) for p in ps]
        chains = correction_chains(normalized, reactions)
        for i, p in enumerate(ps):
            nxt = ps[i + 1] if i + 1 < len(ps) else None
            r = 'end' if not nxt else reactions[i + 1]
            if nxt and normalized[i + 1] == normalized[i]:
                r = 'retry'
            feats = [k for k, f in FEATURES.items() if f(p['text'])]
            rows.append(dict(id=p['id'], agent=agent, session=sid, ts=p['ts'], words=len(p['text'].split()),
                             features=feats, next_reaction=r, correction_chain=chains[i], text=p['text'],
                             next_text=nxt['text'] if nxt else None, next_id=nxt['id'] if nxt else None))
    rows.sort(key=lambda r: (to_ts(r['ts']), r['id']))
    # Only a different session can turn an otherwise unjudged ask into a cross-session retry.
    # Group pending rows by session, expire them after a day, and remove each matched row once.
    pending = collections.defaultdict(dict)
    for r in rows:
        if len(r['text']) < 20:
            continue
        key, session = norm(r['text']), (r['agent'], r['session'])
        groups = pending[key]
        for other, candidates in list(groups.items()):
            while candidates and to_ts(r['ts']) - to_ts(candidates[0]['ts']) >= 86400:
                candidates.popleft()
            if other != session:
                for previous in candidates:
                    previous['next_reaction'] = 'retry'
                candidates.clear()
            if not candidates:
                del groups[other]
        if r['next_reaction'] in ('end', 'new-ask', 'infra'):
            groups.setdefault(session, collections.deque()).append(r)
    # "smooth" = accepted/praised vs corrected. Repeats are reported separately: a re-sent ask is often a
    # deliberate re-run (a smoke test), which is a slash-command opportunity rather than a miss.
    judged = [r for r in rows if r['next_reaction'] in ('praise', 'proceed', 'correct')]
    good = lambda rs: sum(r['next_reaction'] in ('praise', 'proceed') for r in rs)
    rate = lambda rs: round(good(rs) / len(rs), 3) if rs else None
    base = rate(judged)

    by_feature = {}
    for f in FEATURES:
        w = [r for r in judged if f in r['features']]
        wo = [r for r in judged if f not in r['features']]
        lift = round(rate(w) - rate(wo), 3) if w and wo else None
        strata = {}
        for agent in sorted({r['agent'] for r in judged}):
            aw = [r for r in w if r['agent'] == agent]
            awo = [r for r in wo if r['agent'] == agent]
            strata[agent] = dict(with_n=len(aw), without_n=len(awo),
                                 lift=round(rate(aw) - rate(awo), 3) if aw and awo else None)
        consistent = all(v['lift'] * lift >= 0 for v in strata.values()
                         if lift is not None and v['lift'] is not None and min(v['with_n'], v['without_n']) >= 8)
        n = min(len(w), len(wo))
        confidence = ('insufficient comparison' if n == 0 else
                      'strong signal' if n >= 20 and abs(lift) >= .15 and consistent else
                      'early signal' if n >= 8 else f'small sample · {n}')
        by_feature[f] = dict(with_n=len(w), with_successes=good(w), with_rate=rate(w),
                             without_n=len(wo), without_successes=good(wo), without_rate=rate(wo),
                             lift=lift, confidence=confidence, by_agent=strata,
                             with_sessions=len({(r['agent'], r['session']) for r in w}),
                             without_sessions=len({(r['agent'], r['session']) for r in wo}),
                             usage_share=round(sum(f in r['features'] for r in rows) / max(1, len(rows)), 3))
    by_agent = {a: dict(n=len(rs), smooth_rate=rate(rs)) for a, rs in
                ((a, [r for r in judged if r['agent'] == a]) for a in sorted({r['agent'] for r in judged}))}

    # candidates for cards (the coaching pack reads the text and decides; ids point into rows)
    praised = [r['id'] for r in rows if r['next_reaction'] == 'praise']
    first_try = [r['id'] for r in rows if r['next_reaction'] == 'proceed' and r['words'] >= 25]
    loops = sorted((r for r in rows if r['correction_chain'] >= 2), key=lambda r: -r['correction_chain'])
    retries = [r['id'] for r in rows if r['next_reaction'] == 'retry']
    infra_share = round(sum(r['next_reaction'] == 'infra' for r in rows) / max(1, len(rows)), 3)

    result = dict(
        version='coaching-2026-10-05', prompts=len(rows), judged=len(judged), smooth_rate=base,
        reaction_counts=dict(collections.Counter(r['next_reaction'] for r in rows)),
        infra_share=infra_share, by_feature=by_feature, by_agent=by_agent,
        repeats=dict(prompts_resent=len(retries), distinct_texts=len({norm(r['text']) for r in rows if r['next_reaction'] == 'retry'})),
        reminders=dict(count=sum(bool(re.match(r"\W*(ok\W+)?again\b", r['text'], re.I)) or bool(re.search(r"\b(as i said|like i said|remember|reminder|again, (no|let'?s|think|make))\b", r['text'], re.I)) for r in rows),
                       note='standing instructions I re-state; candidates for AGENTS.md or your agent\'s equivalent'),
        checkins=dict(n=len(ck := [r for r in judged if r['words'] <= 15 and re.search(r"(\bright\?|^(is|are|will|does|did|do|can|should)\b[^.]*\?)\s*$", r['text'].strip(), re.I)]),
                      smooth_rate=rate(ck), note='short yes/no check-ins ("is it running?", "…right?")'),
        candidates=dict(praised=praised[:40], smooth_long_briefs=first_try[:40],
                        correction_loops=[dict(id=r['id'], chain=r['correction_chain']) for r in loops[:25]], retries=retries[:25]),
        caveat='Reactions are proxies read from my next message. A correction means an extra round-trip, not a bad prompt; '
               'lifts are correlations on small samples. Treat anything with n < 8 as an anecdote.',
    )

    # rows carry prompt text for the deck writer to look up; redact it (then truncate) on the way out
    rows = [dict(r, text=scrub_secrets(r['text']), next_text=scrub_secrets(r['next_text'])[:400] if r['next_text'] else None) for r in rows]
    safe = scrub_tree(dict(schema_version=SCHEMA_VERSION, privacy='redacted-v1', summary=result, rows=rows))
    write_json(out, safe)
    print(json.dumps({k: result[k] for k in ('prompts', 'judged', 'smooth_rate', 'reaction_counts', 'infra_share')}, indent=1))
    print('feature lifts:', {f: (v['with_n'], v['lift']) for f, v in by_feature.items()})

    return safe


def main(src, out):
    return measure(read_json(src), out)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
