---
name: retro
description: Your weekly Agent Retro — a 12-slide look back at how you used your coding agents (Claude Code, Codex, and ChatGPT or claude.ai exports), with four bite-sized coaching tips. Use only when the user asks for their retro.
argument-hint: "[only=<agents>] [days=N] | chatgpt | help"
---

# Agent Retro

Build my Agent Retro for the last week: 12 animated slides, with 8 fun stats and 4 small coaching moments woven in. Do the work yourself, and don't stop to ask me questions unless you're blocked.

**Paths:** `PLUGIN_ROOT` is the folder two levels above this `SKILL.md`, the one that contains `scripts/` and `reference/`. Resolve it to an absolute path before running anything, and use it in every command below.

I may have passed options along with the request. Handle them like this:
- **`help`:** explain these options in 5 lines and stop.
- **`chatgpt`:** show me the three ChatGPT options from `PLUGIN_ROOT/reference/chatgpt.md`, including its pastable prompts exactly as written, and stop.
- **`only=<agents>`:** set `RETRO_SOURCES` to the comma-separated agent keys (`claude-code`, `codex`, `chatgpt`, `claude-ai`), so every other source is skipped.
- **`days=N`:** set `RETRO_DAYS=N`. The default is 7.

The scripts run locally and redact the prompt text before you read it. Don't upload or send anything else; the only thing that may be published is the finished deck, as a private page.

## 1. Set up
- `RETRO_HOME` is `$AGENT_RETRO_HOME` if that's set, otherwise `~/agent-retro`.
- Create `RETRO_HOME/builds/<today>/`. Call it `BUILD`.
- Pick a random integer seed and print it.

## 2. Gather and measure (run these, in order)
```bash
python3 "$PLUGIN_ROOT/scripts/extract.py" "$BUILD/data.json"
python3 "$PLUGIN_ROOT/scripts/stats.py" "$BUILD/data.json" "$BUILD/stats.json"
python3 "$PLUGIN_ROOT/scripts/coaching_signals.py" "$BUILD/data.json" "$BUILD/coaching.json"
```
Set the `RETRO_SOURCES` and `RETRO_DAYS` environment variables on the first command when the options ask for them.
- `extract.py` reads whichever of these it finds: `~/.claude/projects` (Claude Code), `~/.codex` (Codex), and any claude.ai or ChatGPT export zips in `~/Downloads`.
- If your sandbox blocks reading those folders or `~/Downloads`, or writing to `RETRO_HOME`, ask me to approve access rather than skipping a source or the save silently.
- `stats.py` also writes `BUILD/prompts.txt`, a redacted one-line-per-prompt digest.
- If a script fails because a log format has changed, make the smallest fix that gets it running in a copy under `BUILD/`, and tell me what you changed. Never edit the plugin's own files.

## 3. Read
- **`stats.json`:** the deterministic numbers.
- **`coaching.json`'s `summary`:** feature lifts, reaction counts, repeats, reminders, and check-ins. Look up specific moments in its `rows` by id.
- **`prompts.txt`:** read all of it. The best stories come from reading what I actually wrote.
- **`RETRO_HOME/runs.jsonl`:** past runs, if there are any. Use them for week-over-week deltas, and to avoid repeating a lens used in both of the last two runs.
- **Sources:** if ChatGPT wasn't included, the outro footer gets one short line: "Add ChatGPT: run the retro with `chatgpt`".

## 4. Write the deck
Follow `PLUGIN_ROOT/reference/deck-spec.md` exactly. It defines the 12 slots, the lens and coaching menus, the tone, honesty and privacy rules, and the `slides.json` component formats.
- Write `BUILD/slides.json`.
- Before rendering, re-read every headline, quote and try line against the spec's tone and privacy rules. Check that every number traces back to `stats.json`, `coaching.json`, or a count you made from the data.

## 5. Render, save and share
```bash
python3 "$PLUGIN_ROOT/scripts/render.py" "$BUILD/slides.json" "$RETRO_HOME/retro-<YYYY-MM-DD>.html"
```
- **Publishing:** if this session has a tool for publishing private web pages, publish the HTML as a **private** page titled like `Agent Retro, Sep 23–30`. Otherwise, open the local file with `open "<path>"` on macOS or `xdg-open` on Linux.
- **Memory:** append one line to `RETRO_HOME/runs.jsonl` with the date, window, seed, sources, the 12 slide headlines and lens ids, the archetype, the 3 tries, and the key numbers (tokens, prompts per agent, smooth rate).
- **Clean up:** run `python3 "$PLUGIN_ROOT/scripts/cleanup.py" "$BUILD"`. It removes the two files that contain raw prompt text and keeps `stats.json`, `slides.json` and `prompts.txt`.
- **Report back in 5 lines or fewer:** the link or path, the seed, which sources were included, the archetype, and the 3 things to try this week.
