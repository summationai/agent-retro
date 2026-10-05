"""Compatibility entry point; the plugin implementation is canonical."""
import runpy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / 'plugins/agent-retro/scripts'
sys.path.insert(0, str(SCRIPTS))
implementation = runpy.run_path(str(SCRIPTS / 'coaching_signals.py'))
main = implementation['main']

if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Usage: python3 coaching_signals.py <data.json> <out.json>')
    main(sys.argv[1], sys.argv[2])
