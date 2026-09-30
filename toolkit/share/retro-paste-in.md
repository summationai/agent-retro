# Agent Retro (paste-in edition)

> **What this is:** a playful recap of your last 7 days with AI agents: Claude Code, Codex, and (optionally) ChatGPT and claude.ai. You get a private, animated slide deck, and it's different every week.
>
> **How to use it:**
> 1. *(Optional)* To include chat apps, request their official exports and leave the zips in `~/Downloads`. For ChatGPT, go to **Settings → Data controls → Export data**. For claude.ai, go to **Settings → Privacy → Export data**. Both arrive by email. You can also run the ChatGPT prompt in **Appendix A** to add some flavor.
> 2. Open a coding agent that can run shell commands on your machine (Claude Code, Codex, or similar), start a session with any folder or none, and **paste this entire file**.
> 3. Run it weekly. It keeps its memory in `~/agent-outputs/agent-retro/`, so later decks compare against earlier weeks and rotate in new slides.
>
> Everything is read locally. Your agent reads your prompts to write the deck, and sends them to its model provider as it would for any other task. The deck itself is published only as a private page that only you can open until you share it, if your agent can publish one. Works on macOS and Linux.
>
> *Note for the agent: Appendix A is for the human to paste into ChatGPT. Don't act on it. Appendix B is the extraction script to use in Phase 1.*

---

Make me this week's **Agent Retro**: a playful, multi-slide infographic of how I used my AI agents (Claude Code, claude.ai, Codex, and ChatGPT) over the **last 7 days**, published as a private page. It should surprise me. If I ran it on the same data twice, I'd want different insights at least some of the time. When the data is new, I want new slides alongside a few returning favorites, not just the same deck with new numbers. Claude is still the headliner, and the other agents are the supporting cast. The most interesting stories are usually about how I split work between them.

Work through the phases below in order, and don't stop to ask me questions unless you're blocked. If a source is missing, skip it and say so on the final slide instead of stopping.

---

## Phase 1 — Gather the data (be precise, it's easy to get wrong)

Save the script in **Appendix B** to `~/agent-outputs/agent-retro/extract.py`, exactly as written, creating the folder if needed. If a file already exists there, compare the `Version:` line in its docstring. Keep whichever is newer, and never overwrite a newer or locally edited script with an older one. Run it with `python3 ~/agent-outputs/agent-retro/extract.py <scratch>/retro_data.json`. It reads everything locally and writes one normalized file, with each row tagged by `agent` (`claude-code`, `claude-ai`, `codex` or `chatgpt`). The script already handles the pitfalls listed below. They're here so you can **fix the script minimally** if a log format has changed since it was written, and so you know what the fields mean. Don't rewrite it from scratch. Projects are named by git repo, so worktrees fold into their main repo, and `workspace` holds the checkout folder name.

- **prompt**: `ts`, `agent`, `surface` (cli, desktop, vscode, web), `project`, `workspace`, `session`, `text`, `is_automation`
- **usage**: `ts`, `agent`, `model`, `effort`, `project`, `workspace`, `session`, `fresh_input`, `cache_read`, `cache_write`, `output`, `reasoning`, `estimated` (bool)
- **tool**: `ts`, `agent`, `name`, `file_path` (optional)

Record timestamps in **my local timezone**. Group projects by `cwd`, the same way for every agent, so that one repo worked on in both Claude Code and Codex becomes **one project with a per-agent split**. Collapse git worktrees and scratch/"no folder" workspaces into sensible project names. Use a repo's basename, and combine all scratch sessions as "No-folder sessions".

### Claude Code (local)
Transcripts are in `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl`. Subagent transcripts are in `.../<sessionId>/subagents/*.jsonl`. Include only files modified in the last 7 days, then filter each record by its `timestamp`. These are the known pitfalls:

