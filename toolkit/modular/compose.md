# Composer

**Job:** turn every enabled pack's cards into one Agent Retro deck, then publish it. The composer never computes new numbers. Everything comes from the cards' `evidence` and `viz.data`.

## Default profile: `default-12`

When `profile` is `default-12`, which is the default, use the fixed 12-slot plan from `~/agent-outputs/agent-retro/plugins/agent-retro/reference/deck-spec.md`: 8 stats slides and 4 coaching slides (at least 2 of them wins), with each coaching slide placed right after the stat it cites. You can also render with that plugin's `scripts/render.py`. Use the other placements and slide ranges only when `profile` is `custom`.

## Order

1. **Cold open.** From `anchors_from`. If that pack is off, write a short cold open from the strongest card that's left.
2. **The big number**, then the **rotation**, then **top projects**. These are the stats anchors, when stats is on.
3. **The stats rotating cards.**
   - With `placement: inline` or `both`: any coach card with `pairs_with` goes straight after its stat card, as a small "💡 Level up" follow-on slide in a lighter treatment.
4. **"Level up" section** (placement `section` or `both`).
   - A divider slide opens it: *"Level up: what's working, and how to make it even better."*
   - Then the coach cards that weren't placed inline: wins first, then growth.
5. **Archetype.** Coaching can add one line of flavor to it ("…and your secret sauce is boundaries").
6. **Try this week.** Up to `try_this_week` checkboxes taken from the coaching pack's `try` lines. The boxes are clickable, purely as a visual.
7. **Outro / share card.** It includes one coaching highlight.

Respect each pack's `slides` range. If there are more cards than slots, keep the highest `score` totals, but always keep at least one win for every growth card.

## Visual language

- **Same series:**
  - one self-contained HTML file with full-viewport scroll-snap slides
  - keyboard, tap and swipe navigation, and a story-style progress bar
  - count-ups, staggered reveals, confetti on the archetype
  - `prefers-reduced-motion` respected
  - riso-print look, with the palette variant picked by the seed
  - agent colors fixed: Claude Code pink, Codex blue, ChatGPT green, claude.ai orange
- **Coaching slides look related but distinct.** A "Level up" tab or eyebrow, and a small icon of a lightbulb or an arrow pointing up.
  - Wins get a gold star mark.
  - Growth cards get a "one small tweak" ribbon.
  - Each coach slide has three parts, in the same place every time:
    - **the moment:** a stat or quote
    - **why it works:** one line from the card's `why`
    - **try this:** the card's `try`, in a copyable monospace box with a Copy button
- **Confidence** appears as a small chip: "strong signal", "early signal", or "one moment".
- **Charts:**
  - a `before-after` viz is two bars, "with" and "without", with n labels
  - a `dots` viz is identical dots
  - a `timeline` viz is a small vertical timeline

## Checks before publishing

1. **Tone pass** on the finished HTML. There must be no "wrong", "bad", "mistake", "poor", "fail", "should have", or close synonyms. Every growth card has a `try`, and the deck has at least as many wins as growth cards.
2. **Privacy pass:** no secrets, credentials, tokens, emails or other people's names in any quote.
3. **Number pass.** Every number shown appears in a card's `evidence` or `viz.data`.

## Ship

- **Save the deck** to `~/agent-outputs/agent-retro/retro-modular-YYYY-MM-DD.html`.
- **Publish** it as a private page titled "Agent Retro, <week range>". If only coaching is on, call it "Agent Retro Level Up, <week range>".
- **Append the run** to the modular memory file, recording which packs ran, the card ids and scores, and the placement.
- **Report back in chat:** the link, which packs ran, the slide list grouped by pack, and the 3 "try this week" lines.
