"""Remove legacy raw build files; redacted coaching evidence is safe to retain.

Usage: python3 cleanup.py <build-dir>
New prepare.py builds never write raw transcripts to disk.
"""
import argparse
from pathlib import Path
from io_utils import read_json


def cleanup(build):
    removed = []
    for name in ('data.json', 'retro_data.json'):
        path = Path(build) / name
        if path.is_file() or path.is_symlink():
            path.unlink()
            removed.append(name)
    for name in ('coaching.json', 'coaching_signals.json'):
        path = Path(build) / name
        if not path.exists() and not path.is_symlink():
            continue
        try:
            safe = not path.is_symlink() and read_json(path).get('privacy') == 'redacted-v1'
        except (OSError, ValueError, AttributeError):
            safe = False
        if not safe:
            path.unlink()
            removed.append(name)
    return removed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build')
    args = parser.parse_args()
    for name in cleanup(args.build):
        print('removed', name)
