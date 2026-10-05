import copy
import unittest

import support
from deck_schema import validate_deck
from deck_fixtures import components, default_deck


class DeckSchemaTest(unittest.TestCase):
    def test_every_component_and_default_profile(self):
        validate_deck(dict(title='All components',profile='custom',slides=components()))
        validate_deck(default_deck())

    def test_invalid_structures_have_field_errors(self):
        cases=[([], 'slides'),
               ([dict(type='ranking',headline='Projects',rows=[])], 'slides[0].rows'),
               ([dict(type='lineup',headline='Agents',acts=[{}])], 'slides[0].acts[0].agent'),
               ([dict(type='cold',big='1',headline='x',bg='unknown')], 'slides[0].bg'),
               ([dict(type='unknown')], 'slides[0].type')]
        for slides,field in cases:
            with self.subTest(field=field),self.assertRaises(ValueError) as caught:
                validate_deck(dict(title='Invalid',profile='custom',slides=slides))
            self.assertIn(field,str(caught.exception))

    def test_default_profile_enforces_slots_balance_counts_and_tries(self):
        mutations=[lambda d:d['slides'].pop(),
                   lambda d:d['slides'][3].update(kind='tweak'),
                   lambda d:d['slides'][0].update(type='tally',tally=[dict(label='x',value=1)]),
                   lambda d:d['slides'][9]['evidence'].pop(),
                   lambda d:d['slides'][11]['facts'].pop(),
                   lambda d:d['slides'][11]['tries'].__setitem__(0,'An unsupported suggestion'),
                   lambda d:d['slides'][3].pop('evidence_refs')]
        for mutate in mutations:
            deck=default_deck(); mutate(deck)
            with self.subTest(deck=deck),self.assertRaises(ValueError):
                validate_deck(deck)

    def test_quote_limits_and_privacy(self):
        for text in ['word '*13,'[email]','hello audit@example.org','password='+'orchidsecret']:
            with self.subTest(text=text),self.assertRaises(ValueError):
                validate_deck(dict(title='Quote',profile='custom',slides=[dict(type='quote',headline='Quote',quote=text)]))

    def test_evidence_references_resolve_and_back_confidence(self):
        deck=default_deck()
        evidence=dict(stats=dict(tokens=dict(total=1200)),coaching=dict(summary=dict(candidates={})))
        validate_deck(deck,evidence)
        deck['slides'][3]['evidence_refs']=['/coaching/summary/missing']
        with self.assertRaisesRegex(ValueError,'does not resolve'):
            validate_deck(deck,evidence)
        deck['slides'][3]['evidence_refs']=['/coaching/summary/candidates']
        deck['slides'][3]['confidence']='strong signal'
        with self.assertRaisesRegex(ValueError,'comparison groups'):
            validate_deck(deck,evidence)
        evidence['coaching']['summary']['candidates']=dict(confidence='strong signal')
        validate_deck(deck,evidence)
        evidence['stats']['tokens']['total']=1
        with self.assertRaisesRegex(ValueError,'stats.tokens.total'):
            validate_deck(deck,evidence)

    def test_limited_profile_omits_unfounded_coaching(self):
        with self.assertRaisesRegex(ValueError,'limited data'):
            validate_deck(dict(title='Limited',profile='limited',slides=[components()[9]]))
