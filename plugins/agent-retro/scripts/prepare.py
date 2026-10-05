"""Prepare a private, redacted build. Raw transcripts are never written to disk.

Usage: python3 prepare.py [--retro-home PATH] [--days N] [--sources codex,chatgpt]
"""
import argparse
import os
import secrets
import tempfile
from datetime import datetime, timezone

import coaching_signals
import stats
from contracts import SCHEMA_VERSION
from extract import config, extract
from io_utils import private_directory, write_json
from redact import scrub_tree


def prepare(settings, retro_home, seed=None):
    home = private_directory(retro_home)
    builds = private_directory(home / 'builds')
    date = datetime.fromtimestamp(settings.now, timezone.utc).strftime('%Y-%m-%d')
    build = private_directory(tempfile.mkdtemp(prefix=date + '-', dir=str(builds)))
    run = dict(schema_version=SCHEMA_VERSION, run_id=build.name, created=settings.now,
               seed=secrets.randbelow(2**31) if seed is None else seed, status='preparing')
    write_json(build / 'run.json', run)
    try:
        data = extract(settings)
        measured = stats.measure(data, build / 'stats.json')
        coaching_signals.measure(data, build / 'coaching.json')
        run.update(status='ready', sources=measured['sources'], window=measured['window'])
        write_json(build / 'run.json', scrub_tree(run))
    except BaseException:
        # No raw files exist, including on interruption. Incomplete builds cannot be finalized.
        run['status'] = 'failed'
        write_json(build / 'run.json', run)
        raise
    return build


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retro-home', default=os.environ.get('AGENT_RETRO_HOME', '~/agent-retro'))
    parser.add_argument('--home', help='input home directory (defaults to the current user)')
    parser.add_argument('--now', type=float)
    parser.add_argument('--days', default=os.environ.get('RETRO_DAYS', '7'))
    parser.add_argument('--sources', default=os.environ.get('RETRO_SOURCES', 'all'))
    parser.add_argument('--export', action='append', default=[])
    parser.add_argument('--seed', type=int)
    args = parser.parse_args(argv)
    try:
        settings = config(args.home, args.now, args.days, args.sources, args.export)
    except ValueError as exc:
        parser.error(str(exc))
    build = prepare(settings, args.retro_home, args.seed)
    print('BUILD=' + str(build))


if __name__ == '__main__':
    main()
