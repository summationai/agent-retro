"""Private, atomic output files. No process-wide umask changes."""
import json
import os
import tempfile
from pathlib import Path


def write_text(path, text):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    write_text(path, json.dumps(value, indent=1, ensure_ascii=False, allow_nan=False) + '\n')


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def private_directory(path):
    path = Path(path).expanduser()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path.resolve()
