"""Agent Retro deck renderer. Version: render-2026-09-30

Usage: python3 render.py <slides.json> <out.html>

slides.json = {"title": "...", "seed": 1234, "brand": "Agent Retro", "slides": [ {<component>}, ... ]}
Each slide is {"type": <component>, ...fields}. Components and their fields are documented in
reference/deck-spec.md. The renderer owns the look (riso-print palette, motion, layout); content comes only
from slides.json, so every number on screen is one the writer put there.
"""
import html, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = {'claude-code': ('Claude Code', 'var(--claude)'), 'codex': ('Codex', 'var(--codex)'),
         'chatgpt': ('ChatGPT', 'var(--chatgpt)'), 'claude-ai': ('claude.ai', 'var(--claudeai)')}
# background themes: (bg, fg, dot, mis, data-fg)
THEMES = {
    'ink': ('var(--ink)', 'var(--paper)', 'var(--yellow)', 'var(--pink)', '#fbf8f2'),
    'blue': ('var(--blue)', 'var(--paper)', 'var(--yellow)', 'var(--ink)', '#fbf8f2'),
    'yellow': ('var(--yellow)', 'var(--ink)', 'var(--orange)', 'var(--pink)', '#1d1b3f'),
    'paper': ('var(--paper)', 'var(--ink)', 'var(--blue)', 'var(--yellow)', '#1d1b3f'),
    'pink': ('var(--pink)', 'var(--ink)', 'var(--paper)', 'var(--yellow)', '#1d1b3f'),
    'orange': ('var(--orange)', 'var(--ink)', 'var(--yellow)', 'var(--paper)', '#1d1b3f'),
    'green': ('var(--green)', 'var(--paper)', 'var(--ink)', 'var(--ink)', '#fbf8f2'),
}
# slides whose charts use agent colors need a neutral background
NEUTRAL = ['ink', 'paper', 'yellow']
DEFAULT_BG = {'cold': 'ink', 'bignum': 'yellow', 'lineup': 'paper', 'ranking': 'ink', 'heatmap': 'paper', 'archetype': 'yellow',
              'outro': 'ink', 'coach': None}

e = lambda s: html.escape(str(s if s is not None else ''), quote=True)


def fmt_int(v):
    return f'{int(v):,}'


def rv(i, cls='rv'):
    return f'class="{cls}" style="--i:{i}"'


def pick_bg(slide, prev, rng, idx):
    want = slide.get('bg') or DEFAULT_BG.get(slide['type'])
    uses_agents = slide['type'] in ('lineup', 'ranking', 'heatmap', 'bignum') or slide.get('agent_colors')
    pool = NEUTRAL if uses_agents else ['blue', 'yellow', 'paper', 'pink', 'orange', 'green', 'ink']
    if want and want != prev:
        return want
    choices = [t for t in pool if t != prev]
    return rng.choice(choices)


def dots(rng):
    vert = rng.choice(['top', 'bottom']); side = 'right' if vert == 'top' else rng.choice(['right', 'left']); size = rng.randint(48, 70)  # never top-left: that's where the eyebrow sits
    return f'<div class="dots" style="width:{size}vmin;height:{size}vmin;{side}:-{size//3}vmin;{vert}:-{size//4}vmin"></div>'


def seg_bar(segments, label):
    total = sum(max(0, s['value']) for s in segments) or 1
    parts = ''.join(f'<i style="width:{max(0.3, 100 * s["value"] / total):.2f}%;background:{AGENT.get(s.get("agent"), (0, s.get("color", "var(--fg)")))[1]}"></i>' for s in segments)
    leg = ''.join(f'<span style="--c:{AGENT.get(s.get("agent"), (0, s.get("color", "var(--fg)")))[1]}">{e(s["label"])}</span>' for s in segments)
    return f'<div style="display:grid;gap:8px">{f"<div class=zoomlabel>{e(label)}</div>" if label else ""}<div class="bar" role="img" aria-label="{e(label or "")}">{parts}</div><div class="legend">{leg}</div></div>'