- **Real prompts from me** are `type == "user"` records where `isSidechain` is false, `origin.kind == "human"` (or `promptSource` is `typed`/`queued`), and the content is text rather than `tool_result`. Remove any `<system-reminder>…</system-reminder>`, `<command-…>` and other injected tags before analyzing the text. Put these in their own "automations" bucket, and don't count them as my voice:
  - prompts sent by automation, such as skills or workspace-manager dispatches with `promptSource: "sdk"` and templated text
  - peer-session messages
  - the zero-prompt sessions in `/private/tmp`
- **Token usage** comes from `type == "assistant"` records at `message.usage`: `input_tokens` → fresh_input, `cache_read_input_tokens` → cache_read, `cache_creation_input_tokens` → cache_write, `output_tokens` → output, and `output_tokens_details.thinking_tokens` → reasoning. **Deduplicate by `message.id`**, because one API response is written across several records and counting every record roughly doubles the totals. Also record `message.model`, `effort`, `gitBranch`, `cwd` and `entrypoint`.
- **Cost and lines changed**: take `type == "cost-state"` records and keep the last one per session. Coverage is patchy, so only show dollars or lines if nearly every session reports them.
- **Tools**: collect the `tool_use` blocks inside assistant content. Subagent usage shows up as sidechain records.
- `~/.claude/history.jsonl` is a clean log of typed prompts. Use it to cross-check.

### Codex (local)
- **Sessions** are in `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`. Each line is `{timestamp, type, payload}`.
  - `session_meta` gives `cwd`, `originator` (codex-tui, Codex Desktop, codex_exec), and `source`.
  - `turn_context` gives `model` and `effort` for each turn.
- **Real prompts from me**: use `~/.codex/history.jsonl` (`session_id`, `ts` in epoch *seconds*, `text`). It contains only what I typed. **Codex Desktop sessions don't write to history.jsonl.** For any non-automation session with no history entries, take the `response_item` user messages from its rollout instead, and drop injected ones: anything starting with `<`, `# AGENTS.md`, or `The following is the Codex agent history`. Treat Desktop working directories under `~/Documents/Codex/` as "No-folder sessions".
- **Automations**: treat these as automation, not my voice or my sessions:
  - sessions whose `source` is a subagent (for example `{"subagent": …"guardian"}`) or whose `thread_source` is `guardian_review`
  - turns on the `codex-auto-review` model
  - `codex_exec` sessions that have no matching entry in history.jsonl, since those are usually scripts or other agents calling Codex
- **Token usage**: `token_usage_record` lines hold per-response `usage`. **Deduplicate by `response_id`**, then window by timestamp. `event_msg` / `token_count` lines hold a *cumulative* `total_token_usage` per session. Use it only as a cross-check against your summed per-response numbers, and report any mismatch over 5% in chat.
- **Critical normalization:** OpenAI's `input_tokens` **already includes** `cached_input_tokens`. So `fresh_input = input_tokens − cached_input_tokens` and `cache_read = cached_input_tokens`. Map `reasoning_output_tokens` → reasoning, and `cache_write_input_tokens` → cache_write. Anthropic reports these the other way (cache reads are separate from input). If you skip this, Codex's cache share and all per-agent comparisons will be wrong.
- **Tools**: collect `custom_tool_call` / `function_call` names. `~/.codex/session_index.jsonl` has thread titles.

### claude.ai and ChatGPT (optional data exports)
Look in `~/Downloads` for recent export zips or JSON files, and identify each one by its **structure**, not its filename. Some files in Downloads may have been **made by another agent** rather than by the official export. Check any `source`, `scope_note` or `coverage` fields they carry, and say on the final slide how complete each source is. When such a file summarizes data you can read directly (for example, a Codex summary built from `~/.codex`), read the original and use the file only to cross-check. claude.ai conversations have `chat_messages`. ChatGPT's `conversations.json` is a list of conversations, each with a `mapping` of message nodes.

- **Inspect the schema first**, because both formats change over time. Then take my human turns from the last 7 days.
  - claude.ai: `sender == "human"`.
  - ChatGPT: `author.role == "user"`. Walk the `mapping` tree, skip nodes where `metadata.is_visually_hidden_from_conversation` is set, and skip system or tool messages. Take the model from `metadata.model_slug` on the assistant nodes.
