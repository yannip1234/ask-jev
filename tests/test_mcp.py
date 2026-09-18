"""Exercise the real MCP/CLI boundary; fake only curl's external API response.

Set ASKJEV_TEST_IMAGE to run the same contract suite against Docker.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = {'greeting': {'type': 'noul', 'instructions': 'Is this a greeting?'}}


class MCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.directory.chmod(0o755)
        (self.directory / 'bin').mkdir()
        curl = self.directory / 'bin/curl'
        curl.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
header = pathlib.Path(args[args.index('--header') + 1][1:]).read_text()
expected = os.environ.get('EXPECTED_KEY', 'file-test-key')
if 'Authorization: Bearer ' + expected + '\\n' not in header:
    sys.exit(12)
request = json.load(sys.stdin)
response = pathlib.Path(args[args.index('--output') + 1])
if request['state'] == 'api-error':
    response.write_text('Invalid credential: ' + expected)
    print('401', end='')
else:
    response.write_text(json.dumps({'model': request['model'], 'answers': {
        name: {'type': q['type'], q['type']: 0.97}
        for name, q in request['questions'].items()
    }, 'usage': {'input_tokens': 12, 'output_tokens': 3}}))
    print('200', end='')
''')
        curl.chmod(0o755)

    def client(self, key=None, environment_key='', fake=True):
        server = ROOT / 'askjev_mcp.py'
        self.assertTrue(server.is_file(), 'MCP server entrypoint has not been implemented')
        image = os.environ.get('ASKJEV_TEST_IMAGE')
        env_file = self.directory / 'credentials.env'
        if key is not None:
            env_file.write_text('TYPESAFE_API_KEY=' + repr(key) + '\n')
            env_file.chmod(0o644)  # synthetic credential, readable by container user
        if image:
            args = ['run', '--rm', '-i', '--network=none',
                    '--mount', f'type=bind,src={self.directory},dst=/run/askjev-test,readonly',
                    '-e', 'TYPESAFE_API_KEY=' + environment_key]
            if fake:
                args += ['-e', 'PATH=/run/askjev-test/bin:/usr/local/bin:/usr/bin:/bin',
                         '-e', 'EXPECTED_KEY=' + (environment_key or 'file-test-key')]
            args += [image]
            if key is not None:
                args += ['--env-file', '/run/askjev-test/credentials.env']
            parameters = StdioServerParameters(command='docker', args=args)
        else:
            env = dict(os.environ, TYPESAFE_API_KEY=environment_key)
            if fake:
                env['PATH'] = str(self.directory / 'bin') + os.pathsep + env['PATH']
                env['EXPECTED_KEY'] = environment_key or 'file-test-key'
            args = [str(server)]
            if key is not None:
                args += ['--env-file', str(env_file)]
            parameters = StdioServerParameters(command=sys.executable, args=args, env=env, cwd=self.directory)
        return Client(parameters, read_timeout_seconds=20)

    async def test_discovery_and_dry_run_without_credentials(self):
        async with self.client(fake=False) as client:
            tools = await client.list_tools()
            self.assertEqual([tool.name for tool in tools.tools], ['askjev'])
            result = await client.call_tool('askjev', {'state': {'text': 'Hello'}, 'questions': QUESTIONS, 'dry_run': True})
            self.assertFalse(result.is_error, result.content)
            self.assertEqual(result.structured_content['model'], 'jev-latest')
            self.assertEqual(result.structured_content['state'], {'text': 'Hello'})
            self.assertNotIn('answers', result.structured_content)

    async def test_dotenv_call_returns_typed_cli_result(self):
        async with self.client(key='file-test-key') as client:
            result = await client.call_tool('askjev', {'state': 'Hello', 'questions': QUESTIONS, 'model': 'jev-latest'})
            self.assertFalse(result.is_error, result.content)
            self.assertEqual(result.structured_content['answers']['greeting'], {'type': 'noul', 'noul': 0.97})
            self.assertEqual(result.structured_content['usage']['input_tokens'], 12)

    async def test_environment_key_overrides_file(self):
        async with self.client(key='wrong-file-key', environment_key='environment-test-key') as client:
            result = await client.call_tool('askjev', {'state': 'Hello', 'questions': QUESTIONS})
            self.assertFalse(result.is_error, result.content)
            self.assertEqual(result.structured_content['answers']['greeting']['noul'], 0.97)

    async def test_missing_credentials_are_a_tool_error(self):
        async with self.client(fake=False) as client:
            result = await client.call_tool('askjev', {'state': 'Hello', 'questions': QUESTIONS})
            self.assertTrue(result.is_error)
            self.assertIn('TYPESAFE_API_KEY', str(result.content))

    async def test_invalid_questions_are_a_tool_error(self):
        async with self.client(fake=False) as client:
            result = await client.call_tool('askjev', {'state': 'Hello', 'questions': {}, 'dry_run': True})
            self.assertTrue(result.is_error)
            self.assertIn('questions', str(result.content))

    async def test_api_errors_are_redacted_tool_errors(self):
        async with self.client(key='file-test-key') as client:
            result = await client.call_tool('askjev', {'state': 'api-error', 'questions': QUESTIONS})
            self.assertTrue(result.is_error)
            self.assertIn('401', str(result.content))
            self.assertNotIn('file-test-key', str(result))


if __name__ == '__main__':
    unittest.main()
