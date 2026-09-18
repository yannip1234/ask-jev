# Astra Jev Review + AskJev

Two skills for using the AskJev CLI continuously while Astra works:

- **[astra-jev-review](skills/astra-jev-review/SKILL.md)** checks interpretations, plans, choices, edits, analysis, tool results, and completion claims as they arise. It is automatically discoverable and explicitly enables implicit invocation.
- **[askjev](skills/askjev/SKILL.md)** sends typed Noul, Choice, and Score questions to TypeSafe through a bundled Python/curl CLI.

The workflow checks meaningful units of work throughout a task. Astra supplies evidence, inspects Jev's actual judgments, investigates concerns, and continues working. It batches related checks and avoids repeatedly asking for approval on unchanged evidence.

## Install

Requires Git, Python 3, curl, and a TypeSafe API key. The CLI needs no Python packages or SDK.

Clone this repository and copy both skills into your Codex skills directory. These commands stop if either skill already exists so an existing installation can be inspected before updating it:

```sh
git clone https://github.com/yannip1234/astra-jev-review.git
cd astra-jev-review
python3 - <<'PYINSTALL'
import os
from pathlib import Path
import shutil

destination = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'skills'
names = ('askjev', 'astra-jev-review')
existing = [str(destination / name) for name in names if (destination / name).exists()]
if existing:
    raise SystemExit('Inspect existing skill directories before updating: ' + ', '.join(existing))
destination.mkdir(parents=True, exist_ok=True)
for name in names:
    shutil.copytree(Path('skills') / name, destination / name)
print('Installed both skills in', destination)
PYINSTALL
```

Configure `TYPESAFE_API_KEY` in the environment used by the agent, or put this in a local `.env` file in the directory where you run AskJev:

```dotenv
TYPESAFE_API_KEY='your-key-here'
```

A nonempty environment variable wins over the file. To use a shared key file from any task directory, pass `--env-file /absolute/path/to/.env`. The CLI reads only `TYPESAFE_API_KEY`, without sourcing shell code or expanding variables. It supports single-line unquoted or quoted values, optional `export`, and comments. It does not search parent directories. Dry runs do not read key files.

Keep real key files out of Git and chat; this repository ignores `.env` and `.env.*`. AskJev reads the installed `typesafe-ai` skill or its public upstream instructions, then checks current TypeSafe documentation; a third skill does not need to be copied into this repository.

## Use

```text
Use $astra-jev-review throughout this task. Use the AskJev CLI to check your
interpretations, plans, choices, changes, and results as you work.
```

The skill's description makes it eligible for automatic selection throughout work. Explicit invocation ensures the instructions are loaded for a task; this is a skill, not a host-level hook that intercepts every tool call. Select Astra in the host to run the workflow with Astra; the skill does not change the running model.

AskJev can also be used by itself:

```text
Use $askjev to judge whether this claim is supported by these source excerpts.
```

Test request construction from this checkout without credentials or network access:

```sh
python3 skills/askjev/scripts/askjev \
  --state 'The test observed that an empty list returns zero.' \
  --question 'Does the supplied observation establish that empty input returns zero?' \
  --dry-run
```

To use a specific dotenv file:

```sh
python3 skills/askjev/scripts/askjev --env-file /absolute/path/to/.env \
  --state 'Hello' --question 'Is this a greeting?'
```

Remove `--dry-run` from the earlier example to call TypeSafe. Requests send the selected state and questions to `https://api.typesafe.ai/v1/systemone` and may incur API usage charges. The CLI can be run by its installed absolute path; putting it on PATH is optional.

A missing key or API failure is reported accurately while useful local work continues. Jev supplements evidence and verification. It does not authorize actions or replace executable tests. Keep requests and responses from your own work outside the public repository.

See the [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart), [HTTP API](https://docs.typesafe.ai/api), and [upstream TypeSafe skill](https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md).
