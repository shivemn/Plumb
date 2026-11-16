# Plumb

Plumb explains a GitHub repository: what runs, how the code is laid out,
where it changes most, and how to start contributing. Every claim in a
report links to the file, commit or issue it came from. Anything the
repo does not show is marked "not determined" instead of guessed.

**Status:** early development. Nothing works end to end yet.

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
uv run plumb --version
uv run pytest
```

## Licence

MIT. See [LICENSE](LICENSE).
