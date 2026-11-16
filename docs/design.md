# Design

## The rule everything follows

Every sentence in a report links to the file, commit or issue that
supports it. If nothing supports it, it is removed. If the repo does not
answer a question, the report says "not determined".

## Pipeline

1. **Miner.** Clones the repo (size and time limits, code never run),
   reads git history and GitHub issues. Python first, Go later.
2. **Parser and graph.** tree-sitter parses Python and Java; NetworkX
   builds the dependency graph and groups files into components.
3. **Detectors.** Find services (Docker, Compose, Kubernetes, CI),
   databases and queues (drivers, connection settings, migrations),
   outside APIs (HTTP clients, SDKs, environment variable names) and
   entry points (routes, commands, scheduled jobs, consumers).
4. **Repo kind.** Service, library, CLI, data, docs or small. Decides
   which section leads the report. No diagram is drawn when no running
   system is found.
5. **Fact store.** Every finding becomes a `Fact` with evidence
   (`core/src/plumb/model.py`). PostgreSQL on the server, SQLite locally.
6. **Prompt planner.** Summarises bottom-up: file, module, system. The
   model sees facts, not the raw repo.
7. **AI runner.** Runs in the user's browser (or the local tool) with the
   user's own key. The key never reaches Plumb's server.
8. **Verifier.** Every claim must cite fact ids that exist, and named
   files, symbols and issues must exist in the facts. Failures are dropped
   and counted.
9. **Report builder.** Assembles the report JSON the web app renders.

## Report, by repo kind

| Kind    | Leads with |
|---------|------------|
| service | System design diagram, then how a request moves |
| library | What it lets other code do, main modules, how a call flows |
| cli     | Commands and the path from input to output |
| data    | Data sources, the order scripts run in, outputs |
| docs    | How content is organised and how to add to it |
| small   | A short summary, no diagram |

All kinds then show the code map, hot spots, how to contribute and what
was not determined.

## Decisions

| Decision | Why |
|----------|-----|
| Python for the core | Fastest to ship; best parsing, graph and model libraries. |
| Go for the miner, later | Git history is the CPU-heavy stage; a measured rewrite shows the gain. |
| One JSON contract generated from Pydantic | Python, Go and TypeScript validate against one definition. |
| Postgres table as the job queue | One database instead of adding Redis. |
| Keys stay in the browser | Users can bring paid models without trusting Plumb's server. |
| Python and Java first | Depth over breadth; the eval repos have known answers. |
| Repo text is data, never instructions | READMEs and comments can contain text aimed at the model. |

## Known limits of the analysis so far

- Only Python and Java imports are read. Other languages are counted but
  not linked, so a TypeScript front end does not show in the code map yet.
- Python imports made through `importlib` or plugin lookups are not seen.
- Java references come from imports and from type names used in the same
  package. Fully qualified names written inline are not read yet.
- History needs a full clone. A shallow clone skips hot spots rather than
  reporting wrong counts.

## Security

- Repo code is never executed.
- Clone size, file count and time are capped.
- The web app's content security policy lists the only hosts the page may
  contact, and the analyse page loads no third-party scripts.
- API keys are kept in memory for the session, never stored or logged.
