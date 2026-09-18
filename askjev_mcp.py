#!/usr/bin/env python3
"""Expose the bundled AskJev CLI through MCP over stdio."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

CLI = Path(__file__).resolve().parent / 'skills' / 'askjev' / 'scripts' / 'askjev'


def create_server(env_file: str | None = None) -> MCPServer:
    server = MCPServer('AskJev', instructions=(
        'Ask Jev for typed judgments on supplied evidence. Batch independent '
        'questions. Noul returns probability of yes; Choice and Score include '
        'confidence. Results are judgments, not proof or authorization. '
        'Only send relevant context permitted to be shared with TypeSafe.'
    ), log_level='WARNING')

    @server.tool()
    def askjev(
        state: str | dict[str, Any] | list[Any],
        questions: dict[str, dict[str, Any]],
        model: str = 'jev-latest',
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run AskJev and return its full JSON response, including answers and usage.

        Each questions entry needs type (noul, choice, or score) and complete
        instructions. Choice needs a criteria object mapping options to descriptions;
        Score needs a criteria list of at least two ordered level descriptions.
        State contains the evidence itself, not local file paths to read.
        Credentials are configured by the operator, never passed as tool arguments.
        dry_run returns only the prepared request without credentials or an API call;
        it does not contain judgments. Live calls send state to TypeSafe and use API quota.
        """
        try:
            body = json.dumps({'state': state, 'questions': questions, 'model': model},
                              ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError):
            raise ToolError('Request must contain valid JSON values.') from None
        command = [sys.executable, str(CLI), '--request', '-']
        if env_file is not None:
            command += ['--env-file', env_file]
        if dry_run:
            command.append('--dry-run')
        try:
            result = subprocess.run(command, input=body, text=True, encoding='utf-8',
                                    capture_output=True, timeout=130)
        except subprocess.TimeoutExpired:
            raise ToolError('AskJev timed out; the API outcome is unknown. Do not blindly retry.') from None
        except OSError:
            raise ToolError('Could not start the bundled AskJev CLI.') from None
        if result.returncode:
            # The CLI redacts credentials in upstream errors; do not forward stdout.
            raise ToolError(result.stderr.strip() or 'AskJev failed without an error message.')
        try:
            response = json.loads(result.stdout)
            if not isinstance(response, dict):
                raise ValueError('Expected object')
        except ValueError:
            raise ToolError('AskJev returned an invalid JSON response.') from None
        return response

    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', help='Optional dotenv file; a nonempty environment key wins')
    options = parser.parse_args()
    create_server(options.env_file).run(transport='stdio')
