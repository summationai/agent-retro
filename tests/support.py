"""Shared helpers for the test suite. Standard library only; runs on Python 3.9+.

Fake secrets are assembled at runtime from fragments, so no file in the repo contains a literal
credential that secret scanners (or a curious reader) would flag.
"""
import importlib.util, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'plugins', 'agent-retro', 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def load(path, name):
    """Import a script by path (the toolkit scripts aren't packages)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def j(*parts):
    return ''.join(parts)


# (kind, text containing the secret, the fragment that must never survive)
SECRETS = [
    ('aws access key id', j('use AK', 'IA', 'Z7Q4XW2N8R5T1Y3U', ' for the bucket'), 'Z7Q4XW2N8R5T1Y3U'),
    ('aws secret, labeled', j('aws_secret_access_key = ', 'wJalrXUtnFEMI/K7MDENG/', 'bPxRfiCYzq81mVn3'), 'bPxRfiCYzq81mVn3'),
    ('anthropic-style key', j('my key is sk-', 'ant-', 'api03-Qx7vT2mK9pL4nR8s'), 'Qx7vT2mK9pL4nR8s'),
    ('openai-style key', j('OPENAI key sk-', 'proj-', 'Hd83kQm2Lp9Zx4Vn7Rt1'), 'Hd83kQm2Lp9Zx4Vn7Rt1'),
    ('github token', j('token gh', 'p_', 'aB3dE5gH7jK9mN1pQ3sT5vW7yZ9bC1dE3fG5'), 'aB3dE5gH7jK9mN1pQ3sT5vW7yZ9bC1dE3fG5'),
    ('github fine-grained pat', j('github_', 'pat_', '11ABCDEFG0123456789_qrstuvwxyzabcdefgh'), 'qrstuvwxyzabcdefgh'),
    ('slack bot token', j('xo', 'xb-', '1234567890-abcdefghijkl'), 'abcdefghijkl'),
    ('slack webhook', j('post to https://hooks.slack.com/services/', 'T0001/B0001/', 'q' * 24), 'q' * 24),
    ('stripe live key', j('sk', '_live_', 'Zq81mVn3Lp9Zx4Vn7Rt1'), 'Zq81mVn3Lp9Zx4Vn7Rt1'),
    ('google api key', j('AI', 'za', 'SyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY'), 'SyD-9tSrke72PouQMnMX'),
    ('jwt', j('ey', 'JhbGciOiJIUzI1NiJ9', '.eyJzdWIiOiIxMjM0NTY3ODkwIn0', '.dozjgNryP4J3jVmNHl0w5N'), 'dozjgNryP4J3jVmNHl0w5N'),
    ('bearer header', j('Authorization: Bearer ', 'mF_9.B5f-4.1JqM-zXc8Vb7Nm'), 'mF_9.B5f-4.1JqM'),
    ('url query secret', j('callback https://x.example/cb?code=', 'Qm9rZWQ5NTA0', '&state=1'), 'Qm9rZWQ5NTA0'),
    ('db url credentials', j('postgres://admin:', 'hunter2horse', '@db.internal:5432/app'), 'hunter2horse'),
    ('json password', j('{"password": "', 'correct-horse-battery', '"}'), 'correct-horse-battery'),
    ('password-like word', j('log in with ', 'Tr0ub4dor&3x', ' please'), 'Tr0ub4dor&3x'),
    ('lowercase hex secret', j('webhook secret ', 'deadbeef' * 5), 'deadbeef' * 5),
    ('private key block', j('-----BEGIN ', 'RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA7x\n-----END RSA PRIVATE KEY-----'), 'MIIEowIBAAKCAQEA7x'),
    ('private key, cut off', j('-----BEGIN ', 'OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjE'), 'b3BlbnNzaC1rZXktdjE'),
    ('email', j('ping jane.', 'doe@', 'example.com about it'), 'jane.doe'),
    ('us phone', j('call (415) 555-', '0134 today'), '555-0134'),
    ('intl phone', j('whatsapp +44 20 7946 ', '0958'), '7946 0958'),
    ('card number', j('card 4111 1111 ', '1111 1111 exp 12/29'), '1111 1111 1111'),
    ('ssn', j('ssn 078-05-', '1120'), '078-05-1120'),
    ('macOS home folder', j('see /Users/', 'jdoe-secret', '/code/app/main.py'), 'jdoe-secret'),
    ('linux home folder', j('see /home/', 'jdoe-secret', '/app'), 'jdoe-secret'),
    ('windows home folder', j('see C:\\Users\\', 'jdoe-secret', '\\app'), 'jdoe-secret'),
]

# Ordinary prompt text that must come through unchanged.
BENIGN = [
    'Fix the bug in src/app/main.py line 42, then run the tests.',
    'We used 1,234,567 tokens on 2026-10-05 at 14:30, about 12% more than v1.2.3.',
    'Set max_tokens=4096 and temperature 0.7; commit abc1234 looks good.',
    'Open https://github.com/summationai/agent-retro/pull/12?tab=files',
    'The ticket is ENG-1234 and the PR is #567. Call it at 3pm.',
    'Use the uuid 123e4567-e89b-12d3-a456-426614174000 as the id.',
    'My branch is feature/add-retro-skill and the folder is /Users/Shared/data.',
    'Rename getUserById to fetchUser; keep it under 80 chars.',
    'the token count is 2048 and the api key lives in the env var OPENAI_API_KEY',
    'Order #4111-1111 shipped; tracking 1Z999 arrives Tue.',
    'Run it 3 times: 10.0.0.1, then 192.168.1.20, then localhost:8080.',
]


def prompt_rows(texts, agent='claude-code', session='s1', start=None, project='demo'):
    """Extractor-shaped prompt rows, one minute apart."""
    start = start or time.time() - 3600
    return [dict(ts=start + 60 * i, agent=agent, surface='cli', project=project, workspace=project, session=session,
                 text=t, is_automation=False, branch=None) for i, t in enumerate(texts)]


def usage_row(ts, agent='claude-code', session='s1', project='demo', output=100):
    return dict(ts=ts, agent=agent, model='model-x', effort=None, project=project, workspace=project, session=session,
                side=False, branch=None, fresh_input=50, cache_read=200, cache_write=10, output=output, reasoning=0, estimated=False)


def data_file(path, prompts, usage=None):
    now = time.time()
    usage = usage if usage is not None else [usage_row(p['ts'], p['agent'], p['session'], p['project']) for p in prompts]
    sessions = {}
    for p in prompts:
        s = sessions.setdefault(f"{p['agent']}:{p['session']}", dict(agent=p['agent'], sid=p['session'], first=p['ts'], last=p['ts'],
                                                                    cwd=None, surface='cli', prompts=0, project=p['project'], title=None))
        s['last'] = max(s['last'], p['ts']); s['prompts'] += 1
    with open(path, 'w') as f:
        json.dump(dict(generated=now, cut=now - 7 * 86400, sources={'claude-code': 'test'}, codex_check={}, self_report=None,
                       prompts=prompts, automations=[], usage=usage, sessions=sessions, tools=[]), f)
    return path
