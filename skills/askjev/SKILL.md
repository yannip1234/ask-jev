---
name: askjev
description: Ask Jev for typed judgments through a direct curl call to the TypeSafe API. Use when the user invokes /AskJev, $askjev, or asks to consult Jev about supplied context, choices, or ratings.
---

# AskJev

Use the installed `typesafe-ai` skill to design the questions. If it is not
installed, read its [upstream SKILL.md](https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md).
Read it before the first request in a task, and follow its live-docs workflow. Start with the [quickstart](https://docs.typesafe.ai/introduction/quickstart)
and [HTTP API](https://docs.typesafe.ai/api). Fetch Markdown with curl if browsing
cannot read it. Reuse documentation already read in the current task.

Actually consult Jev when invoked; do not merely write an example request.
The bundled CLI uses curl directly, without an SDK. It needs Python 3, curl,
and `TYPESAFE_API_KEY` in the environment or a local dotenv file. If the key is
missing, prepare the request and tell the user to configure it locally; do not ask them to
paste a secret into chat or claim an API result.

## Configure the API key

A nonempty `TYPESAFE_API_KEY` environment variable takes precedence. Otherwise,
the CLI reads `.env` in its current working directory, or the file selected by
`--env-file /absolute/path/to/.env`. It does not search parent directories or the
skill directory. Use `--env-file` for a shared key file when working across tasks.

```dotenv
TYPESAFE_API_KEY='your-key-here'
```

Only `TYPESAFE_API_KEY` is read; other entries are ignored. Values may be unquoted,
single-quoted, or double-quoted on one line, with optional `export` and comments.
Values are literal: no variable expansion, escape processing, shell commands, or
multiline values. For duplicate key entries the last one wins. A missing default
`.env` is ignored; an explicitly selected missing file is an error when needed.
Keep real key files out of version control. Never print their contents.
`--dry-run` neither reads dotenv files nor requires a key.

## Prepare the judgment

Use the user's relevant context as `state`, and phrase complete questions in
`instructions`. Jev returns typed judgments, not generated prose or explanations.
For an open-ended question, formulate useful bounded judgments or candidate
answers from the supplied evidence; ask for clarification if doing that would
materially change the user's question. Do not invent missing evidence.

- Noul: a yes/no condition; its number is the probability of yes.
- Choice: one of the supplied options; include a no-match option when appropriate.
- Score: degree on an ordered rubric with at least two concrete levels.

Batch independent questions over the same state in one request. Dependent questions
need a subsequent call with the necessary results or new evidence. Send only the
context relevant to the user's request, never credentials or unrelated files.

## Run the CLI

Resolve this skill directory from the skill catalog or this file's location.
Run `python3 scripts/askjev` from that directory, or pass the script's resolved
absolute path from any working directory. If installed on PATH, `askjev` works too.
The examples below use that optional PATH command.

```bash
askjev --state 'Please help today; checkout is broken.' \
  --question 'Does the message express urgency?'

askjev --state-file ticket.txt --question 'Which team should handle this?' \
  --type choice --criteria '{"billing":"Charges and refunds","technical":"Bugs and outages","other":"Neither team fits"}'

askjev --state-file ticket.txt --question 'How frustrated is the customer?' \
  --type score --criteria '["Calm","Frustrated but civil","Very angry"]'

askjev --request request.json

askjev --env-file /absolute/path/to/.env --request request.json
```

`--state-file -` reads text from stdin; `--state-json` interprets state as JSON.
`--request PATH` (or `-` for stdin) accepts a full JSON request containing `state`
and `questions`; `model` defaults to `jev-latest`. Use a JSON serializer to build
request files from arbitrary user text, rather than interpolating it into shell
commands. `--dry-run` prints the payload without credentials or a network request.
Do not print dry-run content if it contains material the user did not ask to display.

The CLI prints the complete JSON response, retains HTTP error bodies on stderr,
and returns nonzero on failures. For 401, fix authentication; for 422, fix the
payload. For 429 or 529, retry at most twice with increasing delays, respecting
Retry-After if available. Do not blindly repeat a timeout whose outcome is unknown.

## Report the result

Report Jev's actual answer and relevant probabilities, plus confidence for Choice
or Score and the Score rubric. Noul has no separate confidence; 0.5 indicates
uncertainty, not medium intensity. Distinguish your interpretation from Jev's
returned fields and never attribute a generated rationale to Jev. A judgment does
not authorize executing a chosen action. If the API fails, report the failure.
