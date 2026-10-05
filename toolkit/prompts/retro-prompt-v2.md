> **Historical reference.** Do not run this older raw-data workflow. Use the plugin or
> `toolkit/share/retro-paste-in.md`, which prepares redacted data before the agent reads it.

# Agent Retro — weekly prompt (v2: Claude Code, Codex and chat exports)

> v2 builds on v1 (`retro-prompt-v1.md`, kept unchanged). It adds Codex and ChatGPT alongside Claude Code, so the deck covers every AI agent I used this week. Look, tone, and the rotation and honesty rules all carry over from v1.

Make me this week's **Agent Retro**: a playful, multi-slide infographic of how I used my AI agents (Claude Code, claude.ai, Codex, and ChatGPT) over the **last 7 days**, published as a private page. It should surprise me. If I ran it on the same data twice, I'd want different insights at least some of the time. When the data is new, I want new slides alongside a few returning favorites, not just the same deck with new numbers. Claude is still the headliner, and the other agents are the supporting cast. The most interesting stories are usually about how I split work between them.

Work through the phases below in order, and don't stop to ask me questions unless you're blocked. If a source is missing, skip it and say so on the final slide instead of stopping.

---

## Phase 1 — Gather the data (be precise, it's easy to get wrong)

Start from `~/agent-outputs/agent-retro/extract.py` if it exists. It already handles Claude Code correctly. Extend it with the sources below instead of rewriting it, and save it back. The script should write one normalized `retro_data.json` with three row types, each tagged with `agent` (`claude-code`, `claude-ai`, `codex` or `chatgpt`):

- **prompt**: `ts`, `agent`, `surface` (cli, desktop, vscode, web), `project`, `session`, `text`, `is_automation`
- **usage**: `ts`, `agent`, `model`, `effort`, `project`, `session`, `fresh_input`, `cache_read`, `cache_write`, `output`, `reasoning`, `estimated` (bool)
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
- Also use `~/Downloads/chatgpt-self-report.json` if it exists (see the companion ChatGPT prompt). It's ChatGPT describing me from its memory. Treat it as **flavor only**: it can inspire a slide or a line of copy, but no number may come from it.
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
