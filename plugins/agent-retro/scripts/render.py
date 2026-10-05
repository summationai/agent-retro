"""Agent Retro deck renderer. Version: render-2026-10-05

Usage: python3 render.py <slides.json> <out.html>

slides.json = {"title": "...", "seed": 1234, "brand": "Agent Retro", "slides": [ {<component>}, ... ]}
Each slide is {"type": <component>, ...fields}. Components and their fields are documented in
reference/deck-spec.md. The renderer owns the look (riso-print palette, motion, layout); content comes only
from slides.json, so every number on screen is one the writer put there.
"""
import html, json, os, random, sys

from io_utils import read_json, write_text
from deck_schema import number, color, validate_deck
from pathlib import Path

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
    'green': ('var(--green)', 'var(--ink)', 'var(--paper)', 'var(--yellow)', '#1d1b3f'),
}
# slides whose charts use agent colors need a neutral background
NEUTRAL = ['ink', 'paper', 'yellow']
DEFAULT_BG = {'cold': 'ink', 'bignum': 'yellow', 'lineup': 'paper', 'ranking': 'ink', 'heatmap': 'paper', 'archetype': 'yellow',
              'outro': 'ink', 'coach': None}

e = lambda s: html.escape(str(s if s is not None else ''), quote=True)


def segment_color(segment):
    value = AGENT.get(segment.get('agent'), (None, segment.get('color', 'var(--fg)')))[1]
    return e(color(value))


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
    total = sum(number(s['value'], 'segment.value') for s in segments) or 1
    parts = ''.join(f'<i style="width:{100 * s["value"] / total:.2f}%;background:{segment_color(s)}"></i>' for s in segments)
    leg = ''.join(f'<span style="--c:{segment_color(s)}">{e(s["label"])}</span>' for s in segments)
    return f'<div style="display:grid;gap:8px">{f"<div class=zoomlabel>{e(label)}</div>" if label else ""}<div class="bar" role="img" aria-label="{e(label or "")}">{parts}</div><div class="legend">{leg}</div></div>'


def tally(items, start):
    parts = []
    for item in items:
        value = item['value']
        integer = type(value) in (int, float) and float(value).is_integer()
        counter = f' data-count="{int(value)}"' if integer else ''
        label = fmt_int(value) if integer else value
        parts.append(f'<div><b><span class="num"{counter}>{e(label)}</span>{e(item.get("suffix", ""))}</b>'
                     f'<span>{e(item["label"])}</span></div>')
    return f'<div class="tally rv" style="--i:{start}">' + ''.join(parts) + '</div>'


def compare_rows(rows):
    out = '<div class="ba" role="img" aria-label="' + e('; '.join(f'{r["label"]}: {r["pct"]}%' for r in rows)) + '">'
    for i, r in enumerate(rows):
        number(r['pct'], f'rows[{i}].pct', maximum=100)
        col = 'var(--fg)' if i == 0 else 'color-mix(in srgb, var(--fg) 40%, transparent)'
        out += f'<div class="row"><span>{e(r["label"])}</span><div class="track"><i style="--w:{e(r["pct"])}%;--c:{col}"></i></div><b>{e(r["pct"])}% <small>{e(r.get("n_label", ""))}</small></b></div>'
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
        number(s['value'], 'value', integer=True)
        body = eb + f'<div class="bignum riso num rv" style="--i:1" data-count="{int(s["value"])}">{fmt_int(s["value"])}</div>' + lede(2)
        for i, b in enumerate(s.get('bars', [])):
            body += f'<div class="rv" style="--i:{3 + i}">' + seg_bar(b['segments'], b.get('label')) + '</div>'
        return body + small(6)
    if t == 'lineup':
        acts = ''.join(
            f'<div class="act rv" style="--i:{2 + i};--a:{AGENT.get(a["agent"], (0, "var(--blue)"))[1]};--afg:{"var(--paper)" if a["agent"] == "codex" else "var(--ink)"}"><span class="role">{e(a.get("role", ""))}</span><h3>{e(AGENT.get(a["agent"], (a["agent"],))[0])}</h3>'
            f'<div class="stats"><div><b class="num">{e(a["prompts"])}</b><span>prompts</span></div><div><b class="num">{e(a["sessions"])}</b><span>sessions</span></div><div><b class="num">{e(a["tokens_label"])}</b><span>tokens</span></div></div>'
            f'<p>{e(a.get("line", ""))}</p><span class="surf">{e(a.get("surfaces", ""))}</span></div>' for i, a in enumerate(s['acts']))
        return eb + h2(1) + f'<div class="lineup">{acts}</div>' + small(6)
    if t == 'ranking':
        mx = max(sum(number(g['value'], 'segment.value') for g in r['segments']) for r in s['rows']) or 1
        rows = ''
        for i, r in enumerate(s['rows']):
            segs = ''.join(f'<i style="width:{100 * g["value"] / mx:.2f}%;background:{AGENT.get(g.get("agent"), (0, "var(--fg)"))[1]}"></i>' for g in r['segments'])
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
        for h in hours:
            number(h, 'hours[]', maximum=23, integer=True)
        mx = max((sum(number(n, 'cells count') for n in v.values()) for v in cells.values()), default=1) or 1
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


def main(src, out):
    spec = validate_deck(read_json(src))
    rng = random.Random(spec.get('seed', 0))
    base = Path(HERE, '_base.css').read_text(encoding='utf-8')
    components = Path(HERE, '_components.css').read_text(encoding='utf-8')
    js = Path(HERE, '_deck.js').read_text(encoding='utf-8')
    sections, prev = [], None
    for idx, s in enumerate(spec['slides']):
        bg = pick_bg(s, prev, rng, idx); prev = bg
        tb, tf, td, tm, dfg = THEMES[bg]
        cls = 'slide' + (' s-arch' if s['type'] == 'archetype' else '')
        inner = render_slide(s, rng)
        deco = dots(rng) if s['type'] not in ('heatmap', 'timeline', 'archetype') else ''
        sections.append(f'<section class="{cls}" data-fg="{dfg}" style="--t-bg:{tb};--t-fg:{tf};--t-dot:{td};--t-mis:{tm}">{deco}<div class="inner">{inner}</div></section>')
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{e(spec["title"])}</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,300..800&family=DM+Mono:wght@400;500&display=swap">\n'
            f'<style>{base}{components}</style>\n'
            '</head><body><div class="progress" id="progress" aria-hidden="true"></div>'
            f'<div class="brand">{e(spec.get("brand", "Agent Retro"))}</div>'
            '<div class="navbtns"><button id="prev" aria-label="Previous slide">↑</button><button id="next" aria-label="Next slide">↓</button></div>\n'
            '<main id="deck">\n' + '\n'.join(sections) + '\n</main>\n'
            f'<script>{js}</script></body></html>\n')
    write_text(out, page)
    print(f'rendered {len(sections)} slides → {out} ({len(page):,} bytes)')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    try:
        main(sys.argv[1], sys.argv[2])
    except ValueError as exc:
        sys.exit(f'Invalid deck: {exc}')