def tally(items, start):
    return '<div class="tally ' + 'rv" style="--i:%d">' % start + ''.join(
        f'<div><b class="num"{f" data-count={int(t[chr(118)+chr(97)+chr(108)+chr(117)+chr(101)])}" if isinstance(t.get("value"), (int, float)) and float(t["value"]).is_integer() else ""}>{e(t["value"] if not isinstance(t.get("value"), (int, float)) else fmt_int(t["value"]) if float(t["value"]).is_integer() else t["value"])}{e(t.get("suffix", ""))}</b><span>{e(t["label"])}</span></div>'
        for t in items) + '</div>'


def compare_rows(rows):
    out = '<div class="ba" role="img" aria-label="' + e('; '.join(f'{r["label"]}: {r["pct"]}%' for r in rows)) + '">'
    for i, r in enumerate(rows):
        col = 'var(--fg)' if i == 0 else 'color-mix(in srgb, var(--fg) 40%, transparent)'
        out += f'<div class="row"><span>{e(r["label"])}</span><div class="track"><i style="--w:{r["pct"]}%;--c:{col}"></i></div><b>{e(r["pct"])}% <small>{e(r.get("n_label", ""))}</small></b></div>'
    return out + '</div>'


def render_slide(s, rng):
    t = s['type']
    eb = f'<div class="eyebrow rv">{e(s.get("eyebrow", ""))}</div>' if s.get('eyebrow') else ''
    small = lambda i: f'<p class="small rv" style="--i:{i}">{e(s["small"])}</p>' if s.get('small') else ''
    lede = lambda i: f'<p class="lede rv" style="--i:{i}">{e(s["lede"])}</p>' if s.get('lede') else ''
    h2 = lambda i: f'<h2 class="riso rv" style="--i:{i}">{e(s["headline"])}</h2>' if s.get('headline') else ''
    if t == 'cold':
        return eb + f'<div class="huge rv pop" style="--i:1">{e(s["big"])}</div>' + h2(2) + lede(3) + small(4) + \
            '<div class="hint rv" style="--i:5"><b>↓</b> scroll, swipe, or press space</div>'
    if t == 'bignum':
        body = eb + f'<div class="bignum riso num rv" style="--i:1" data-count="{int(s["value"])}">{fmt_int(s["value"])}</div>' + lede(2)
        for i, b in enumerate(s.get('bars', [])):
            body += f'<div class="rv" style="--i:{3 + i}">' + seg_bar(b['segments'], b.get('label')) + '</div>'
        return body + small(6)
    if t == 'lineup':
        acts = ''.join(
            f'<div class="act rv" style="--i:{2 + i};--a:{AGENT.get(a["agent"], (0, "var(--blue)"))[1]}"><span class="role">{e(a.get("role", ""))}</span><h3>{e(AGENT.get(a["agent"], (a["agent"],))[0])}</h3>'
            f'<div class="stats"><div><b class="num">{e(a["prompts"])}</b><span>prompts</span></div><div><b class="num">{e(a["sessions"])}</b><span>sessions</span></div><div><b class="num">{e(a["tokens_label"])}</b><span>tokens</span></div></div>'
            f'<p>{e(a.get("line", ""))}</p><span class="surf">{e(a.get("surfaces", ""))}</span></div>' for i, a in enumerate(s['acts']))
        return eb + h2(1) + f'<div class="lineup">{acts}</div>' + small(6)
    if t == 'ranking':
        mx = max(sum(g['value'] for g in r['segments']) for r in s['rows']) or 1
        rows = ''
        for i, r in enumerate(s['rows']):
            segs = ''.join(f'<i style="width:{max(0.25, 100 * g["value"] / mx):.2f}%;background:{AGENT.get(g.get("agent"), (0, "var(--fg)"))[1]}"></i>' for g in r['segments'])
            rows += f'<li class="rv" style="--i:{2 + i}"><span class="r">{i + 1}</span><span class="n">{e(r["name"])}</span><span class="v">{e(r["value_label"])}</span><span class="track">{segs}</span>' + (f'<span class="meta">{e(r["meta"])}</span>' if r.get('meta') else '') + '</li>'
        agents = sorted({g.get('agent') for r in s['rows'] for g in r['segments'] if g.get('agent')})
        leg = '<div class="legend rv" style="--i:9">' + ''.join(f'<span style="--c:{AGENT[a][1]}">{AGENT[a][0]}</span>' for a in agents if a in AGENT) + '</div>' if len(agents) > 1 else ''
        return eb + h2(1) + f'<ol class="rank2">{rows}</ol>' + leg + small(10)
    if t == 'quote':
        return eb + h2(1) + f'<p class="quote rv" style="--i:2"><q>{e(s["quote"])}</q></p>' + (tally(s['tally'], 3) if s.get('tally') else '') + small(4)
    if t == 'tally':
        return eb + h2(1) + lede(2) + tally(s['tally'], 3) + small(4)
    if t == 'compare':
        return eb + h2(1) + lede(2) + f'<div class="rv" style="--i:3">{compare_rows(s["rows"])}</div>' + small(4)
    if t == 'timeline':
        items = ''.join(f'<li style="--a:{AGENT.get(x.get("agent"), (0, "var(--fg)"))[1]}"><time>{e(x["time"])}</time><span>' + (f'<em>{e(AGENT.get(x["agent"], (x["agent"],))[0])}</em>' if x.get('agent') else '') + f'{e(x["text"])}</span></li>' for x in s['items'])
        return eb + h2(1) + f'<ol class="tl rv" style="--i:2">{items}</ol>' + small(3)
    if t == 'heatmap':
        days = s['days']; hours = s.get('hours', list(range(8, 23))); cells = s['cells']
        mx = max((sum(v.values()) for v in cells.values()), default=1) or 1
        g = '<span></span>' + ''.join(f'<span class="d{" wk" if d.get("weekend") else ""}">{e(d["label"])}</span>' for d in days)
        k = 0
        for h in hours:
            g += f'<span class="h">{(("12p" if h == 12 else f"{h-12}p" if h > 12 else f"{h}a") if h % 2 == 0 else "")}</span>'
            for d in days:
                c = cells.get(f'{d["key"]}|{h}')
                style = ''
                if c:
                    tot = sum(c.values()); a = round((0.35 + 0.65 * (tot / mx) ** .5) * 100)
                    ags = sorted(c, key=lambda x: -c[x])
                    mix = lambda ag: f'color-mix(in srgb, {AGENT.get(ag, (0, "var(--yellow)"))[1]} {a}%, transparent)'
                    style = f'background:linear-gradient(135deg, {mix(ags[0])} 50%, {mix(ags[1])} 50%)' if len(ags) > 1 else f'background:{mix(ags[0])}'
                g += f'<span class="c" style="{style};--i:{k}"></span>'; k += 1
        agents = sorted({a for v in cells.values() for a in v})
        leg = ''.join(f'<span style="--c:{AGENT.get(a, (a, "var(--yellow)"))[1]}">{e(AGENT.get(a, (a,))[0])}</span>' for a in agents)
        return eb + h2(1) + lede(2) + f'<div class="heat-wrap rv" style="--i:3"><div class="heat2" style="grid-template-columns:40px repeat({len(days)}, minmax(22px,1fr))" role="img" aria-label="{e(s.get("alt", "Activity by day and hour"))}">{g}</div></div><div class="legend rv" style="--i:4">{leg}</div>' + small(5)
    if t == 'coach':
        win = s.get('kind') == 'win'
        tag = '<span class="tag"><span class="star">★</span> Win</span>' if win else '<span class="tag">↑ Level up</span>'
        head = f'<div class="lv rv">{tag}<span class="conf">{e(s.get("confidence", ""))}</span>' + (f'<span class="cite">from “{e(s["cite"])}”</span>' if s.get('cite') else '') + '</div>'
        st = s.get('stat') or {}
        if st.get('type') == 'compare':
            stat = f'<div class="rv" style="--i:2">{compare_rows(st["rows"])}</div>'
        elif st.get('type') == 'number':
            stat = f'<div class="coachnum rv" style="--i:2"><b class="num">{e(st["value"])}</b><span>{e(st["label"])}</span></div>'
        elif st.get('type') == 'quote':
            stat = f'<p class="quote rv" style="--i:2"><q>{e(st["quote"])}</q></p>' + (f'<p class="small rv" style="--i:2">{e(st["context"])}</p>' if st.get('context') else '')
        else:
            stat = ''
        return head + h2(1) + stat + f'<div class="duo2 rv" style="--i:3"><div><h4>Why it works</h4><p>{e(s["why"])}</p></div><div><h4>Try this</h4><div class="tryb"><code>{e(s["try"])}</code></div></div></div>'
    if t == 'archetype':
        ev = ''.join(f'<div><b>{e(x["value"])}</b><span>{e(x["label"])}</span></div>' for x in s['evidence'])
        return '<canvas class="confetti" aria-hidden="true"></canvas>' + eb + f'<h1 class="riso rv pop" style="--i:1">{e(s["name"])}</h1>' + \
            f'<p class="lede rv" style="--i:2;max-width:42ch;margin-inline:auto">{e(s["lede"])}</p><div class="evidence rv" style="--i:3">{ev}</div>'
    if t == 'outro':
        facts = ''.join(f'<div{" class=wide" if f.get("wide") else ""}><dt>{e(f["label"])}</dt><dd>{e(f["value"])}</dd></div>' for f in s['facts'])
        tries = ''.join(f'<li><button type="button" aria-pressed="false" aria-label="Mark done">✓</button><span>{e(x)}</span></li>' for x in s.get('tries', []))
        return f'<div class="card rv pop"><div class="eyebrow" style="opacity:.8">{e(s.get("eyebrow", ""))}</div><h3>{e(s["title"])}</h3><dl>{facts}</dl>' + \
            (f'<div class="tries"><div class="zoomlabel">Try this week</div><ul class="checks">{tries}</ul></div>' if tries else '') + '</div>' + \
            (f'<p class="footer rv" style="--i:2">{e(s["footer"])}</p>' if s.get('footer') else '')
    raise ValueError(f'unknown slide type {t!r}')


