> **Historical reference.** Do not run this older raw-data workflow. Use the plugin or
> `toolkit/share/retro-paste-in.md`, which prepares redacted data before the agent reads it.

# Agent Retro — weekly prompt

Make me this week's **Agent Retro**: a playful, multi-slide infographic of how I used Claude Code over the **last 7 days**, published as a private page. It should surprise me. If I ran it on the same data twice, I'd want different insights at least some of the time. When the data is new, I want new slides alongside a few returning favorites, not just the same deck with new numbers.

Work through the phases below in order, and don't stop to ask me questions unless you're blocked.

---

## Phase 1 — Gather the data (be precise, it's easy to get wrong)

**Claude Code transcripts** are in `~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl`. Subagent transcripts are in `.../<sessionId>/subagents/*.jsonl`. Include only files modified in the last 7 days, then filter each record by its `timestamp`. Write a Python script in your scratchpad that reads them and writes a compact `retro_data.json`. These are the known pitfalls:

- **Real prompts from me** are `type == "user"` records where `isSidechain` is false, `origin.kind == "human"` (or `promptSource` is `typed`/`queued`), and the content is text rather than `tool_result`. Remove any `<system-reminder>…</system-reminder>`, `<command-…>` and other injected tags before analyzing the text. Put prompts sent by automation, such as skills or workspace-manager dispatches with `promptSource: "sdk"` and templated text, in their own "automations" bucket. Don't count them as my voice.
- **Token usage** comes from `type == "assistant"` records at `message.usage`: `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, and `output_tokens_details.thinking_tokens`. **Deduplicate by `message.id`**, because one API response is written across several records and counting every record roughly doubles the totals. Also record `message.model`, `effort`, `gitBranch`, `cwd` and `entrypoint` (cli vs. claude-desktop).
- **Cost and lines changed**: take `type == "cost-state"` records (`totalCostUSD`, `totalLinesAdded`, `totalLinesRemoved`, `modelUsage`) and keep the last one per session.
- **Tools the agent used for me**: collect the `tool_use` blocks inside assistant content (name, and file paths for Edit/Write/Read). Subagent usage shows up as sidechain records.
- **Projects**: group by `cwd`. Collapse git worktrees and scratch/"no folder" workspaces into sensible project names. Use a repo's basename, and combine all scratch sessions as "No-folder sessions". Session titles are in `custom-title` / `agent-name` records.
- `~/.claude/history.jsonl` is a clean log of typed prompts with `project` and `timestamp`. Use it to cross-check the prompt extraction.
- Record timestamps in **my local timezone**.

**claude.ai chats (optional):** check `~/Downloads` for a recent claude.ai data export (a `conversations.json`, possibly in a zip). If you find one, include my human turns from the last 7 days under a "Claude.ai" project. Exports have no token counts, so estimate them at about 4 characters per token and label them as estimates everywhere. If there's no export, add one small line on the final slide explaining how to include one (Settings → Privacy → Export data).

Once the script runs, **actually read all of my real prompts**. There are usually only a few hundred. The best insights come from reading them, not from counting them.

## Phase 2 — Load memory from past Retros

Keep a persistent folder at `~/agent-outputs/agent-retro/`:

- `runs.jsonl`: one line per past run, with the date, the random seed, the slide IDs used, the headline stat for each slide, and the week's key numbers (tokens, prompts, sessions, top project, archetype).
- `lenses.md`: the growing catalog of insight "lenses" (see Phase 3). If it doesn't exist, create it from the starter list below.
- `retro-YYYY-MM-DD.html`: a local copy of each deck.

Use this history in three ways. First, compute **week-over-week deltas** for the key numbers. Second, **avoid repeating** a lens that has been used in both of the last two runs unless this week's data makes it dramatically more interesting. Third, **compare me to my own past weeks** ("your most-polite week yet", "top 20% of your weeks for late-night coding").

## Phase 3 — Choose this week's slides

Start by picking a random seed and printing it, so a run can be reproduced. Use it to break ties and drive creative choices.

**Fixed anchor slides**, which appear every week and act as the old favorites:
1. **Cold open.** A single striking number or phrase that stands for the week, not just a generic title.
2. **The big number.** Total tokens, split into input, output, cache read, cache write and thinking. Include a relatable comparison (novels' worth, printed pages, and so on) and the change from last week.
3. **Top projects.** Projects ranked by tokens, drawn as a "Top Artists" countdown, with sessions and prompts for each.
4. **Your agent archetype.** Give the week a named persona, like a personality-quiz result ("The 1 a.m. Refactorer", "The Polite Interrogator", "The Delegator-in-Chief"). Invent a new name every week, backed by 2–3 pieces of real evidence.
5. **Outro / share card.** A compact summary of the week on one card.

**Rotating slides** (6–9 of them): score every lens in `lenses.md` against this week's data for *surprise × strength of evidence × novelty*. Novelty is lower if the lens appeared recently. Take the top scorers, and use the seed to break near-ties. **Also invent at least one brand-new lens** that isn't in the catalog, based on something unusual in this week's data, and append it to `lenses.md` so it can come back in later weeks.

**Starter lens catalog** (seed `lenses.md` with these):
- *First words*: a leaderboard of the words I start prompts with ("Please", "Can", "Let's", "I", "Go ahead"…).
- *Politeness index*: how often I say please/thanks/sorry, and whether it drifts by project or time of day.
- *Catchphrases*: recurring 2–4 word phrases that are distinctly mine.
- *Signature vocabulary*: words I use far more often than general English does. (Use a common-word baseline and say which one.)
- *On repeat*: exact or near-duplicate prompts I sent more than once, and the task I keep coming back to.
- *Question vs. command*: my ratio of questions to instructions, and which projects lean each way.
- *The epic*: my longest prompt, shown as an excerpt with its word count. Plus my shortest prompt that still worked.
- *Plot twist*: a project or topic that appeared suddenly, or one that went quiet.
- *Genres*: my prompts classified by task type (debug, build, review, research, write, explain, plan), shown as a genre mix.
- *Clock*: an hour × day heatmap, my latest-night prompt, my longest streak, and a morning-vs-evening character.
- *Marathon*: the longest session by wall-clock time, turns or tokens, and what it was about.
- *Course corrections*: how often I push back ("no", "actually", "that's not", "undo", interruptions), and where it happens most.
- *The crew*: subagents launched, skills and slash commands used, and my top MCP tools.
- *Hands on the keyboard*: the agent's top tools for me, the files it touched most, languages by file extension, and lines added vs. removed.
- *Cache wizard*: cache-read share of input tokens, framed as tokens (and $) saved.
- *Model mix and effort*: which models and effort levels I used, and when.
- *Branch names*: the most colorful git branch names from the week.
- *Autonomy dial*: how much I delegate ("go ahead", "as long as you need") compared with how much I micromanage.
- *Emoji, exclamation and ALL-CAPS* habits.
- *Quiz slide*: an interactive "Guess which project ate the most tokens?" that reveals the answer on tap.
- *Week in a haiku*: a short poem built from my actual phrases.

**Honesty rule (important):** you don't have data on other users, so **never invent a population percentile** like "top 12% of users". To get that year-in-review feel honestly, do one of the following instead:
- compare me to **my own past weeks** from `runs.jsonl`
- compare me to a **named, real baseline** (for example, word frequencies in general English)
- make it a **clearly playful framing** that isn't a statistic ("friendlier than a golden retriever at a dog park").

Every number on a slide must come from the extracted data. Every insight should be something I'd find true once I think about it. Surprising is good, but it can't be made up.

## Phase 4 — Design and build

- **Format:** one self-contained HTML file. Use full-viewport slides with vertical **scroll-snap**, plus keyboard (arrows/space), tap and swipe navigation, and a story-style segmented progress bar at the top. It has to look great both on a phone and on desktop.
- **Motion:** slick and modern, with a distinct entrance for each slide that triggers via IntersectionObserver. Use count-up numbers, bars that grow into a ranking, staggered text reveals, morphing blob or gradient backgrounds, and a confetti or particle burst on the archetype reveal. CSS and vanilla JS are preferred. GSAP from cdnjs is fine. Respect `prefers-reduced-motion`.
- **Visual identity that rotates weekly:** use the seed to pick this week's palette and motif (duotone gradients, bold type, grain texture, geometric shapes, and so on). The deck should look like it belongs to the same series but not be identical from week to week. Give each slide a bold background color, and don't use the same one twice in a row.
- **Charts:** hand-built SVG, readable at a glance, with only one idea per slide. Large type goes on the one number that matters. Keep supporting text to a single line.
- **Copy:** punchy, second person, warm, lightly cheeky. Use year-in-review-style headlines ("You had a type.", "This one was on repeat.").
- **Privacy:** these are my own prompts, but still redact anything that looks like a secret, token, email, customer name or long file path before quoting it. Keep quotes short.

## Phase 5 — Ship it

1. Save the HTML to `~/agent-outputs/agent-retro/retro-YYYY-MM-DD.html` and publish it as a **private page** if your agent can (otherwise open the local file) titled "Agent Retro — <week range>".
2. Append this run to `runs.jsonl` and update `lenses.md`.
3. In chat, give me the link, the seed, which slides were new this week versus returning, and one sentence on the single most surprising thing you found.
