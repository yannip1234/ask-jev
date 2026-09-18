# AskJev MCP server in Docker

The container exposes one tool, `askjev`, over **stdio**. Your MCP client starts
`docker run`, writes protocol messages to stdin, and reads stdout. Use `-i`,
without `-t` or `-d`. There is no listening port or HTTP endpoint.

The server runs the existing AskJev CLI for each call. The standalone CLI stays
dependency-free; the MCP wrapper uses the official Python MCP SDK, pinned in
`requirements-mcp.txt`. The image runs as a non-root user. Its build context
allowlist excludes `.env`, Git history, and all unrelated files.

## Build

Run from the repository root with Docker running:

```sh
docker build -t askjev-mcp:local .
```

## Supply credentials

If `TYPESAFE_API_KEY` is exported in the environment launching Docker:

```sh
docker run --rm -i -e TYPESAFE_API_KEY askjev-mcp:local
```

To use an existing dotenv file, including the quoted values supported by AskJev,
mount it read-only at `/app/.env`. Run as your local user so owner-only file
permissions work on Linux and macOS:

```sh
docker run --rm -i --user "$(id -u):$(id -g)" \
  --mount type=bind,src=/absolute/path/to/.env,dst=/app/.env,readonly \
  askjev-mcp:local
```

The file must already exist. This invokes AskJev's dotenv reader, with no shell
sourcing or expansion. To combine both sources, add `-e TYPESAFE_API_KEY` to the
mount command; a nonempty environment variable wins. To mount at another path,
append `--env-file /container/path/to/.env` **after the image name**.

Docker also has its own `--env-file` option before the image name, but its parser
is different: use unquoted `TYPESAFE_API_KEY=value` with that option. The bind
mount above preserves AskJev's quoted-value handling.

Starting the process alone waits silently for MCP messages. A key is needed only
for live tool calls; discovery and `dry_run` work without one. Keys are supplied
at runtime, never built into the image or passed in tool arguments.

## Connect an MCP client

For clients accepting an `mcpServers` JSON configuration, use this entry. Replace
`YOUR_UID:YOUR_GID` with the output of `id -u` and `id -g` joined by a colon, and
replace the dotenv path. Shell substitutions do not run inside this JSON:

```json
{
  "mcpServers": {
    "askjev": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--user", "YOUR_UID:YOUR_GID",
        "--mount", "type=bind,src=/absolute/path/to/.env,dst=/app/.env,readonly",
        "askjev-mcp:local"
      ]
    }
  }
}
```

Use the absolute path to Docker if your desktop client cannot find it on PATH.
For an environment-based configuration, replace the `--user` and `--mount`
arguments with `"-e", "TYPESAFE_API_KEY"` and make that variable available to the
MCP client's process.

## Call the tool

`askjev` accepts:

| Argument | Meaning |
| --- | --- |
| `state` | Evidence as text, a JSON object, or an array |
| `questions` | Nonempty map of named questions using the AskJev/TypeSafe schema |
| `model` | Optional model identifier; defaults to `jev-latest` |
| `dry_run` | Optional boolean, default false; prepare a request without an API call |

Example arguments:

```json
{
  "state": {"message": "Hello!"},
  "questions": {
    "greeting": {
      "type": "noul",
      "instructions": "Does message contain a greeting?"
    }
  }
}
```

Supply complete instructions in every question. Choice requires a `criteria`
object of options and descriptions. Score requires an ordered `criteria` array
with at least two levels. See [AskJev](../skills/askjev/SKILL.md) for question
design and probability semantics.

Live calls return the CLI's full JSON response as structured MCP content,
including typed answers and usage. Dry runs return the prepared request, **not
judgments**. Failures return MCP tool errors. Calls are not automatically retried;
a timeout may have an unknown API outcome. Allow at least 140 seconds in the
client's tool timeout to accommodate the CLI's API timeout and process startup.

Only supplied state and questions are sent to TypeSafe; a file path in `state`
is not a command to read that file. Do not include credentials in the state.

## Verify

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-mcp.txt
.venv/bin/python -m unittest discover -s tests -v
ASKJEV_TEST_IMAGE=askjev-mcp:local \
  .venv/bin/python -m unittest discover -s tests -p test_mcp.py -v
```

The MCP contract tests launch the real stdio server and bundled CLI, substituting
only curl's external API response. Container tests disable networking. They
exercise discovery, dry runs, dotenv credentials, environment precedence, request
validation, and redacted upstream errors without real keys or API charges.

Protocol implementation reference: [official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/).