EXTRA_CSS = r'''
:root { --claude: var(--pink); --codex: var(--blue); --chatgpt: var(--green); --claudeai: var(--orange); }
.slide { --bg: var(--t-bg); --fg: var(--t-fg); --dot: var(--t-dot); --mis: var(--t-mis); }
.huge { font-size: clamp(96px, 22vw, 260px); font-weight: 800; font-stretch: 75%; line-height: .82; letter-spacing: -.035em; color: var(--yellow); text-shadow: .03em .025em 0 var(--pink), -.02em -.015em 0 var(--blue); overflow-wrap: anywhere; }
.hint { font-family: var(--mono); font-size: 13px; opacity: .7; display: flex; gap: 10px; align-items: center; }
.hint b { display: inline-block; animation: bob 1.6s ease-in-out infinite; }
@keyframes bob { 50% { transform: translateY(6px); } }
.lineup { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.act { background: var(--a); color: var(--paper); border-radius: 8px; padding: 16px 18px; display: grid; gap: 8px; align-content: start; box-shadow: 6px 6px 0 var(--ink); min-width: 0; }
.act .role { font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; opacity: .9; }
.act h3 { margin: 0; font-size: clamp(26px, 3.6vw, 38px); font-weight: 800; font-stretch: 78%; line-height: .95; }
.act .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; border-top: 1.5px solid color-mix(in srgb, var(--paper) 45%, transparent); padding-top: 8px; }
.act .stats b { display: block; font-size: 22px; font-weight: 800; font-stretch: 80%; line-height: 1; }
.act .stats span, .act .surf { font-family: var(--mono); font-size: 11px; opacity: .9; }
.act p { margin: 0; font-size: 15px; line-height: 1.35; }
.rank2 { display: grid; gap: 10px; list-style: none; margin: 0; padding: 0; }
.rank2 li { display: grid; grid-template-columns: 2.2ch minmax(0, 1fr) auto; gap: 4px 12px; align-items: baseline; }
.rank2 .r { font-family: var(--mono); font-size: 13px; opacity: .6; }
.rank2 .n { font-weight: 700; font-size: clamp(16px, 2.2vw, 21px); min-width: 0; overflow-wrap: anywhere; }
.rank2 .v { font-family: var(--mono); font-size: 13px; font-variant-numeric: tabular-nums; }
.rank2 .track { grid-column: 2 / 4; height: 12px; display: flex; gap: 2px; }
.rank2 .track i { display: block; height: 100%; min-width: 3px; border-radius: 2px; transform-origin: left; transition: transform 1s cubic-bezier(.2,.7,.2,1); transition-delay: calc(var(--i) * 110ms + .2s); }
.armed:not(.in) .rank2 .track i { transform: scaleX(0); }
.rank2 .meta { grid-column: 2 / 4; font-family: var(--mono); font-size: 12px; opacity: .7; margin-top: -3px; }
.heat-wrap { overflow-x: auto; }
.heat2 { display: grid; gap: 3px; min-width: 280px; font-family: var(--mono); font-size: 11px; }
.heat2 .h { opacity: .6; text-align: right; padding-right: 6px; align-self: center; }
.heat2 .d { text-align: center; opacity: .8; padding-bottom: 4px; line-height: 1.2; white-space: pre-line; }
.heat2 .d.wk { color: var(--codex); font-weight: 500; opacity: 1; }
.heat2 .c { height: clamp(8px, 1.8vh, 18px); border-radius: 3px; background: color-mix(in srgb, var(--fg) 7%, transparent); transition: transform .5s ease; transition-delay: calc(var(--i) * 5ms); }
.armed:not(.in) .heat2 .c { transform: scale(.2); }
.tl { list-style: none; margin: 0; padding: 0 0 0 16px; display: grid; gap: 7px; border-left: 2px solid color-mix(in srgb, var(--fg) 30%, transparent); }
.tl li { position: relative; display: grid; grid-template-columns: 8ch minmax(0, 1fr); gap: 12px; align-items: baseline; }
.tl li::before { content: ""; position: absolute; left: -23px; top: .45em; width: 12px; height: 12px; border-radius: 50%; background: var(--a); box-shadow: 0 0 0 3px var(--bg); }
.tl time { font-family: var(--mono); font-size: 13px; opacity: .8; }
.tl span { font-size: clamp(15px, 2vw, 19px); line-height: 1.3; min-width: 0; }
.tl em { font-style: normal; font-family: var(--mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; margin-right: 8px; opacity: .85; }
.ba { display: grid; gap: 10px; }
.ba .row { display: grid; grid-template-columns: 16ch minmax(0, 1fr) 11ch; gap: 12px; align-items: center; font-family: var(--mono); font-size: 13px; }
.ba .track { height: 30px; background: color-mix(in srgb, var(--fg) 12%, transparent); border-radius: 4px; overflow: hidden; }
.ba .track i { display: block; height: 100%; width: var(--w); background: var(--c); transform-origin: left; transition: transform 1.1s cubic-bezier(.2,.7,.2,1) .35s; }
.armed:not(.in) .ba .track i { transform: scaleX(0); }
.ba .row b { font-size: 20px; font-weight: 800; font-family: var(--display); font-stretch: 80%; }
.ba .row small { font: 400 11px var(--mono); }
.lv { font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.lv .tag { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: var(--fg); color: var(--bg); font-weight: 500; }
.lv .conf { padding: 3px 9px; border-radius: 999px; border: 1.5px solid currentColor; letter-spacing: .08em; }
.lv .cite { opacity: .75; text-transform: none; letter-spacing: .02em; }
.star { color: var(--yellow); }
.coachnum { display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
.coachnum b { font-size: clamp(64px, 11vw, 120px); font-weight: 800; font-stretch: 75%; line-height: .85; }
.coachnum span { font-family: var(--mono); font-size: 14px; max-width: 34ch; }
.duo2 { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); gap: 14px; }
.duo2 > div { border-top: 3px solid var(--fg); padding-top: 10px; display: grid; gap: 6px; align-content: start; min-width: 0; }
.duo2 h4 { margin: 0; font-family: var(--mono); font-size: 11px; font-weight: 500; letter-spacing: .12em; text-transform: uppercase; opacity: .8; }
.duo2 p { margin: 0; font-size: clamp(15px, 2vw, 19px); line-height: 1.35; }
.tryb { position: relative; background: color-mix(in srgb, var(--fg) 88%, var(--bg)); color: var(--bg); border-radius: 8px; padding: 12px 14px; font-family: var(--mono); font-size: 13px; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; }
.tryb code { display: block; padding-right: 72px; }
.tryb button { position: absolute; top: 8px; right: 8px; font: 500 11px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; padding: 6px 9px; border-radius: 999px; border: 0; background: var(--yellow); color: var(--ink); cursor: pointer; }
.s-arch { text-align: center; }
.s-arch .inner { justify-items: center; }
.s-arch h1 { font-size: clamp(46px, 9.5vw, 112px); }
.confetti { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; }
.evidence { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; width: 100%; text-align: left; }
.evidence div { background: var(--ink); color: var(--paper); padding: 14px 16px; border-radius: 6px; display: grid; gap: 4px; }
.evidence b { font-size: 32px; font-weight: 800; font-stretch: 78%; color: var(--yellow); line-height: 1; }
.evidence span { font-family: var(--mono); font-size: 12.5px; line-height: 1.4; }
.tries { display: grid; gap: 8px; border-top: 2px solid var(--ink); padding-top: 10px; }
.checks { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.checks li { display: flex; gap: 10px; align-items: center; font-weight: 600; font-size: clamp(14px, 1.9vw, 17px); }
.checks button { flex: 0 0 auto; width: 26px; height: 26px; border-radius: 6px; border: 2px solid var(--ink); background: transparent; color: transparent; font: 800 16px/1 var(--display); cursor: pointer; }
.checks button[aria-pressed="true"] { background: var(--ink); color: var(--yellow); }
.checks li.done span { text-decoration: line-through; text-decoration-thickness: 2px; }
.slide { height: auto; }  /* a slide taller than the screen grows instead of clipping; snap still lands on its top */
@media (max-width: 560px) { .act p, .act .surf { display: none; } .act { padding: 12px 14px; gap: 6px; } .lineup { gap: 10px; } .act h3 { font-size: 24px; } }
@media (max-width: 640px) { .duo2 { grid-template-columns: 1fr; } .ba .row { grid-template-columns: 1fr 10ch; } .ba .row .track { grid-column: 1 / -1; grid-row: 2; } .tl li { grid-template-columns: 1fr; gap: 0; } }
@media (max-height: 740px) { .slide .small { display: none; } .rank2 .meta { display: none; } }
'''

