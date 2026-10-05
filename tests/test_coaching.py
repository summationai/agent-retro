"""Reaction semantics, stable evidence IDs, comparison confidence, and large correction runs."""
import contextlib
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

import support
import coaching_signals as coaching
import stats


class CoachingTest(unittest.TestCase):
    def measure(self, prompts):
        with tempfile.TemporaryDirectory() as tmp:
            src=support.data_file(Path(tmp)/'data.json',prompts)
            with contextlib.redirect_stdout(io.StringIO()):
                return coaching.main(src,Path(tmp)/'coaching.json')

    def test_reaction_examples_and_false_positives(self):
        cases={'Perfect, thanks!':'praise','🎉':'praise','OK, go ahead':'proceed',
               'No, still broken':'correct','Thanks, but this is still failing':'correct',
               'Please continue':'infra','Run the regression suite':'new-ask','This is a regression':'correct',
               'Explore the next feature':'new-ask','':'unknown'}
        for text,expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(coaching.reaction(text),expected)

    def test_same_session_nonconsecutive_repeat_is_not_a_fresh_session_retry(self):
        d=self.measure(support.prompt_rows(['Run the complete regression suite','Explore a different feature','Run the complete regression suite']))
        self.assertEqual(d['rows'][0]['next_reaction'],'new-ask')
        self.assertEqual(d['summary']['repeats']['prompts_resent'],0)

    def test_cross_session_retries_expire_after_a_day(self):
        rows=support.prompt_rows(['Run the complete regression suite'],session='a',start=100)
        rows+=support.prompt_rows(['Run the complete regression suite'],session='b',start=200)
        rows+=support.prompt_rows(['Run the complete regression suite'],session='c',start=90000)
        d=self.measure(rows)
        self.assertEqual([r['next_reaction'] for r in d['rows']],['retry','end','end'])

    def test_digest_and_coaching_share_ids_for_interleaved_sessions(self):
        prompts=support.prompt_rows(['First A','Second A'],session='a',start=100)
        prompts+=support.prompt_rows(['First B'],session='b',start=130)
        with tempfile.TemporaryDirectory() as tmp:
            src=support.data_file(Path(tmp)/'data.json',prompts)
            with contextlib.redirect_stdout(io.StringIO()):
                stats.main(src,Path(tmp)/'stats.json')
                measured=coaching.main(src,Path(tmp)/'coaching.json')
            ids=[line.split(']')[0][1:] for line in (Path(tmp)/'prompts.txt').read_text().splitlines()]
        self.assertEqual(ids,[r['id'] for r in measured['rows']])
        self.assertEqual(measured['rows'][0]['next_id'],measured['rows'][2]['id'])

    def test_confidence_requires_both_comparison_groups(self):
        def sample(with_n,without_n):
            rows=[]
            for i in range(with_n+without_n):
                constrained=i<with_n
                text=('Only change this feature' if constrained else 'Update this feature')+f' request {i}'
                rows+=support.prompt_rows([text,'Great work' if constrained else 'No, still broken'],session=str(i),start=100+i*120)
            return self.measure(rows)['summary']['by_feature']['sets_constraints']
        small=sample(30,1)
        self.assertEqual(small['confidence'],'small sample · 1')
        strong=sample(20,20)
        self.assertEqual(strong['confidence'],'strong signal')
        self.assertEqual((strong['with_successes'],strong['without_successes']),(20,0))
        self.assertEqual(sample(20,0)['confidence'],'insufficient comparison')

    def test_optimized_chains_match_the_defined_scan(self):
        rng=random.Random(7)
        for _ in range(50):
            words=[rng.choice('abc') for _ in range(100)]
            reactions=[rng.choice(['correct','infra','praise','new-ask']) for _ in words]
            expected=[]
            for i,word in enumerate(words):
                j,extra=i+1,0
                while j<len(words) and (reactions[j] in ('correct','infra') or words[j]==word):
                    extra+=reactions[j]=='correct' or words[j]==word
                    j+=1
                expected.append(extra)
            self.assertEqual(coaching.correction_chains(words,reactions),expected)
        self.assertEqual(coaching.correction_chains(['a']*20000,['correct']*20000)[0],19999)

    def test_empty_stats_have_zero_streak(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=support.data_file(Path(tmp)/'data.json',[])
            with contextlib.redirect_stdout(io.StringIO()):
                result=stats.main(src,Path(tmp)/'stats.json')
        self.assertEqual(result['longest_streak'],dict(prompts=0,agent=None))


if __name__ == '__main__':
    unittest.main()
