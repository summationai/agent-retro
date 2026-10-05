# Agent Retro: deck spec

The default Retro is **12 slides**: 8 stats slides (the fun part) and 4 coaching slides (small teachable moments). Each coaching slide sits right after the stat it grows out of, wherever that's possible. The renderer (`scripts/render.py`) owns the look. Your job is to choose the story and write `slides.json`.

## Profiles and validation

`slides.json` uses `schema_version: 1` and `profile: "default-12"` (the default).
The renderer validates component fields, numeric bounds, quote privacy/length, and the default slot plan.
Finalization also checks evidence references and the total-token slide against the measured data.

Read `BUILD/run.json` first. If `presentation_profile` is `limited`, preparation has written a
short starter `slides.json`. Refine it using only available measurements and keep `profile: "limited"`.
This profile omits coaching and archetypes and allows fewer facts and zero tries. It is used when
there are fewer than eight human prompts or eight judged reactions. Do not force the 12-slot plan.

The modular edition can use `profile: "custom"` for a different layout when sufficient data exists.
Component and quote validation still applies. Numerical prose still needs the writer's number pass.

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

Work from `coaching.json` (the summary plus per-prompt rows) and the prompts themselves (`prompts.txt`). **Read the actual prompt and the next user message before explaining why.** The extractor does not supply assistant replies to the deck writer. Stable prompt IDs are shared by the digest and coaching rows; `next_id` identifies the next user message.

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
- Use `coaching.summary.by_feature.<feature>.confidence` for feature comparisons.
- "strong signal": both groups have at least 20 judged prompts, a gap of 15 points or more, and no reversal in adequately sampled agent groups. Still read the examples before explaining the pattern.
- "early signal": both groups have at least 8 judged prompts and the comparison does not qualify as strong.
- "small sample · n": the smaller group has fewer than 8 judged prompts.
- "one moment": a single grounded story. "insufficient comparison" means choose another comparison or use a single story; do not manufacture a percentage lift.
- These labels describe correlations, not causal effects; repeated prompts within one session are not independent experiments.

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
  - Read `stats.diagnostics` and `stats.provenance`. A source marked `partial` has incomplete measurements; label its totals as partial. `usage_unavailable` means unknown usage, never zero activity.
  - Preserve source coverage labels, including "app history, may be incomplete". Self-report content is flavor only and never supports a number.
  - Coaching signals are proxies (your next message's reaction). The outro footer says so.
- **Privacy:**
  - Quotes are 12 words or fewer.
  - Never quote a secret, password, token, email address, customer name, or anyone else's name.
  - `prompts.txt`, `stats.json` and the `coaching.json` rows are pre-redacted (secrets, keys, emails, phone and card numbers, home-folder names), but still check anything you quote.
  - Never quote a redaction marker: `[redacted…]`, `[email]` or `[phone]`.

## Components (`slides.json`)

```json
{"schema_version": 1, "profile": "default-12", "title": "Agent Retro, <Mon D>–<D>", "brand": "Agent Retro", "seed": 1234, "slides": [ ... ]}
```

Optional on every slide:
- `"bg"`: one of `ink`, `blue`, `yellow`, `paper`, `pink`, `orange`, `green`. The renderer otherwise picks it, and never uses the same one twice in a row.
- `"eyebrow"`: a small label above the headline.
- `"lens"`: the lens ID to record in history.
- `"evidence_refs"`: JSON pointers into the measured outputs, such as `"/stats/tokens/total"` or
  `"/coaching/summary/by_feature/sets_constraints"`. Required on default-profile coaching slides.
  Strong/early confidence must reference a feature comparison with at least that computed confidence.
  For one moment, reference its row (for example `"/coaching/rows/0"`); use stable IDs to find the row first.

Explicit segment colors must be `#rgb`, `#rrggbb`, or a supported palette variable such as `var(--fg)`. Percentages are numeric values in 0–100; counts are finite and nonnegative.

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
