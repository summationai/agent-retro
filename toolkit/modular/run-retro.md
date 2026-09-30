# Agent Retro: modular run

> Paste this into your coding agent. To change which packs run, edit `~/agent-outputs/agent-retro/modular/retro.config.json`, or say so at the end of your message ("coaching only", "no coaching", "placement: section").

Make this week's Agent Retro from content packs, then compose them into one deck. Work through the steps in order, and don't stop to ask me questions unless you're blocked.

1. **Read the config** at `~/agent-outputs/agent-retro/modular/retro.config.json`. Anything I wrote at the end of this message overrides it for this run only.
   - Pick a random seed and print it.
   - Create a build folder: `~/agent-outputs/agent-retro/modular/build-YYYY-MM-DD/`.
2. **Get the data**, whether or not the stats pack is enabled:
   - Run `~/agent-outputs/agent-retro/extract.py <build>/retro_data.json`. If it doesn't exist, use the script from `share/retro-paste-in.md`, Appendix B.
3. **Run each enabled pack** in this order: stats, then coaching, then any other packs listed. For each one, follow `modular/packs/<pack>.md` and write `<build>/cards/<pack>.json`. Coaching runs after stats so it can cite the stat cards.
4. **Compose**, following `modular/compose.md`: order, pairing, design, the tone, privacy and number passes, then save, publish, record in memory, and report.
