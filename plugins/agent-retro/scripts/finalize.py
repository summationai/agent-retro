"""Render a prepared deck and record its history once, with a lock and atomic writes.

Usage: python3 finalize.py <build-dir>
Publishing remains a separate host action after this command succeeds.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path

import render
from io_utils import read_json, write_json, write_text
from redact import scrub_tree


def finalize(build):
    build = Path(build).resolve()
    home = build.parent.parent
    if build.parent.name != 'builds':
        raise ValueError('build must be inside RETRO_HOME/builds')
    run = read_json(build / 'run.json')
    if run.get('run_id') != build.name or run.get('status') not in ('ready', 'complete'):
        raise ValueError('build is not ready to finalize')
    out = home / ('retro-' + build.name + '.html')
    if run['status'] == 'complete' and out.is_file():
        return out
    spec = read_json(build / 'slides.json')
    spec['seed'] = run['seed']
    # Rendering must succeed before either history or completion state is changed.
    write_json(build / 'slides.json', spec)
    render.main(build / 'slides.json', out)
    stats = read_json(build / 'stats.json')
    coaching = read_json(build / 'coaching.json')['summary']
    outro = next((s for s in spec['slides'] if s['type'] == 'outro'), {})
    entry = scrub_tree(dict(schema_version=1, run_id=run['run_id'], date=build.name[:10], window=run['window'],
                            seed=run['seed'], sources=run['sources'],
                            slides=[dict(headline=s.get('headline') or s.get('name') or s.get('title'), lens=s.get('lens')) for s in spec['slides']],
                            archetype=next((s['name'] for s in spec['slides'] if s['type'] == 'archetype'), None),
                            tries=outro.get('tries', []), tokens=stats['tokens']['total'],
                            prompts_per_agent={a: v['prompts'] for a, v in stats['agents'].items()},
                            smooth_rate=coaching['smooth_rate']))
    lock = os.open(home / '.history.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        history = home / 'runs.jsonl'
        lines = history.read_text(encoding='utf-8').splitlines() if history.exists() else []
        records = [json.loads(line) for line in lines if line.strip()]
        if not any(r.get('run_id') == run['run_id'] for r in records):
            records.append(entry)
            write_text(history, ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in records))
        run['status'] = 'complete'
        write_json(build / 'run.json', run)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build')
    args = parser.parse_args(argv)
    try:
        print('DECK=' + str(finalize(args.build)))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Cannot finalize: {exc}\n')


if __name__ == '__main__':
    main()