JS = r'''
(() => {
  const deck = document.getElementById('deck'), slides = [...deck.querySelectorAll('.slide')];
  const prog = document.getElementById('progress'), reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  slides.forEach(() => { const s = document.createElement('span'); s.appendChild(document.createElement('i')); prog.appendChild(s); });
  const segs = [...prog.children];
  slides.forEach((s, i) => { if (i > 0) s.classList.add('armed'); });
  slides[0].classList.add('in');
  document.querySelectorAll('.tryb').forEach(box => {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = 'Copy';
    b.addEventListener('click', ev => { ev.stopPropagation(); const code = box.querySelector('code');
      const sel = () => { const r = document.createRange(); r.selectNodeContents(code); const s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Selected'; };
      try { navigator.clipboard.writeText(code.textContent).then(() => { b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy', 1500); }, sel); } catch (_) { sel(); } });
    box.appendChild(b);
  });
  document.querySelectorAll('.checks button').forEach(b => b.addEventListener('click', ev => { ev.stopPropagation();
    const on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', on); b.closest('li').classList.toggle('done', on); }));
  const fmt = n => Math.round(n).toLocaleString('en-US');
  const countUp = el => { if (reduce || el.dataset.done) return; el.dataset.done = 1;
    const target = +el.dataset.count, t0 = performance.now(), dur = target > 1e6 ? 1800 : 1100;
    const step = t => { const p = Math.min(1, (t - t0) / dur), k = 1 - Math.pow(1 - p, 4); el.textContent = fmt(target * k); if (p < 1) requestAnimationFrame(step); else el.textContent = fmt(target); };
    requestAnimationFrame(step); };
  const confetti = cv => { if (reduce || cv.dataset.done) return; cv.dataset.done = 1;
    const ctx = cv.getContext('2d'), dpr = devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.scale(dpr, dpr);
    const cols = ['#ff4fae', '#1f6fd1', '#11a768', '#ff6b35', '#1d1b3f'];
    const ps = Array.from({ length: 160 }, () => ({ x: W / 2, y: H * .42, vx: (Math.random() - .5) * 16, vy: -Math.random() * 15 - 4, s: Math.random() * 8 + 5, r: Math.random() * 6, vr: (Math.random() - .5) * .3, c: cols[Math.random() * cols.length | 0], o: Math.random() < .35 }));
    const t0 = performance.now();
    const tick = t => { ctx.clearRect(0, 0, W, H);
      for (const p of ps) { p.vy += .38; p.vx *= .99; p.x += p.vx; p.y += p.vy; p.r += p.vr; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c;
        if (p.o) { ctx.beginPath(); ctx.arc(0, 0, p.s / 2, 0, 7); ctx.fill(); } else ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore(); }
      if (t - t0 < 4200) requestAnimationFrame(tick); else ctx.clearRect(0, 0, W, H); };
    requestAnimationFrame(tick); };
  let cur = 0;
  const setActive = i => { cur = i; const s = slides[i]; s.classList.add('in'); s.querySelectorAll('[data-count]').forEach(countUp);
    const cv = s.querySelector('.confetti'); if (cv) setTimeout(() => confetti(cv), 350);
    document.documentElement.style.setProperty('--pfg', s.dataset.fg); segs.forEach((g, j) => g.classList.toggle('done', j <= i)); };
  const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) setActive(slides.indexOf(x.target)); }), { root: deck, rootMargin: '-45% 0px -45% 0px', threshold: 0 });
  slides.forEach(s => io.observe(s)); setActive(0);
  // fallback: whenever scrolling settles, activate the slide under the middle of the screen
  let settle; const check = () => { const mid = innerHeight / 2;
    const i = slides.findIndex(s => { const r = s.getBoundingClientRect(); return r.top <= mid && r.bottom >= mid; });
    if (i >= 0 && (i !== cur || !slides[i].classList.contains('in'))) setActive(i); };
  deck.addEventListener('scroll', () => { clearTimeout(settle); settle = setTimeout(check, 90); }, { passive: true });
  const go = i => { i = Math.max(0, Math.min(slides.length - 1, i)); deck.scrollTo({ top: slides[i].offsetTop, behavior: reduce ? 'auto' : 'smooth' }); };
  document.getElementById('next').onclick = () => go(cur + 1); document.getElementById('prev').onclick = () => go(cur - 1);
  addEventListener('keydown', ev => { if (['ArrowDown', 'ArrowRight', 'PageDown', ' '].includes(ev.key)) { ev.preventDefault(); go(cur + 1); }
    else if (['ArrowUp', 'ArrowLeft', 'PageUp'].includes(ev.key)) { ev.preventDefault(); go(cur - 1); } });
  deck.addEventListener('click', ev => { if (ev.target.closest('button, a, q, .quote, .tryb')) return; const x = ev.clientX / innerWidth; if (x > .72) go(cur + 1); else if (x < .28) go(cur - 1); });
})();
'''


