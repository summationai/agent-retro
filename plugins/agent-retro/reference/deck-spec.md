# Agent Retro: deck spec

A Retro is **12 slides**: 8 stats slides (the fun part) and 4 coaching slides (small teachable moments). Each coaching slide sits right after the stat it grows out of, wherever that's possible. The renderer (`scripts/render.py`) owns the look. Your job is to choose the story and write `slides.json`.

## The 12 slots

| # | Kind | Component | What goes here |
|---|---|---|---|
| 1 | stat | `cold` | One striking number or phrase that stands for the week, never a generic title. |
| 2 | stat | `bignum` | Total tokens, with bars split by agent and by type (cache reads vs. everything else). Mark estimated figures. Add a week-over-week line once there's history. |
| 3 | stat | `lineup` | Your agents as a band lineup: prompts, sessions, tokens and surfaces, with a one-line role for each. If only one agent was used, show its surfaces (CLI, desktop, IDE) as the acts instead. |
| 4 | **coach** | `coach` | Tied to slot 3, or to any stat so far. |
| 5 | stat | `ranking` | Top projects, stacked by agent. |
| 6 | stat | any | A rotating stat lens (A). |
| 7 | **coach** | `coach` | Tied to slot 6. |
| 8 | stat | any | A rotating stat lens (B). |
| 9 | **coach** | `coach` | Tied to slot 8. |
| 10 | stat | `archetype` | A named persona for the week, backed by 3 evidence tiles. |
| 11 | **coach** | `coach` | Tied to the archetype, or standalone. |
| 12 | stat | `outro` | A share card: 6 facts and 3 "try this week" lines, taken from the coaching slides. |

**Picking lenses A and B:** score the stat lenses below for *surprise × strength of evidence × novelty*. Novelty is lower if a lens was used in either of the last two runs (see `runs.jsonl`). Pick A and B **together with** the coaching moments, so each coaching slide has a stat to follow. If the best coaching moment has no matching stat, it can run standalone in slot 4 or 11.

**Coaching balance:** at least 2 of the 4 coaching slides are **wins** (`"kind": "win"`), and the rest are **level-ups** (`"kind": "tweak"`). Keep coaching slides light: one headline, one stat, one line of "why", and one copyable "try".

## Stat lenses (menu)

- *On repeat*: a prompt sent 2+ times (`stats.repeats`).
- *First words*: your opener leaderboard (`first_words`).
- *Voice drift*: questions, length and please rates by agent (`voice`).
- *Manners*: please count vs. thank-you count.
- *Night shift / clock*: the busiest output hour, especially if you sent 0 prompts in it. Show the grid as a `heatmap`.
- *Weekend band*: weekend prompts by agent.
- *Relay race*: handoffs between agents, and your longest single-agent streak.
- *The crew*: subagent token share, top tools and MCP servers.
- *Model mix*: models' share of tokens vs. share of output.
- *Names you gave things*: the most colorful branch names, the most-edited file.
- *Marathon*: the longest session.
- *Leverage*: words typed vs. an estimate of words back.
- *Plot twist*: anything new or surprising that you invent from this week's data.

## Coaching moments (menu)

Work from `coaching.json` (the summary plus per-prompt rows) and the prompts themselves (`prompts.txt`). **Read the actual prompt and the reply that followed before explaining why.**

