"""Drift guards for things that must stay copies of each other."""
import json, os, re, unittest

import support

ROOT = support.ROOT


def read(*parts):
    with open(os.path.join(ROOT, *parts)) as f:
        return f.read()


class SyncTest(unittest.TestCase):
    def test_paste_in_prompts_embed_the_current_scripts(self):
        pairs = [(('toolkit', 'share', 'retro-paste-in.md'), ('toolkit', 'share', 'extract_standalone.py'))]
        for md, py in pairs:
            with self.subTest(md[-1]):
                blocks = re.findall(r'```python\n(.*?)```', read(*md), re.S)
                self.assertEqual(len(blocks), 1)
                self.assertEqual(blocks[0], read(*py), f're-embed {py[-1]} in {md[-1]}')

    def test_plugin_manifests_agree(self):
        claude = json.loads(read('plugins', 'agent-retro', '.claude-plugin', 'plugin.json'))
        codex = json.loads(read('plugins', 'agent-retro', '.codex-plugin', 'plugin.json'))
        for key in ('name', 'version', 'license'):
            with self.subTest(key):
                self.assertEqual(claude[key], codex[key])
        self.assertEqual(claude['license'], 'MIT')

    def test_marketplaces_point_at_the_plugin(self):
        claude = json.loads(read('.claude-plugin', 'marketplace.json'))
        codex = json.loads(read('.agents', 'plugins', 'marketplace.json'))
        self.assertEqual([p['source'] for p in claude['plugins']], ['./plugins/agent-retro'])
        self.assertEqual([p['source']['path'] for p in codex['plugins']], ['./plugins/agent-retro'])

    def test_skill_uses_no_host_specific_variables(self):
        skill = read('plugins', 'agent-retro', 'skills', 'retro', 'SKILL.md')
        for var in ('CLAUDE_PLUGIN_ROOT', '$ARGUMENTS'):
            self.assertNotIn(var, skill)


if __name__ == '__main__':
    unittest.main()
