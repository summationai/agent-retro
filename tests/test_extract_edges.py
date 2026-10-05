"""Synthetic source fixtures for session merging, coverage, branches, and format drift."""
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import support
from extract import config, extract, Extractor
from test_extract import iso, write_jsonl

NOW = 1800000000


def event(kind, payload, age=60):
    return dict(type=kind, timestamp=iso(NOW - age), payload=payload)


def user(text, age=60):
    return event('response_item', dict(type='message', role='user', content=[dict(type='input_text', text=text)]), age)


def counter(total, age=60, last=None):
    usage = dict(input_tokens=total, cached_input_tokens=total // 2, output_tokens=total // 10)
    info = dict(total_token_usage=usage)
    if last is not None:
        info['last_token_usage'] = dict(input_tokens=last, cached_input_tokens=last // 2, output_tokens=last // 10)
    return event('event_msg', dict(type='token_count', info=info), age)


class ExtractEdgesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.downloads = self.home / 'Downloads'
        self.downloads.mkdir()
        self.rollout = self.home / '.codex/sessions/one.jsonl'
        self.meta = event('session_meta', dict(id='one', cwd='/opt/retro-first', originator='codex-tui'), 300)

    def tearDown(self):
        self.tmp.cleanup()

    def run_extract(self, sources='all'):
        return extract(config(str(self.home), NOW, 7, sources))

    def codex(self, rows, history=()):
        write_jsonl(str(self.rollout), [self.meta] + rows)
        if history:
            write_jsonl(str(self.home / '.codex/history.jsonl'), history)

    def test_duplicate_rollouts_and_history_are_reconciled(self):
        self.codex([user('original', 120), user('desktop follow-up', 60)],
                   [dict(session_id='one', ts=NOW-122, text='original')]*2)
        shutil.copyfile(self.rollout, self.rollout.with_name('duplicate.jsonl'))
        d = self.run_extract('codex')
        self.assertEqual([p['text'] for p in d['prompts']], ['original', 'desktop follow-up'])
        self.assertEqual(len({p['id'] for p in d['prompts']}), 2)
        self.assertIn('usage_unavailable', d['diagnostics']['codex']['issues'])

    def test_prompt_keeps_its_turn_directory(self):
        self.codex([event('turn_context', dict(cwd='/opt/retro-first'), 140), user('first', 120),
                    event('turn_context', dict(cwd='/opt/retro-second'), 80), user('second', 60)],
                   [dict(session_id='one', ts=NOW-120, text='first')])
        self.assertEqual([p['project'] for p in self.run_extract('codex')['prompts']], ['retro-first', 'retro-second'])

    def test_counter_fallback_uses_window_delta_and_deduplicates(self):
        before = counter(1000, 8*86400)
        current = counter(1200)
        self.codex([before, current, current, user('ask')])
        usage = self.run_extract('codex')['usage']
        self.assertEqual(len(usage), 1)
        self.assertEqual((usage[0]['fresh_input'], usage[0]['cache_read'], usage[0]['output']), (100,100,20))
        self.assertEqual(usage[0]['measurement'], 'counter_delta')

    def test_first_counter_counts_only_last_response_and_reports_gap(self):
        self.codex([counter(1200, last=200), user('ask')])
        d = self.run_extract('codex')
        self.assertEqual(d['usage'][0]['output'], 20)
        self.assertIn('partial_counter_baseline', d['diagnostics']['codex']['issues'])

    def test_counter_without_baseline_does_not_invent_weekly_usage(self):
        self.codex([counter(1200), user('ask')])
        d = self.run_extract('codex')
        self.assertEqual(d['usage'], [])
        self.assertEqual(d['diagnostics']['codex']['status'], 'partial')

    def test_native_usage_and_counter_are_not_double_counted(self):
        self.codex([event('token_usage_record',dict(response_id='r1',usage=dict(input_tokens=100,cached_input_tokens=50,output_tokens=10))),
                    counter(100, last=100)])
        d = self.run_extract('codex')
        self.assertEqual(len(d['usage']), 1)
        self.assertNotIn('usage_cross_check_mismatch', d['diagnostics']['codex']['issues'])

    def test_counter_reset_is_reported(self):
        self.codex([counter(1000,120),counter(100,60)])
        self.assertIn('token_counter_reset', self.run_extract('codex')['diagnostics']['codex']['issues'])

    def test_history_only_session_is_kept(self):
        write_jsonl(str(self.home / '.codex/history.jsonl'), [dict(session_id='one',ts=NOW-60,text='hello')])
        d=self.run_extract('codex')
        self.assertEqual(len(d['prompts']),1)
        self.assertIn('history_without_rollout',d['diagnostics']['codex']['issues'])

    def test_malformed_records_do_not_abort_valid_records(self):
        self.codex([event('turn_context', []), user('valid')])
        with self.rollout.open('a') as f:
            f.write('{\n[]\n')
        d=self.run_extract('codex')
        self.assertEqual(len(d['prompts']),1)
        self.assertEqual(d['diagnostics']['codex']['malformed_records'],3)

    def test_no_history_file_is_required(self):
        self.codex([user('desktop')])
        self.assertEqual(self.run_extract('codex')['prompts'][0]['text'],'desktop')

    def test_active_chatgpt_branch_only_and_coverage_survives(self):
        def node(text, parent=None):
            return dict(parent=parent,message=dict(author=dict(role='user'),create_time=NOW-60,content=dict(parts=[text])))
        conv=dict(id='chat',current_node='edited',mapping=dict(root=node('start'),old=node('discarded','root'),edited=node('active','root')))
        with zipfile.ZipFile(self.downloads/'chat.zip','w') as z:
            z.writestr('conversations.json',json.dumps([conv]))
            z.writestr('coverage.json',json.dumps(dict(source='app history',scope_note='partial')))
        d=self.run_extract('chatgpt')
        self.assertEqual({p['text'] for p in d['prompts']},{'start','active'})
        self.assertEqual(d['provenance']['chatgpt']['coverage']['scope_note'],'partial')
        self.assertIn('incomplete',d['provenance']['chatgpt']['label'])

    def test_unknown_branches_do_not_create_cross_branch_reactions(self):
        conv=dict(id='chat',mapping={k:dict(parent=None,children=[],message=dict(author=dict(role='user'),create_time=NOW-60,content=dict(parts=[k]))) for k in ['a','b']})
        (self.downloads/'chat.json').write_text(json.dumps([conv]))
        d=self.run_extract('chatgpt')
        self.assertEqual(len({p['session'] for p in d['prompts']}),2)
        self.assertIn('active_branch_unknown',d['diagnostics']['chatgpt']['issues'])

    def test_claude_ai_export_filters_window(self):
        conv=dict(uuid='claude',chat_messages=[dict(sender='human',text='current',created_at=iso(NOW-60)),
                                             dict(sender='assistant',text='reply',created_at=iso(NOW-30)),
                                             dict(sender='human',text='old',created_at=iso(NOW-8*86400))])
        (self.downloads/'claude.json').write_text(json.dumps([conv]))
        d=self.run_extract('claude-ai')
        self.assertEqual([p['text'] for p in d['prompts']],['current'])
        self.assertEqual(len(d['usage']),2)
        self.assertTrue(all(u['estimated'] for u in d['usage']))

    def test_bad_optional_self_report_is_diagnostic(self):
        (self.downloads/'chatgpt-self-report.json').write_text('{')
        os.utime(self.downloads/'chatgpt-self-report.json',(NOW,NOW))
        self.assertIn('invalid_self_report',self.run_extract('chatgpt')['diagnostics']['chatgpt']['issues'])

    def test_future_records_are_excluded_and_ids_are_reproducible(self):
        self.codex([user('future',-100),user('present')])
        one=self.run_extract('codex'); two=self.run_extract('codex')
        self.assertEqual(one,two)
        self.assertEqual([p['text'] for p in one['prompts']],['present'])

    def test_settings_validate_days_sources_and_clock(self):
        for kwargs in [dict(days=0),dict(days=-1),dict(days='x'),dict(sources='unknown'),dict(now=float('nan'))]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                config(**kwargs)

    def test_instances_do_not_share_state(self):
        self.codex([user('first')])
        self.run_extract('codex')
        self.rollout.unlink()
        self.assertEqual(self.run_extract('codex')['prompts'],[])
