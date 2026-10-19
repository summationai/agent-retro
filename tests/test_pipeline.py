"""End to end: secrets in prompts must not reach any file or console output the deck writer reads."""
import contextlib, io, json, os, subprocess, sys, tempfile, unittest

import support
from support import SECRETS, data_file, prompt_rows


def read(*parts):
    with open(os.path.join(*parts)) as f:
        return f.read()


stats = support.load(os.path.join(support.SCRIPTS, 'stats.py'), 'retro_stats')
coaching = support.load(os.path.join(support.SCRIPTS, 'coaching_signals.py'), 'retro_coaching')
cleanup = os.path.join(support.SCRIPTS, 'cleanup.py')


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        texts = []
        for _, text, _ in SECRETS:
            texts += [f'Please set this up: {text}', 'ok, now ship it']
        # a repeated prompt with a secret lands in stats.json's "repeats"
        texts += [f'deploy with {SECRETS[0][1]} again'] * 3
        # a long prompt whose secret sits right at the 400-char cut of prompts.txt
        texts.append('x ' * 190 + SECRETS[1][1])
        self.texts = texts
        self.data = data_file(os.path.join(self.dir, 'data.json'), prompt_rows(texts))

    def tearDown(self):
        self.tmp.cleanup()

    def run_scripts(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            stats.main(self.data, os.path.join(self.dir, 'stats.json'))
            coaching.main(self.data, os.path.join(self.dir, 'coaching.json'))
        return out.getvalue()

    def test_no_secret_reaches_any_output(self):
        console = self.run_scripts()
        outputs = {name: read(self.dir, name).lower() for name in ('prompts.txt', 'stats.json', 'coaching.json')}
        outputs['console'] = console.lower()
        for kind, _, fragment in SECRETS:
            for name, body in outputs.items():
                with self.subTest(kind=kind, output=name):
                    self.assertNotIn(fragment.lower(), body)  # case-insensitive: some outputs lowercase text

    def test_outputs_still_carry_the_prompts(self):
        self.run_scripts()
        lines = read(self.dir, 'prompts.txt').splitlines()
        self.assertEqual(len(lines), len(self.texts))
        self.assertIn('ok, now ship it', lines[1])
        st = json.loads(read(self.dir, 'stats.json'))
        self.assertEqual(st['prompts'], len(self.texts))
        self.assertTrue(st['repeats'] and '[redacted:key]' in st['repeats'][0]['text'])
        self.assertGreater(sum(st['redactions'].values()), len(SECRETS))
        rows = json.loads(read(self.dir, 'coaching.json'))['rows']
        self.assertEqual(len(rows), len(self.texts))
        self.assertEqual(rows[1]['text'], 'ok, now ship it')

    def test_reactions_are_read_from_raw_text(self):
        # redaction happens on the way out, so it must not change the coaching numbers
        self.run_scripts()
        summary = json.loads(read(self.dir, 'coaching.json'))['summary']
        self.assertGreaterEqual(summary['reaction_counts'].get('proceed', 0), len(SECRETS))

    def test_metadata_and_derived_words_are_redacted(self):
        secret = 'orchid' + 'secret'
        email = 'audit.person' + '@example.org'
        d = json.loads(read(self.data))
        d['prompts'][0].update(text=support.credential_prompt(secret, 'fix it'), project=email, session=email)
        d['usage'][0].update(project=email, branch='fix/' + email, model=email)
        d['sources'] = {email: email + '.zip'}
        d['tools'] = [dict(name='Edit', file_path='/tmp/' + email, skill=email)]
        d['sessions'] = {email: dict(first=1, last=2, project=email, agent='codex', prompts=1)}
        with open(self.data, 'w') as f:
            json.dump(d, f)
        console = self.run_scripts()
        for output in [console] + [read(self.dir, n) for n in ('stats.json', 'coaching.json', 'prompts.txt')]:
            self.assertNotIn(secret, output)
            self.assertNotIn(email, output)

    def test_self_report_and_coverage_reach_safe_outputs(self):
        d = json.loads(read(self.data))
        d['self_report'] = dict(one_surprising_observation='hello audit@example.org')
        d['provenance'] = dict(chatgpt=dict(coverage=dict(source='app history', scope_note='partial')))
        with open(self.data, 'w') as f:
            json.dump(d, f)
        self.run_scripts()
        result = json.loads(read(self.dir, 'stats.json'))
        self.assertTrue(result['self_report']['flavor_only'])
        self.assertEqual(result['self_report']['content']['one_surprising_observation'], 'hello [email]')
        self.assertEqual(result['provenance']['chatgpt']['coverage']['scope_note'], 'partial')

    def test_cleanup_removes_raw_files_only(self):
        self.run_scripts()
        subprocess.run([sys.executable, cleanup, self.dir], check=True, capture_output=True)
        left = sorted(os.listdir(self.dir))
        self.assertEqual(left, ['coaching.json', 'prompts.txt', 'stats.json'])

    def test_agent_launches_form_their_own_bucket(self):
        with open(self.data) as f:
            d = json.load(f)
        ts = d['prompts'][0]['ts']
        codex = lambda model, transcript=False: dict(agent='codex', via='autoreview', model=model, effort='high', transcript=transcript)
        d['launches'] = [
            dict(ts=ts, caller='claude-code', session='s1', project='demo', workspace='demo', callees=[codex('big')], seconds=120, status='completed'),
            dict(ts=ts, caller='claude-code', session='s1', project='demo', workspace='demo', callees=[codex(None)], seconds=None, status=None),
            dict(ts=ts, caller='claude-code', session='s1', project='demo', workspace='demo', callees=[codex('big', True), codex('small')], seconds=60, status='failed'),
        ]
        d['usage'].append(dict(d['usage'][0], agent='codex', headless=True))
        with open(self.data, 'w') as f:
            json.dump(d, f)
        self.run_scripts()
        out = json.loads(read(self.dir, 'stats.json'))
        route = out['delegation']['routes']['claude-code->codex']
        self.assertEqual((out['delegation']['launches'], out['delegation']['minutes']), (3, 3.0))
        self.assertEqual({k: route[k] for k in ('calls', 'timed_calls', 'minutes', 'failed', 'no_token_record')},
                         dict(calls=4, timed_calls=2, minutes=3.0, failed=1, no_token_record=3))
        self.assertEqual(route['models'], {'big': 2, 'not recorded': 1, 'small': 1})
        self.assertEqual(out['agents']['codex']['launched_by_agents'], dict(calls=4, minutes=3.0))
        self.assertGreater(out['delegation']['headless_tokens']['codex'], 0)


if __name__ == '__main__':
    unittest.main()
