# Getting ChatGPT data into Agent Retro

There are two ways to get ChatGPT data into Retro, and they aren't equally good.

## 1. The real dataset: ChatGPT's built-in export (recommended)

A chat prompt can't reliably list your past conversations. ChatGPT can only see what's in its memory and whatever chat history it happens to be able to reference. The built-in export is complete and exact, so use it for anything that becomes a number.

1. In ChatGPT (web or desktop), open **Settings → Data controls → Export data** and choose **Export**.
2. You'll get an email with a download link. It usually arrives within minutes, and the link expires after about 24 hours.
3. Download the zip to `~/Downloads`. You don't need to unzip or rename it. Retro recognizes it by its structure.

The zip contains your full history. Retro reads only the last 7 days, and the data never leaves your machine except as numbers and short quotes in your private deck. For a weekly habit, export on the morning you run Retro.

## 2. Optional flavor: a self-portrait from ChatGPT

Paste the prompt below into a new ChatGPT chat. Save its reply as `~/Downloads/chatgpt-self-report.json`. Retro uses it only as inspiration for copy and slide ideas, such as "ChatGPT thinks you're…". It never uses it for a number, because it's ChatGPT's own description of you, not a record of what happened.

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

## What Retro does with each

| File in `~/Downloads` | Used for | Can produce numbers? |
|---|---|---|
| ChatGPT export zip (`conversations.json`) | Prompts, timing, topics, models. Tokens are estimated at about 4 characters per token and labeled as estimates. | Yes |
| `chatgpt-self-report.json` | Inspiration for copy and slide ideas | No |
| claude.ai export zip | Same as the ChatGPT export, for claude.ai chats | Yes |
| *(nothing; read from disk automatically)* | Claude Code and Codex | Yes, with exact token counts |
