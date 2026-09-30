# Adding ChatGPT (and Codex) to your Retro

**Codex needs nothing.** If you use Codex on this machine, the Retro reads `~/.codex` automatically. To leave it out, run `/retro only=claude-code`.

**ChatGPT is optional.** ChatGPT keeps your history on OpenAI's servers, not on your Mac, so the Retro can only include it once you've exported it. There are three ways, from most to least complete.

## 1. The official export (most complete)

1. In ChatGPT (web or desktop), open **Settings → Data controls → Export data**, then choose **Export**.
2. An email arrives with a download link. It usually takes a few minutes, and the link expires after about 24 hours.
3. Save the zip to `~/Downloads`. Don't rename or unzip it. The Retro recognizes it by what's inside.

The export includes your whole history, and the Retro uses only the last 7 days. ChatGPT has no token counts, so the Retro estimates them and labels them as estimates.

## 2. Have Codex build the file for you (quickest)

If you have **Codex in the ChatGPT desktop app**, it can read your ChatGPT history with the app's own tools. Paste this into a new Codex chat:

```text
Create a ChatGPT history file for my Agent Retro now. This is a file-generation task: do it, don't explain how.
Use the last 7 days, ending now, in my local time zone. Use this app's ChatGPT chat-history tools to collect every
ChatGPT conversation with messages in that window, and include only messages you can actually see. Never invent any.
Write ~/Downloads/chatgpt-retro-export.zip containing one file, conversations.json, in the ChatGPT export format:
a list of conversations, each {"title", "create_time", "mapping": {node_id: {"message": {"author": {"role"}, "create_time",
"content": {"content_type": "text", "parts": [text]}, "metadata": {"model_slug"}}, "parent", "children"}}}.
Also add coverage.json to the zip, stating the window and that the data came from app history, not an official export.
Leave out secrets, credentials and API keys. When you're done, report the file size and the conversation and message counts.
```

The Retro marks this source as "app history, may be incomplete".

## 3. Keep it fresh with a weekly ChatGPT task (for flavor, not numbers)

ChatGPT's scheduled **Tasks** run on OpenAI's servers, so they can't save files to your Mac. What a task *can* do is send you a weekly self-portrait to paste into `~/Downloads/chatgpt-self-report.json`, plus a reminder to request a fresh export. In ChatGPT, send:

```text
Every Monday at 8am, run this task: remind me to request a fresh data export (Settings → Data controls → Export
data) for my Agent Retro, then reply with a single JSON code block and nothing else, shaped like this:
{"source": "chatgpt-self-report", "generated_on": "<YYYY-MM-DD>", "recent_topics": [{"topic": "", "confidence": "high|medium|low"}],
 "how_i_talk_to_you": ["<up to 5 grounded observations>"], "what_i_mostly_use_you_for": ["<up to 5 labels>"],
 "one_surprising_observation": "<or null>"}
Use only what you can actually see in my memory and recent chats. Never guess, never include secrets, and never estimate counts.
```

The Retro uses a self-report only for flavor lines ("ChatGPT thinks you…"). A self-report never supplies a number.