- **Put each chat under a project:** use its ChatGPT Project if it has one, or else a topic cluster you infer from the conversation titles.
- Exports have **no token counts**. Estimate them at about 4 characters per token, set `estimated: true`, and label them as estimates everywhere they appear. Never mix estimated and measured tokens in one headline number without saying so.
- Also use `~/Downloads/chatgpt-self-report.json` if it exists (see Appendix A). It's ChatGPT describing me from its memory. Treat it as **flavor only**: it can inspire a slide or a line of copy, but no number may come from it.
- For each agent that has no export, add one small line on the final slide saying how to include it next time:
  - claude.ai: Settings → Privacy → Export data
  - ChatGPT: Settings → Data controls → Export data

Once the script runs, **actually read all of my real prompts, from every agent**. There are usually only a few hundred. The best insights come from reading them, not from counting them.

## Phase 2 — Load memory from past Retros

Keep a persistent folder at `~/agent-outputs/agent-retro/`:

- `runs.jsonl`: one line per past run, with the date, the random seed, the slide IDs used, the headline stat for each slide, and the week's key numbers. From v2 on, also record the numbers **per agent**. Older runs are Claude Code-only, so compare against them only on Claude numbers.
- `lenses.md`: the growing catalog of insight "lenses". Add the cross-agent lenses below to it if they aren't there yet.
- `extract.py`: the extraction script (see Phase 1).
- `retro-YYYY-MM-DD.html`: a local copy of each deck.

Use this history in three ways. First, compute **week-over-week deltas** for the key numbers. Second, **avoid repeating** a lens that has been used in both of the last two runs unless this week's data makes it dramatically more interesting. Third, **compare me to my own past weeks** ("your most-polite week yet", "your most Codex-heavy week so far").

## Phase 3 — Choose this week's slides

Start by picking a random seed and printing it, so a run can be reproduced. Use it to break ties and drive creative choices.

**Fixed anchor slides**, which appear every week and act as the old favorites:
1. **Cold open.** A single striking number or phrase that stands for the week, not just a generic title.
2. **The big number.** Total tokens across all agents. Split them into fresh input, cache read, cache write, output and reasoning, and also show a per-agent split. Include a relatable comparison and the change from last week. Mark any estimated portion.
3. **Your rotation.** My agent lineup, like a band roster: each agent's share of my prompts, sessions and tokens, and the surfaces I used it on (CLI, desktop, VS Code, web). Give each agent a one-line "role" based on what I actually used it for ("the builder", "the second opinion").
4. **Top projects.** Projects ranked by tokens, drawn as a "Top Artists" countdown. Each bar is **stacked by agent**, and each project shows sessions and prompts.
5. **Your AI archetype.** Give the week a named persona, like a personality-quiz result. Invent a new name every week, backed by 2–3 pieces of real evidence. At least one piece of evidence should come from how I split work between agents, when more than one agent was used.
6. **Outro / share card.** A compact summary of the week on one card, including the lineup.

**Rotating slides** (6–9 of them): score every lens in `lenses.md` against this week's data for *surprise × strength of evidence × novelty*. Novelty is lower if the lens appeared recently. Take the top scorers, and use the seed to break near-ties. When more than one agent was used, **at least two rotating slides should be cross-agent lenses**. **Also invent at least one brand-new lens** that isn't in the catalog, based on something unusual in this week's data, and append it to `lenses.md` so it can come back in later weeks.

**Starter lens catalog** (seed `lenses.md` with any of these that are missing).