- **Win: your secret sauce.** The feature with the biggest positive lift, for example "with a boundary: 20/20 vs. 79%". Use a `compare` stat.
- **Win: say what done looks like.** Use `defines_done`.
- **Win: best-received prompt.** The prompt that drew praise, and why it worked. Use a `quote` stat.
- **Win: long briefs land**, or plan-first pays off.
- **Level-up: make it a command.** Repeated prompts become a slash command. Use a `number` stat. This pairs with *On repeat*.
- **Level-up: ask for evidence, not reassurance.** Short yes/no check-ins vs. everything else. This pairs with *Voice drift*.
- **Level-up: say it once.** Re-stated rules ("again, …") go into a AGENTS.md (or your agent's equivalent) snippet.
- **Level-up: paste with a label.** A paste followed by confusion gets an instruction line placed above it.
- **Level-up: reset button.** A tangled correction chain would have gone quicker as a fresh session with a crisp restatement.

**Confidence chip:**
- "strong signal": 20 or more prompts, a gap of 15 points or more, and the pattern holds when you read the examples.
- "early signal": 8–19 prompts.
- "small sample · n" or "one moment": fewer than 8 prompts, or a single story.

**The "why" library** (plain language):
1. Say what done looks like.
2. Share the why.
3. Set boundaries.
4. Show an example.
5. Plan, then build.
6. Small steps with checkpoints.
7. Point at exact context.
8. Ask for evidence, not reassurance.
9. Write standing preferences down once (AGENTS.md (or your agent's equivalent)).
10. Turn repeats into commands.
11. Reset when tangled.
12. Delegate in parallel.
13. Lead with the instruction when pasting.
14. Invite clarifying questions.

## Rules

- **Tone:**
  - Warm, punchy, second person, lightly cheeky, year-in-review-style headlines.
  - **Never** "wrong", "bad", "mistake", "poor", "fail", "should have", or synonyms.
  - Level-ups describe a situation and a small tweak, never a failing.
  - Say "even better", "try", "level up".
- **Honesty:**
  - Every number must come from `stats.json`, `coaching.json`, or a count you make from the data files. Never invent one.
  - No population percentiles ("top 10% of users"). Compare to your own past weeks, a named baseline, or obviously playful framing.
  - Token counts differ across vendors, so say so in small print wherever you compare them.
  - Coaching signals are proxies (your next message's reaction). The outro footer says so.
- **Privacy:**
  - Quotes are 12 words or fewer.
  - Never quote a secret, password, token, email address, customer name, or anyone else's name.
  - `prompts.txt`, `stats.json` and the `coaching.json` rows are pre-redacted (secrets, keys, emails, phone and card numbers, home-folder names), but still check anything you quote.
  - Never quote a redaction marker: `[redacted…]`, `[email]` or `[phone]`.

## Components (`slides.json`)

```json
{"title": "Agent Retro, <Mon D>–<D>", "brand": "Agent Retro", "seed": 1234, "slides": [ ... ]}
```

Optional on every slide:
- `"bg"`: one of `ink`, `blue`, `yellow`, `paper`, `pink`, `orange`, `green`. The renderer otherwise picks it, and never uses the same one twice in a row.
- `"eyebrow"`: a small label above the headline.

Agent keys are `claude-code`, `codex`, `chatgpt` and `claude-ai`, which render in their fixed colors: pink, blue, green and orange.

- **`cold`**: `big`, `headline`, `lede`, `small?`
- **`bignum`**: `value` (an integer), `lede`, `bars: [{label, segments: [{agent | color, label, value}]}]`, `small?`
- **`lineup`**: `headline`, `acts: [{agent, role, prompts, sessions, tokens_label, line, surfaces}]`
- **`ranking`**: `headline`, `rows: [{name, value_label, segments: [{agent, value}], meta?}]`
- **`quote`**: `headline`, `quote`, `tally?: [{value, label, suffix?}]`, `small?`
- **`tally`**: `headline`, `lede?`, `tally: [{value, label, suffix?}]`, `small?`
- **`compare`**: `headline`, `lede?`, `rows: [{label, pct, n_label}]`. The first row is highlighted.
- **`timeline`**: `headline`, `items: [{time, agent?, text}]`, `small?`
- **`heatmap`**: `headline`, `lede?`, `days: [{key: "YYYY-MM-DD", label: "Mon\n28", weekend?}]`, `hours?: [8..22]`, `cells: {"YYYY-MM-DD|H": {agent: count}}`, `alt`
- **`coach`**: `kind: "win" | "tweak"`, `confidence`, `cite?` (the stat slide's name), `headline`, `stat: {type: "compare", rows} | {type: "number", value, label} | {type: "quote", quote, context?}`, `why`, `try` (copyable text; newlines are fine)
- **`archetype`**: `name`, `lede`, `evidence: [{value, label}]` (3 tiles)
- **`outro`**: `title`, `eyebrow`, `facts: [{label, value, wide?}]` (6 facts), `tries: [3 strings]`, `footer`
