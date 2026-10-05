# Pack: Coaching (teachable moments)

**Job:** find what's going well, what could be even better, and **why**. Turn each finding into a small card that's evidence-backed, fun, and takes one glance to understand. This pack only writes `cards/coaching.json`. Look and publishing are the composer's job.

## Tone (non-negotiable)

- **Celebrate first.** Every deck leads with wins. Growth cards are about a *situation* ("when a paste arrives with no instruction…"), never about a person's failing.
- **Never say** wrong, bad, mistake, poor, fail, failed, should have, don't do, weak, or any close synonym. Say "even better", "one small tweak", "try", "level up", "next time", "bonus points".
- **Every growth card carries a `try`:** one concrete, low-effort step, ideally copy-pasteable (a phrase, a line for AGENTS.md or your agent's equivalent, a slash command).
- **Growth cards come in wins' clothing:** name what already worked in that moment, then the tweak that would make it land in one go.
- **No scolding about volume, cost, hours or tools.** How much someone uses AI is never a coaching point.

## Evidence rules

1. **Read `BUILD/coaching.json`** from canonical preparation; its rows are already redacted.
   For every prompt, it reads the reaction of the *next* message in the same session:
   - `praise`, `proceed`: it worked
   - `correct`: an extra round-trip
   - `retry`: re-sent
   - `infra`: an outage or a resume
   - `end`: no next message

   It also tags each prompt with features: gives context, explains why, defines done, sets constraints, plan first, gives an example, numbered steps, delegates, pastes evidence, terse, long brief. It computes smooth rates with and without each feature, and extras such as repeats, reminders and yes/no check-ins. Its caveat applies: these are **proxies**, so say so in small print.
2. **Two kinds of "worked", and every card uses at least one:**
   - **Internal:** my own reaction shows it worked (praise or proceed), or took extra round-trips (correct or retry). Read the actual prompt, the next message, and the neighbouring turns before you explain *why*. Don't explain from the feature tags alone.
   - **External:** a well-known practice, from the list below, that explains the pattern or suggests the tweak.
3. **Label confidence** using the computed feature confidence in `coaching.json`. Both comparison groups must meet the sample threshold (20 for strong, 8 for early). Small samples are anecdotes; a missing comparison group is not a measurable lift. Preserve evidence JSON pointers when composing the slides.
4. **Link to stats:** if the stats pack is on, read `cards/stats.json`. When a stat card shows the same behavior, add its id to `evidence.cites` and set `pairs_with`, so the composer can place the tip right after that stat. Coaching can also *reuse* a stat as its evidence instead of repeating it.
5. **Correlation isn't causation, and context matters.** Debugging sessions correct more often than planning sessions whatever the prompt style. Before blaming (or crediting) a feature, check what kind of work it was.
6. **Privacy:**
   - Quotes are 12 words or fewer.
   - Never quote secrets, credentials, tokens, emails or other people's names.

## Well-known practices (the "why" library)

Use these to explain *why* something worked or how to make it even better. Plain language, no links needed.

1. **Say what "done" looks like.** A test to pass, an output to match, a check to run, so the agent can check its own work.
2. **Share the why.** The goal behind the ask lets the agent make good choices you didn't spell out.
3. **Set the boundaries.** Scope, what not to touch, "plan only, no code yet". Fewer guesses, fewer surprises.
4. **Show an example** of the output or style you want.
5. **Plan, then build.** For fuzzy or large work, ask for a plan first and approve it.
6. **Small steps, checkpoints.** Break big work down; commit between steps.
7. **Point at the exact context.** Files, errors, logs, screenshots, links.
8. **Ask for evidence, not reassurance.** "Run it and show me the output" beats "it works, right?"
9. **Write standing preferences down once.** Put things you keep re-stating in AGENTS.md (or your agent's equivalent).
10. **Turn repeats into commands.** A prompt you send over and over wants to be a slash command or a saved prompt.
11. **Reset when tangled.** A fresh session with a crisp restatement often beats a long correction chain.
12. **Delegate in parallel.** Independent chunks go to subagents at the same time.
13. **Lead with the instruction when pasting.** Say what the pasted thing *is* and what to *do* with it before or right after pasting.
14. **Invite questions.** "Ask me if anything's unclear before starting" heads off wrong turns.

## Lenses (seed `coaching-lenses.md` with these; invent at least one new one each run)

- *Your secret sauce*: the feature with the biggest positive lift. Show it with a before/after bar.
- *First-try hits*: long briefs that got an immediate proceed or praise. Say what they had in common.
- *Best-received prompt*: the prompt that drew the warmest praise, and why it worked.
- *The one-tweak moment*: the longest correction chain, retold kindly. Say what was already right, and the one line that would have saved the round-trips.
- *Evidence over reassurance*: how yes/no check-ins fared compared with the average.
- *Say it once*: standing instructions re-stated with "again, …". Offer a ready-to-paste AGENTS.md (or your agent's equivalent) line.
- *Make it a command*: repeated prompts. Offer a ready-to-save slash command.
- *Paste with a label*: pasted documents followed by confusion. Offer an intro line to paste above them next time.
- *Plan-first payoff*: how plan-first prompts fared, and what followed them.
- *Reset button*: long tangled sessions where a fresh start would have been quicker.
- *Try this week* (always last): the 3 highest-impact `try`s, each 12 words or fewer, as a checklist.

## Mix and voice

- **Aim for this mix:** 2–3 `coach-win` cards, 1–3 `coach-grow` cards, and the *Try this week* card. The config sets the total.
- **Voice:** second person ("you"), warm and specific. Use real moments, anchored to a day and time when that helps.
- **Start from what worked for you.** Do internal wins first, then external practices.

## Output

Write `<build>/cards/coaching.json`: an array of cards in the shared format (see `README.md`), with a score on each card. Include lens ids in the final slides; finalization records history.
