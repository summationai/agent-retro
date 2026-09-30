"""Drift guards for things that must stay copies of each other."""
import os, re, unittest

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


if __name__ == '__main__':
    unittest.main()
