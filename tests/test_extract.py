"""extract.py against a fake home folder holding synthetic Claude Code, Codex and ChatGPT-export logs."""
import json, os, subprocess, sys, tempfile, time, unittest, zipfile
from datetime import datetime, timezone

import support

EXTRACT = os.path.join(support.SCRIPTS, 'extract.py')


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace('+00:00', 'Z')


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        for r in records:
            f.write(json.dumps(r) + '\n')


class ExtractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        home = cls.home = cls.tmp.name
        now = time.time()
        t = lambda minutes_ago: now - minutes_ago * 60
        cwd = os.path.join(home, 'code', 'demo')
        os.makedirs(cwd)

        # Claude Code: two typed prompts (one enclosed in injected tags), one automation, one assistant reply
        # that two records share (must count its usage once), and a stale prompt outside the window.
        user = lambda when, text, **kw: dict(type='user', sessionId='cc1', timestamp=iso(when), cwd=cwd,
                                             promptSource='typed', message=dict(role='user', content=text), **kw)
        reply = dict(type='assistant', sessionId='cc1', timestamp=iso(t(29)), cwd=cwd,
                     message=dict(id='msg1', model='model-a', content=[dict(type='tool_use', name='Edit', input=dict(file_path=cwd + '/app.py'))],
                                  usage=dict(input_tokens=10, output_tokens=20, cache_read_input_tokens=300, cache_creation_input_tokens=5)))
        write_jsonl(os.path.join(home, '.claude', 'projects', '-demo', 'cc1.jsonl'), [
            user(t(30), 'Add a retro command to the app'),
            reply, dict(reply, timestamp=iso(t(28))),
            user(t(27), '<system-reminder>injected context</system-reminder>ok, now ship it'),
            dict(user(t(26), 'Base directory for this skill: /x'), promptSource=None),
            user(now - 10 * 86400, 'an old prompt from last month'),
        ])

        # Codex: typed prompts come from history.jsonl; usage from token_usage_record.
        write_jsonl(os.path.join(home, '.codex', 'history.jsonl'), [
            dict(session_id='cx1', ts=t(20), text='review the retro command'),
            dict(session_id='cx1', ts=t(19), text='looks good, commit it'),
        ])
        write_jsonl(os.path.join(home, '.codex', 'sessions', '2026', 'rollout-cx1.jsonl'), [
            dict(type='session_meta', timestamp=iso(t(21)), payload=dict(id='cx1', originator='codex-tui', cwd=cwd)),
            dict(type='turn_context', timestamp=iso(t(20)), payload=dict(turn_id='u1', model='model-b', effort='high', cwd=cwd)),
            dict(type='token_usage_record', timestamp=iso(t(20)),
                 payload=dict(response_id='r1', turn_id='u1', usage=dict(input_tokens=1000, cached_input_tokens=800, output_tokens=50))),
        ])

        # ChatGPT export, recognised by structure (not filename), in Downloads.
        conv = dict(id='g1', title='Trip ideas', create_time=t(15), mapping={
            'a': dict(message=dict(author=dict(role='user'), create_time=t(15), content=dict(parts=['Plan a weekend trip']), metadata={})),
            'b': dict(message=dict(author=dict(role='assistant'), create_time=t(14), content=dict(parts=['Here are three ideas']), metadata=dict(model_slug='m'))),
        })
        os.makedirs(os.path.join(home, 'Downloads'))
        with zipfile.ZipFile(os.path.join(home, 'Downloads', 'export-123.zip'), 'w') as z:
            z.writestr('conversations.json', json.dumps([conv]))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_extract(self, **env):
        out = os.path.join(self.home, 'out.json')
        subprocess.run([sys.executable, EXTRACT, out], check=True, capture_output=True, cwd=self.home,
                       env=dict(os.environ, HOME=self.home, **env))
        with open(out) as f:
            return json.load(f)

    def test_reads_every_source(self):
        d = self.run_extract()
        self.assertEqual(sorted(d['sources']), ['chatgpt', 'claude-code', 'codex'])
        by_agent = {}
        for p in d['prompts']:
            by_agent.setdefault(p['agent'], []).append(p['text'])
        self.assertEqual(by_agent['claude-code'], ['Add a retro command to the app', 'ok, now ship it'])
        self.assertEqual(by_agent['codex'], ['review the retro command', 'looks good, commit it'])
        self.assertEqual(by_agent['chatgpt'], ['Plan a weekend trip'])

    def test_strips_injected_tags_and_flags_automation(self):
        d = self.run_extract()
        texts = [p['text'] for p in d['prompts']]
        self.assertFalse(any('system-reminder' in t or 'injected' in t for t in texts))
        self.assertEqual([a['text'] for a in d['automations']], ['Base directory for this skill: /x'])

    def test_drops_prompts_outside_the_window(self):
        d = self.run_extract()
        self.assertNotIn('an old prompt from last month', [p['text'] for p in d['prompts']])

    def test_counts_shared_reply_usage_once(self):
        d = self.run_extract()
        cc = [u for u in d['usage'] if u['agent'] == 'claude-code']
        self.assertEqual(len(cc), 1)
        self.assertEqual((cc[0]['fresh_input'], cc[0]['cache_read'], cc[0]['output']), (10, 300, 20))

    def test_codex_input_excludes_cached_tokens(self):
        d = self.run_extract()
        cx = [u for u in d['usage'] if u['agent'] == 'codex']
        self.assertEqual((cx[0]['fresh_input'], cx[0]['cache_read']), (200, 800))

    def test_projects_never_carry_full_paths(self):
        d = self.run_extract()
        for row in d['prompts'] + d['usage']:
            self.assertNotIn('/', row['project'] or '')
            self.assertNotIn(self.home, json.dumps(row.get('workspace')))

    def test_only_filter(self):
        d = self.run_extract(RETRO_SOURCES='codex')
        self.assertEqual(list(d['sources']), ['codex'])
        self.assertEqual({p['agent'] for p in d['prompts']}, {'codex'})
        d = self.run_extract(RETRO_SOURCES='claude-code,chatgpt')
        self.assertEqual(sorted(d['sources']), ['chatgpt', 'claude-code'])

    def test_days_window(self):
        d = self.run_extract(RETRO_DAYS='30')
        self.assertIn('an old prompt from last month', [p['text'] for p in d['prompts']])


if __name__ == '__main__':
    unittest.main()
