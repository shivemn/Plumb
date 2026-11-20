# Plumb

Plumb explains a GitHub repository: what runs, how the code is laid out,
where it changes most, and how to start contributing. Every claim in a
report links to the file, commit or issue it came from. Anything the
repo does not show is marked "not determined" instead of guessed.

**Site:** https://shivemn.github.io/Plumb/ has a gallery of reports.

**Status:** early development. Analysis works for Python, Java, JavaScript
and TypeScript repos, and `plumb report` writes a checked report with a
model, free ones included. The site shows reports written ahead of time;
submitting your own repo there, with your own key, comes next. See
[docs/roadmap.md](docs/roadmap.md).

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
| `web`    | The static site: gallery and report page, published to GitHub Pages |
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

To write a report you need a model. Free ones work:

```
export OPENROUTER_API_KEY=...                         # free account at openrouter.ai
uv run plumb report pallets/click --dry-run           # see the prompts and their size first
uv run plumb report pallets/click --model openrouter:openai/gpt-oss-120b:free
```

| Provider | Model option | Key |
|----------|--------------|-----|
| Anthropic | `anthropic:claude-opus-5-5` (default) | `ANTHROPIC_API_KEY` |
| OpenRouter | `openrouter:<model>`; free ones end in `:free` | `OPENROUTER_API_KEY` |
| Groq | `groq:<model>` (free tier) | `GROQ_API_KEY` |
| Google Gemini | `gemini:<model>` (free tier for Flash) | `GEMINI_API_KEY` |
| OpenAI | `openai:<model>` | `OPENAI_API_KEY` |
| Ollama, on your machine | `ollama:<model>` | none |

This writes `click.report.json` and `click.report.md`. The key is read
from the environment and only sent to the provider. If your Anthropic key
is not scoped to one workspace, also set `ANTHROPIC_WORKSPACE_ID`.

`plumb analyse` writes `<repo>.facts.json`: what kind of repo it is, the
services it runs, the databases, queues and outside services it uses, the
settings it reads, its routes, commands and consumers, how a request moves
from route handler to the database, a library's public API, which parts of
the code use which, hot spots, files that change together, starter issues
and how long pull requests wait for review. Every fact cites the files,
lines, commits or issues it came from. Set `GITHUB_TOKEN` to read issues
and pull requests past GitHub's limit of 60 requests an hour, or pass
`--no-github` to skip them.

To run the web API and a worker on your machine:

```
uv sync --extra server
uv run plumb serve                     # http://127.0.0.1:8000/api/docs
uv run plumb worker                    # in a second terminal
curl -X POST localhost:8000/api/jobs -H 'content-type: application/json' \
     -d '{"repo": "pallets/click"}'
```

The server only produces facts. Reports are written in the browser with
the reader's own key, so no model key ever reaches it.

## Licence

MIT. See [LICENSE](LICENSE).
