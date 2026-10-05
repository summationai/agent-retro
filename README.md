# agent-retro

![An Agent Retro cold-open slide](docs/screenshot.webp)

**A weekly look back at how you use AI coding agents.** It reads your local coding-agent logs (Claude Code and Codex today, plus ChatGPT and claude.ai exports if you add them) and builds an animated, 12-slide deck. There are **8 fun stats** about your week, with **4 bite-sized coaching tips** woven in, each one right after the stat it comes from.

The scripts that read your history and compute the stats run on your machine, and they redact secrets and personal details from your prompts before your agent reads them to write the deck. Your agent then sends that redacted text to its model provider, as it would for any other task. If your agent has a tool for publishing private pages, it publishes the deck there; otherwise you get a local HTML file.

## Quick start: the Agent Retro plugin

One plugin, two hosts.

**Claude Code**

```
/plugin marketplace add summationai/agent-retro
/plugin install agent-retro@agent-retro
/retro
```

**Codex / ChatGPT** (the Codex CLI, or Codex in the ChatGPT desktop app)

```
codex plugin marketplace add summationai/agent-retro
codex plugin add agent-retro@agent-retro
```

Then ask Codex to "build my Agent Retro" (or mention `$agent-retro:retro`).

Add `help` for the options: `only=<agents>`, `days=N`, and `chatgpt`, which shows how to add ChatGPT history. See [PLUGIN.md](PLUGIN.md) for details.

## What's in here

| Path | What it is |
|---|---|
| `.claude-plugin/`, `.agents/plugins/` | Marketplace listings for Claude Code and Codex. Both point at `plugins/agent-retro/`. |
| `plugins/agent-retro/` | **The plugin**, with a manifest for each host (`.claude-plugin/`, `.codex-plugin/`). The shared `retro` skill, the deck spec, the ChatGPT guide, and the bundled scripts: extraction, stats, coaching signals, renderer and cleanup. |
| `toolkit/prompts/` | The prompt-driven versions it grew out of: the v1 (Claude Code only) and v2 (Claude Code, Codex and chat exports) prompts, and the ChatGPT export guides. |
| `toolkit/share/` | The v2 edition as a single paste-in file, with its extractor embedded. |
| `toolkit/modular/` | The modular architecture: opt-in content **packs** (stats, coaching) that emit slide cards, plus a **composer** that interleaves them, with a config that sets which packs run and how many slides each gets. |

## How the coaching works

After each prompt, the tool reads your *next* message. "OK, now…", "let's build that" or "great" counts as the prompt landing. "That's not…", "why didn't you…" or "stop" counts as a course-correction. It then compares prompts that used a practice with prompts that didn't: setting a boundary, saying what done looks like, sharing the why, and so on. Each tip is backed by those numbers and explained with well-known prompting practices. These are signals, not grades, and the tips are always framed as "even better", never "wrong".

## Privacy

- **Local-only reading:** `~/.claude/projects`, `~/.codex`, and export zips in `~/Downloads`.
- **Redaction** before any prompt text reaches the deck writer: API keys and tokens (cloud, GitHub, Slack, Stripe and similar), JWTs, auth headers, private keys, credentials in URLs and `key=value` pairs, long secret-looking strings, password-like words, emails, phone numbers, card numbers (checksum-verified), US SSNs, and your home-folder name in paths. See `plugins/agent-retro/scripts/redact.py`. It's pattern-based, so it catches common shapes, not every possible secret.
- **Personal data never belongs in this repo.** That includes decks, run histories and exports, and `.gitignore` keeps them out.

Requires macOS or Linux, with `python3` available.

## Tests

Standard library only, Python 3.9+:

```
python3 -m unittest discover -s tests
```

The suite runs every pipeline on synthetic data, so it never touches your own logs. It checks that no planted secret reaches any output, covers extraction and rendering, and verifies that copied code (the script embedded in the paste-in prompt, and the two plugin manifests) hasn't drifted.

## License

[MIT](LICENSE) © Summation
