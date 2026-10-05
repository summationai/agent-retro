# Agent Retro: modular edition

The v1 and v2 prompts are historical references. The share file is generated from the canonical plugin pipeline. This folder is the next step: **content packs** that each produce slide **cards**, and a **composer** that turns the enabled packs' cards into one deck.

```
data ──► pack: stats ───────► cards/stats.json ─────┐
    └──► pack: coaching ────► cards/coaching.json ──┼──► composer ──► deck
         (+ coaching_signals.py)                    │    (order, pairing, design, privacy pass, publish)
         pack: <future> ────► cards/<pack>.json ────┘
```

- **`retro.config.json`** says which packs run, how many slides each pack gets, and where the coaching goes (`section`, `inline` or `both`).
- **`run-retro.md`** is the one prompt to paste. It reads the config, runs each enabled pack, then runs the composer.
- **`packs/stats.md`** is the existing fun lenses from v2. Instead of building a deck, it outputs cards.
- **`packs/coaching.md`** covers the teachable moments: what went well, what could be even better, and why. It works from `coaching_signals.py`.
- **`compose.md`** turns all the cards into one deck in the existing series look, and publishes it.
- **Adding a pack** means writing `packs/<name>.md` that outputs cards in the format below, then switching it on in the config. The composer doesn't need to change.

## The card format (shared by every pack)

Each pack writes a JSON array of cards to `<build>/cards/<pack>.json`:

```json
{
  "id": "coaching.sets-constraints",
  "pack": "coaching",
  "lens": "boundaries",
  "kind": "stat | anchor | coach-win | coach-grow",
  "headline": "Punchy, second person. Ten words or fewer is ideal.",
  "body": "At most 2 short sentences.",
  "why": "coach cards only: the principle behind it, in one sentence",
  "try": "coach cards only: one concrete thing to try, ideally copy-pasteable",
  "evidence": {
    "metric": "by_feature.sets_constraints", "value": 1.0, "n": 20, "compare": 0.79,
    "confidence": "strong | suggestive | anecdote",
    "cites": ["stats.manners"]
  },
  "quote": "optional, 12 words or fewer, passes the privacy rules",
  "viz": { "type": "big-number | bar-compare | dots | timeline | quote | before-after | none", "data": {} },
  "pairs_with": "optional id of a stats card this should follow when placement is inline",
  "score": { "surprise": 0, "evidence": 0, "novelty": 0 }
}
```

**Evidence-backed coaching:** a coach card should cite the numbers behind it (`evidence`), and it can point at a stats card that shows the same thing (`cites` / `pairs_with`). With `placement: "inline"`, the composer puts the tip right after that stat slide. For example, "You asked Codex half the time" can be followed by "Tip: ask for evidence, not reassurance."

## Memory

All editions use `RETRO_HOME/runs.jsonl`, written by `finalize.py`. Compatibility measurement scripts delegate to the plugin; they are not independent copies.
