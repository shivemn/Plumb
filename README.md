# Plumb

Plumb explains a GitHub repository: what runs, how the code is laid out,
where it changes most, and how to start contributing. Every claim in a
report links to the file, commit or issue it came from. Anything the
repo does not show is marked "not determined" instead of guessed.

**Status:** early development. Analysis works for Python, Java, JavaScript
and TypeScript repos, and `plumb report` writes a checked report with a
model. There is no website yet. See [docs/roadmap.md](docs/roadmap.md).

## How it works

1. **Mine** the repo: clone it, read its git history and GitHub issues.
2. **Analyse** without AI: parse the code, build the dependency graph,
   detect services, databases and outside APIs, and work out what kind
   of repo it is.
3. **Write** with an AI model, using only the facts from step 2. The
   model runs in your browser with your own API key, which never reaches
   Plumb's server.
4. **Verify** every claim against the facts and drop the ones that fail.

## Layout

| Folder   | What it holds |
|----------|---------------|
| `core`   | Python analysis pipeline, verifier and command-line tool |
| `miner`  | Go version of the repo miner (later phase) |
| `web`    | Astro and React site (later phase) |
| `schema` | JSON Schema shared by the Python, Go and TypeScript parts |
| `eval`   | Test repos and hand-written answer keys |
| `docs`   | Design notes and roadmap |

## Development

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```
cd core
uv sync
uv run pytest
uv run plumb analyse pallets/click        # or a GitHub URL, or a local folder
uv run python ../eval/run.py              # analyse and score the evaluation repos
```

To write a report you need an API key for Anthropic or OpenRouter:

```
export ANTHROPIC_API_KEY=...                          # or OPENROUTER_API_KEY
uv run plumb report pallets/click --dry-run           # see the prompts and their size first
uv run plumb report pallets/click --model anthropic:claude-opus-5-5
```

This writes `click.report.json` and `click.report.md`. The key is read
from the environment and only sent to the provider. If your Anthropic key
is not scoped to one workspace, also set `ANTHROPIC_WORKSPACE_ID`.

`plumb analyse` writes `<repo>.facts.json`: what kind of repo it is, the
services it runs, the databases, queues and outside services it uses, the
settings it reads, its routes, commands and consumers, which parts of the
code use which, hot spots and files that change together. Every fact cites
the files, lines or commits it came from.

## Licence

MIT. See [LICENSE](LICENSE).
