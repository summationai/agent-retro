# Agent Retro

A weekly look back at how you use AI coding agents. It's 12 animated slides: **8 fun stats** about your week (tokens, projects, habits, your archetype), with **4 bite-sized coaching tips** woven in, each right after the stat it comes from. The tips show what's working and one small thing to try.

## Install

In Claude Code:

```
/plugin marketplace add <path-or-git-url-of-this-folder>
/plugin install agent-retro@agent-retro
```

The first line takes a local folder (such as `~/Downloads/agent-retro`) or a git repository that contains this folder. From a terminal, the same two steps are `claude plugin marketplace add …` and then `claude plugin install agent-retro@agent-retro`.

## Use

| Command | What it does |
|---|---|
| `/retro` | Build this week's Retro from every source it finds: Claude Code and Codex logs on your machine, plus any ChatGPT or claude.ai export in `~/Downloads` |
| `/retro only=codex` | Use only the listed sources (comma-separated: `claude-code`, `codex`, `chatgpt`, `claude-ai`) |
| `/retro days=14` | Look back 14 days instead of 7 |
| `/retro chatgpt` | Ways to add your ChatGPT history, with prompts you can paste |
| `/retro help` | Show the options |

If another plugin also has a `/retro` command, use `/agent-retro:retro`.

It takes a few minutes. You get a private link if your agent can publish pages, or a local HTML file otherwise. Everything is saved in `~/agent-retro/`, so next week's Retro can compare against this one and rotate in new slides. Set `AGENT_RETRO_HOME` to use a different folder.

## Privacy

- **Everything is read locally:** `~/.claude/projects`, `~/.codex`, and export zips you put in Downloads.
- **Your agent sees redacted text only.** It reads a redacted digest of your prompts to write the deck, and sends that to its model provider as it would for any other task. Nothing else leaves your machine, except the finished deck if you publish it as a *private* page that only you can open until you share it.
- **Sensitive text stays out of the deck.** Quotes are short. Before the deck writer sees your prompts, the scripts redact API keys, tokens, private keys, credentials in URLs, password-like strings, emails, phone and card numbers, and your home-folder name.
- **Raw prompt text is deleted.** The working files that contain it are removed at the end of each run.

## How the coaching works

After each prompt, the Retro looks at your *next* message. "OK, now…", "let's build that" or "great" counts as landed. "That's not…", "why didn't you…" or "stop" counts as a course-correction. It compares prompts that did something (set a boundary, said what done looks like, shared the why) with those that didn't, and explains the pattern using well-known prompting practices. These are signals, not grades. Every tip is framed as "even better", never "wrong".

Requires macOS or Linux, with `python3` available.
