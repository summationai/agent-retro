"""Failure, privacy, atomic-output, portability, and history tests."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import support
import prepare
import finalize
from extract import config
from io_utils import write_json, write_text
from test_extract_edges import NOW, event, user
from test_extract import write_jsonl


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)/'input'
        self.retro = Path(self.tmp.name)/'output'
        self.secret = 'orchid' + 'secret'
        write_jsonl(str(self.home/'.codex/sessions/one.jsonl'), [
            event('session_meta',dict(id='one',cwd='/opt/retro-test',originator='codex-tui'),120),
            user('password=' + self.secret + ' fix this')])
        self.settings = config(str(self.home),NOW,7,'codex')

    def tearDown(self):
        self.tmp.cleanup()

    def run_prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return prepare.prepare(self.settings,self.retro,seed=7)

    def slides(self, build):
        write_json(build/'slides.json',dict(title='Synthetic',profile='custom',slides=[dict(type='cold',big='1',headline='Synthetic week')]))

    def test_private_builds_are_unique_and_never_contain_raw_data(self):
        first,second = self.run_prepare(),self.run_prepare()
        self.assertNotEqual(first,second)
        for build in [first,second]:
            self.assertEqual(build.stat().st_mode & 0o777,0o700)
            self.assertEqual(json.loads((build/'run.json').read_text())['status'],'ready')
            self.assertFalse((build/'data.json').exists())
            for path in build.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777,0o600)
                self.assertNotIn(self.secret,path.read_text())

    def test_failure_and_interruption_leave_no_raw_files(self):
        for failure in [RuntimeError('synthetic error'),KeyboardInterrupt()]:
            with patch.object(prepare.stats,'measure',side_effect=failure):
                with self.assertRaises(type(failure)):
                    self.run_prepare()
        for build in (self.retro/'builds').iterdir():
            self.assertEqual(json.loads((build/'run.json').read_text())['status'],'failed')
            self.assertEqual([p.name for p in build.iterdir()],['run.json'])
            with self.assertRaisesRegex(ValueError,'not ready'):
                finalize.finalize(build)

    def test_finalize_is_idempotent_and_records_the_preparation_seed(self):
        build=self.run_prepare(); self.slides(build)
        with contextlib.redirect_stdout(io.StringIO()):
            one=finalize.finalize(build); two=finalize.finalize(build)
        self.assertEqual(one,two)
        lines=(self.retro/'runs.jsonl').read_text().splitlines()
        self.assertEqual(len(lines),1)
        self.assertEqual(json.loads(lines[0])['seed'],7)
        self.assertEqual(one.stat().st_mode & 0o777,0o600)

    def test_parallel_finalizations_preserve_both_history_records(self):
        builds=[self.run_prepare(),self.run_prepare()]
        for b in builds:
            self.slides(b)
        procs=[subprocess.Popen([sys.executable,str(Path(support.SCRIPTS)/'finalize.py'),str(b)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for b in builds]
        for proc in procs:
            stdout,stderr=proc.communicate(timeout=20)
            self.assertEqual(proc.returncode,0,stderr.decode())
        records=[json.loads(s) for s in (self.retro/'runs.jsonl').read_text().splitlines()]
        self.assertEqual({r['run_id'] for r in records},{b.name for b in builds})

    def test_cleanup_removes_legacy_unredacted_coaching(self):
        from cleanup import cleanup
        build = Path(self.tmp.name) / 'legacy'
        build.mkdir()
        write_json(build / 'coaching.json', {'rows': [{'text': self.secret}]})
        write_json(build / 'retro_data.json', {})
        self.assertEqual(set(cleanup(build)), {'coaching.json', 'retro_data.json'})

    def test_failed_atomic_write_preserves_previous_output(self):
        path=Path(self.tmp.name)/'out.json'
        write_text(path,'old')
        with patch('io_utils.os.replace',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                write_text(path,'new')
        self.assertEqual(path.read_text(),'old')
        self.assertEqual(list(path.parent.glob('.out.json-*')),[])

    def test_atomic_write_does_not_follow_destination_symlink(self):
        target=Path(self.tmp.name)/'target'; target.write_text('original')
        link=Path(self.tmp.name)/'link'; link.symlink_to(target)
        write_text(link,'new')
        self.assertEqual(target.read_text(),'original')
        self.assertFalse(link.is_symlink())

    def test_portable_preparation_and_modular_wrappers_use_redaction(self):
        portable=Path(support.ROOT)/'toolkit/share/extract_standalone.py'
        output=Path(self.tmp.name)/'portable'
        subprocess.run([sys.executable,str(portable),'--home',str(self.home),'--retro-home',str(output),'--now',str(NOW),'--sources','codex'],check=True,capture_output=True)
        build=next((output/'builds').iterdir())
        self.assertFalse((build/'data.json').exists())
        for path in build.iterdir():
            self.assertNotIn(self.secret,path.read_text())
        raw=Path(self.tmp.name)/'raw.json'
        support.data_file(raw,support.prompt_rows(['password='+self.secret+' fix this']*2))
        for module in ['stats','coaching_signals']:
            out=Path(self.tmp.name)/(module+'.json')
            subprocess.run([sys.executable,str(Path(support.ROOT)/'toolkit/modular'/(module+'.py')),str(raw),str(out)],check=True,capture_output=True)
            self.assertNotIn(self.secret,out.read_text())


if __name__ == '__main__':
    unittest.main()