def main(src, out):
    spec = json.load(open(src))
    rng = random.Random(spec.get('seed', 0))
    base = open(os.path.join(HERE, '_base.css')).read()
    sections, prev = [], None
    for idx, s in enumerate(spec['slides']):
        bg = pick_bg(s, prev, rng, idx); prev = bg
        tb, tf, td, tm, dfg = THEMES[bg]
        cls = 'slide' + (' s-arch' if s['type'] == 'archetype' else '')
        inner = render_slide(s, rng)
        deco = dots(rng) if s['type'] not in ('heatmap', 'timeline', 'archetype') else ''
        sections.append(f'<section class="{cls}" data-fg="{dfg}" style="--t-bg:{tb};--t-fg:{tf};--t-dot:{td};--t-mis:{tm}">{deco}<div class="inner">{inner}</div></section>')
    page = ('<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{e(spec["title"])}</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,300..800&family=DM+Mono:wght@400;500&display=swap">\n'
            f'<style>{base}{EXTRA_CSS}</style>\n'
            '<div class="progress" id="progress" aria-hidden="true"></div>'
            f'<div class="brand">{e(spec.get("brand", "Agent Retro"))}</div>'
            '<div class="navbtns"><button id="prev" aria-label="Previous slide">↑</button><button id="next" aria-label="Next slide">↓</button></div>\n'
            '<main id="deck">\n' + '\n'.join(sections) + '\n</main>\n'
            f'<script>{JS}</script>\n')
    open(out, 'w').write(page)
    print(f'rendered {len(sections)} slides → {out} ({len(page):,} bytes)')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
