"""Delete the build files that contain raw prompt text. Usage: python3 cleanup.py <build-dir>"""
import os, sys
build = sys.argv[1]
for name in ('data.json', 'coaching.json'):
    p = os.path.join(build, name)
    if os.path.exists(p):
        os.remove(p); print('removed', p)
