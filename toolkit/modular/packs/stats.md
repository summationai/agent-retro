# Pack: Stats (the fun lenses)

**Job:** the fun-stats part: numbers, patterns and surprises about how I used AI agents. This pack reuses the existing editions' data and lens logic, but **outputs cards instead of a deck**.

## Data and lenses

Read `BUILD/stats.json` and `BUILD/prompts.txt` from canonical preparation. Use the
stat lens menu, evidence rules, and privacy rules in `plugins/agent-retro/reference/deck-spec.md`.
Preserve diagnostic coverage labels. Do not read raw transcripts or rerun an older extractor.

## Output

Write `<build>/cards/stats.json`: one card per slide, in the shared format (`README.md`).
- **Anchor slides:** `kind: "anchor"`, with ids `stats.cold-open`, `stats.big-number`, `stats.rotation`, `stats.top-projects`, `stats.archetype` and `stats.outro`.
- **Rotating lenses:** `kind: "stat"`, with ids like `stats.<lens>`.
- **Chart data:** put the exact numbers the chart needs in `viz.data`, so the composer never recomputes or invents anything.
- **Memory:** include each chosen lens in the composed slide's `lens` field; finalization records it.