Single-agent lenses (from v1; any of them can also be split by agent):
- *First words*: a leaderboard of the words I start prompts with.
- *Politeness index*: how often I say please/thanks/sorry, and whether it drifts by project, agent or time of day.
- *Catchphrases*: recurring 2–4 word phrases that are distinctly mine.
- *Signature vocabulary*: words I use far more often than general English does. (Use a common-word baseline and say which one.)
- *On repeat*: exact or near-duplicate prompts I sent more than once, and the task I keep coming back to.
- *Question vs. command*: my ratio of questions to instructions.
- *The epic*: my longest prompt, shown as an excerpt with its word count. Plus my shortest prompt that still worked.
- *Plot twist*: a project or topic that appeared suddenly, or one that went quiet.
- *Genres*: my prompts classified by task type, shown as a genre mix.
- *Clock*: an hour × day heatmap, my latest-night prompt, and my longest streak.
- *Night shift*: tokens produced in hours when I sent no prompts.
- *Marathon*: the longest session by wall-clock time, turns or tokens.
- *Course corrections*: how often I push back ("no", "actually", "undo", interruptions).
- *The crew*: subagents launched, skills and slash commands used, and my top MCP tools.
- *Hands on the keyboard*: top tools, most-touched files, and languages.
- *Cache wizard*: cache-read share of input tokens.
- *Model mix*: models and effort levels, and share of tokens vs. share of output.
- *Branch names*: the most colorful git branch names; most-edited file.
- *Leverage*: words I typed vs. words my agents wrote, drawn to scale.
- *Measure twice*: how often I told an agent to plan and not code yet, and what followed.
- *Punctuation*: typed dashes vs. em-dashes, emphasis habits, rare all-caps, "whoops".
- *Comeback*: resumes after rate limits, disconnects and expired sessions.
- *Autonomy dial*, *emoji and caps*, *quiz slide*, *week in a haiku*.

Cross-agent lenses (new in v2):
- *Division of labor*: which kinds of work I send to which agent (for example, building in Claude Code, reviewing in Codex, quick questions in ChatGPT).
- *Two agents, one repo*: projects I worked on with more than one agent, how close together, and who did what.
- *Second opinion*: times I took one agent's output to another agent, to review, check or "ask the other one".
- *Who you're nicer to*: please/thanks rate and average prompt length per agent. (This is my tone with each agent, not how good each agent is.)
- *Voice drift*: how my first words, sentence length or formality change depending on which agent I'm talking to.
- *Agent hours*: when in the day and week I reach for each agent.
- *Loyalty streak*: my longest stretch using only one agent, and the moment I switched.
- *Cross-vendor model roster*: every model I touched this week across vendors, drawn as a festival lineup poster.
- *Crossover hit*: the same prompt, or nearly the same one, sent to two different agents.

**Honesty rules (important):**
- You don't have data on other users, so **never invent a population percentile** like "top 12% of users". To get that year-in-review feel honestly, do one of the following instead:
  - compare me to **my own past weeks** from `runs.jsonl`
  - compare me to a **named, real baseline** (for example, word frequencies in general English)
  - make it a **clearly playful framing** that isn't a statistic
- **Tokens aren't exactly comparable across vendors.** The tokenizers differ, and some counts are estimates. When a slide compares token volumes between agents, say so in small print. Prefer comparing prompts, sessions, time or words where you can.
- **Never rank the agents on quality.** The deck is about *my* habits, not a benchmark.

Every number on a slide must come from the extracted data. Every insight should be something I'd find true once I think about it. Surprising is good, but it can't be made up.

## Phase 4 — Design and build

- **Format:** one self-contained HTML file. Use full-viewport slides with vertical **scroll-snap**, plus keyboard (arrows/space), tap and swipe navigation, and a story-style segmented progress bar at the top. It has to look great both on a phone and on desktop.
- **Motion:** slick and modern, with a distinct entrance for each slide that triggers via IntersectionObserver. Use count-up numbers, bars that grow into a ranking, staggered text reveals, morphing blob or gradient backgrounds, and a confetti or particle burst on the archetype reveal. CSS and vanilla JS are preferred. GSAP from cdnjs is fine. Respect `prefers-reduced-motion`.
- **Visual identity that rotates weekly:** use the seed to pick this week's palette and motif (duotone gradients, bold type, grain texture, geometric shapes, and so on). The deck should look like it belongs to the same series but not be identical from week to week. Give each slide a bold background color, and don't use the same one twice in a row.
- **Agent colors:** give each agent one fixed color from this week's palette, and use it consistently on every slide (stacked bars, legends, the rotation slide), so I can recognize an agent without reading a label. Don't copy vendor logos or brand marks. Use each agent's plain name.
- **Charts:** hand-built SVG, readable at a glance, with only one idea per slide. Large type goes on the one number that matters. Keep supporting text to a single line.
- **Copy:** punchy, second person, warm, lightly cheeky. Use year-in-review-style headlines ("You had a type.", "This one was on repeat.").
- **Privacy:** these are my own prompts, but still redact anything that looks like a secret, password, token, pairing code, email, customer name or long file path before quoting it. Keep quotes short.

