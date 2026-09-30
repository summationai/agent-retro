# Pack: Stats (the fun lenses)

**Job:** the fun-stats part: numbers, patterns and surprises about how I used AI agents. This pack reuses the existing editions' data and lens logic, but **outputs cards instead of a deck**.

## Data and lenses

Follow **Phases 1–3** of `~/agent-outputs/agent-retro/prompts/retro-prompt-v2.md`. Its extraction rules, memory, honesty rules, fixed anchors, rotating-lens scoring, and "invent one new lens" rule all apply. You can also use the standalone script in `share/retro-paste-in.md`, Appendix B.
- **Skip v2's Phases 4–5.** The composer handles design and publishing.
- **Write the data file** that the extraction step produces to `<build>/retro_data.json`. The coaching pack reads it too.

## Output

Write `<build>/cards/stats.json`: one card per slide, in the shared format (`README.md`).
- **Anchor slides:** `kind: "anchor"`, with ids `stats.cold-open`, `stats.big-number`, `stats.rotation`, `stats.top-projects`, `stats.archetype` and `stats.outro`.
- **Rotating lenses:** `kind: "stat"`, with ids like `stats.<lens>`.
- **Chart data:** put the exact numbers the chart needs in `viz.data`, so the composer never recomputes or invents anything.
- **Memory:** record the lenses you used in the stats memory files, as the original editions do.
