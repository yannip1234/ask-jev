"""Offline credential-loading regression tests; no real API requests or keys."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/askjev/scripts/askjev'
loader = importlib.machinery.SourceFileLoader('askjev', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
askjev = importlib.util.module_from_spec(spec)
loader.exec_module(askjev)


class DotenvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.env = self.directory / '.env'
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.cwd = patch.object(Path, 'cwd', return_value=self.directory)
        self.cwd.start()
        self.addCleanup(self.cwd.stop)

    def test_environment_wins_without_reading_file(self):
        os.environ['TYPESAFE_API_KEY'] = 'environment-key'
        with patch.object(Path, 'read_text', side_effect=AssertionError('must not read')):
            self.assertEqual(askjev.api_key('missing'), 'environment-key')

    def test_default_file_and_empty_environment_fallback(self):
        os.environ['TYPESAFE_API_KEY'] = ''
        self.env.write_text('TYPESAFE_API_KEY=file-key\n')
        self.assertEqual(askjev.api_key(), 'file-key')

    def test_explicit_file_replaces_default(self):
        self.env.write_text('TYPESAFE_API_KEY=default\n')
        selected = self.directory / 'selected.env'
        selected.write_text('TYPESAFE_API_KEY=selected\n')
        self.assertEqual(askjev.api_key(str(selected)), 'selected')

    def test_literal_syntax_and_duplicates(self):
        cases = [
            ('  export TYPESAFE_API_KEY = unquoted # comment\n', 'unquoted'),
            ('TYPESAFE_API_KEY="quoted#value" # comment\n', 'quoted#value'),
            ("TYPESAFE_API_KEY='${OTHER}$(touch marker)`cmd`'\n", '${OTHER}$(touch marker)`cmd`'),
            ('TYPESAFE_API_KEY=abc#def\n', 'abc#def'),
            ('\ufeff# comment\r\nOTHER=ignored\r\nTYPESAFE_API_KEY=first\r\nTYPESAFE_API_KEY=last\r\n', 'last'),
            ('TYPESAFE_API_KEY= # comment\n', ''),
            ('UNRELATED="unfinished\n', ''),
        ]
        for content, expected in cases:
            with self.subTest(content=content):
                self.env.write_text(content)
                self.assertEqual(askjev.api_key(), expected)
        self.assertFalse((self.directory / 'marker').exists())

    def test_missing_files(self):
        self.assertEqual(askjev.api_key(), '')
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            askjev.api_key(str(self.env))

    def test_bad_quotes_do_not_echo_secret(self):
        for value in ['"private-key', "'private-key' junk", '"private-key\ncontinuation"']:
            self.env.write_text('TYPESAFE_API_KEY=' + value)
            with self.assertRaises(ValueError) as raised:
                askjev.api_key()
            self.assertNotIn('private-key', str(raised.exception))

    def run_cli(self, extra=()):
        stdout, stderr = io.StringIO(), io.StringIO()
        argv = [str(SCRIPT), '--state', 'Hello', '--question', 'Is this a greeting?', *extra]
        with patch('sys.argv', argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = askjev.main()
        return status, stdout.getvalue(), stderr.getvalue()

    def test_dry_run_never_loads_credentials(self):
        with patch.object(askjev, 'api_key', side_effect=AssertionError('must not load')):
            status, output, error = self.run_cli(['--dry-run', '--env-file', 'missing'])
        self.assertEqual(status, 0, error)
        self.assertEqual(json.loads(output)['state'], 'Hello')

    def test_dotenv_key_reaches_private_curl_header_only(self):
        self.env.write_text("TYPESAFE_API_KEY='synthetic-secret'\n")
        def fake_curl(argv, **kwargs):
            self.assertNotIn('synthetic-secret', ' '.join(argv))
            self.assertNotIn('synthetic-secret', kwargs['input'])
            header = Path(argv[argv.index('--header') + 1][1:])
            self.assertIn('Authorization: Bearer synthetic-secret', header.read_text())
            self.assertEqual(header.stat().st_mode & 0o777, 0o600)
            response = Path(argv[argv.index('--output') + 1])
            response.write_text(json.dumps({'answers': {'answer': {'type': 'noul', 'noul': 0.99}}}))
            return subprocess.CompletedProcess(argv, 0, stdout='200', stderr='')
        with patch.object(askjev.shutil, 'which', return_value='/fake/curl'), patch.object(askjev.subprocess, 'run', side_effect=fake_curl):
            status, output, error = self.run_cli()
        self.assertEqual(status, 0, error)
        self.assertEqual(json.loads(output)['answers']['answer']['noul'], 0.99)
        self.assertNotIn('synthetic-secret', output + error)

    def test_missing_key_and_header_injection_stop_before_network(self):
        for content in ['', 'TYPESAFE_API_KEY=bad\x00key']:
            self.env.write_text(content)
            with patch.object(askjev.subprocess, 'run', side_effect=AssertionError('no network')):
                status, output, error = self.run_cli()
            self.assertEqual(status, 1)
            self.assertNotIn('bad\x00key', error)


if __name__ == '__main__':
    unittest.main()