## Phase 5 — Ship it

1. Save the HTML to `~/agent-outputs/agent-retro/retro-YYYY-MM-DD.html` and publish it as a **private page** if your agent can (otherwise open the local file). Title it "Agent Retro, <week range>". Keep the title a plain name, with no dash and no subtitle.
2. Append this run to `runs.jsonl`, including per-agent numbers. Update `lenses.md` and save `extract.py`.
3. In chat, give me the following:
   - the link and the seed
   - which agents and sources were included, and which were missing
   - any token cross-check mismatches
   - which slides were new this week and which were returning
   - one sentence on the single most surprising thing you found

---

## Appendix A — Optional ChatGPT self-report (for the human, not for the agent)

Paste this into a new ChatGPT chat, then save its reply as `~/Downloads/chatgpt-self-report.json`. Retro uses it only for flavor, never for numbers.

```text
I'm building a personal "Retro"-style recap of how I use AI assistants, and I'd like your help with one part of it. Please reply with a single JSON code block and nothing else, using exactly this shape:

{
  "source": "chatgpt-self-report",
  "generated_on": "<today's date, YYYY-MM-DD>",
  "can_reference_chat_history": <true or false: whether you can currently see my past conversations>,
  "saved_memories": ["<each thing you have saved in memory about me, one short string each, verbatim or near-verbatim>"],
  "custom_instructions_summary": "<one or two sentences summarizing any custom instructions or personality settings I've set, or null>",
  "recent_topics": [
    {"topic": "<short label>", "approx_when": "<e.g. 'this week', 'last month', or 'unknown'>", "confidence": "<high|medium|low>"}
  ],
  "how_i_talk_to_you": ["<up to 5 observations about my tone, phrasing, or habits when I write to you, each grounded in something you can actually see>"],
  "what_i_mostly_use_you_for": ["<up to 5 short labels>"],
  "one_surprising_observation": "<one thing about how I use you that I might not have noticed, or null if you can't ground it>"
}

Rules:
- Use only what you can actually see: your saved memories, my custom instructions, and any chat history you can currently reference. Do not guess or fill gaps with plausible-sounding details.
- If you can't see something, use an empty list or null rather than inventing an entry.
- Don't include any secrets, passwords, API keys, or other people's personal details, even if they appear in memory.
- Don't estimate counts, token usage, or dates you don't actually know.
```

## Appendix B — Extraction script (`extract.py`)

```python
"""Agent Retro extractor (standalone edition). Version: standalone-2026-09-30

Usage: python3 extract.py [out.json]
Reads local Claude Code (~/.claude/projects) and Codex (~/.codex) logs, plus claude.ai / ChatGPT
export zips found in ~/Downloads, and writes normalized rows tagged by agent. Everything stays local.
Projects are named by git repo (worktrees fold into their main repo); `workspace` is the checkout folder.
"""
import json, glob, os, re, sys, time, zipfile, subprocess, collections
from datetime import datetime

HOME = os.path.expanduser('~')
NOW = time.time()
CUT = NOW - 7 * 86400
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
    for line in open(base + '/history.jsonl', errors='ignore'):
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
        if agent in sources:
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
    return json.load(open(flavor)) if os.path.exists(flavor) and os.path.getmtime(flavor) >= CUT else None


claude_code()
codex_cum = codex()
self_report = exports()

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
```
