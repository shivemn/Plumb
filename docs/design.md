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
   (`core/src/plumb/model.py`). The web API (`core/src/plumb/server`)
   keeps jobs and their facts in one table: SQLite for now, written in
   SQL PostgreSQL also accepts.
6. **Prompt planner.** Summarises bottom-up: file, module, system. The
   model sees facts, not the raw repo.
7. **AI runner.** The server writes a few reports a day with a free model
   (`PLUMB_MODEL`, `PLUMB_DAILY_REPORTS`). Past that cap, or with no model
   set, the reader's browser fetches the prompts (`/api/jobs/{id}/tasks`),
   calls OpenRouter or Anthropic with the reader's own key, and posts back
   only the answers (`/verify`). The local tool runs the same prompts with
   a key from the environment.
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
| website | Pages, content and how the site is built |
| docs    | How content is organised and how to add to it |
| small   | A short summary, no diagram |

All kinds then show the code map, hot spots, how to contribute and what
was not determined. "How to contribute" is built from Makefile targets,
the commands CI runs and the contribution guide's headings.

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

- Python, Java, JavaScript and TypeScript imports are read, including the
  script parts of Astro, Vue and Svelte files.
- Python imports made through `importlib` or plugin lookups are not seen.
- Java references come from imports and from type names used in the same
  package. Fully qualified names written inline are not read yet.
- Spring placeholders are filled from the default settings files only;
  profile files (application-prod.yml) are not used.
- Express prefixes are followed through `.use()` calls and default
  exports; routers passed around in other ways are not.
- Plugins loaded by name are not seen. Migrations are found as folders, not
  through imports.
- All fifteen evaluation repos have now been used to fix detectors, so their
  scores are optimistic until the next held-out round.
- Request tracing follows calls the imports or declared types explain:
  imported functions and classes, typed parameters, objects built in the
  function, Spring fields and constructor parameters, and interfaces with
  one implementation. Calls through dependency-injection containers,
  dynamic dispatch or inherited Python methods are not followed. Spring
  controllers that implement generated OpenAPI interfaces are not traced.
- A library's public API is what its package entry point exports. Names
  added at run time and Java classes in packages named internal, impl or
  examples are left out.
- Review speed counts only the 30 most recently closed pull requests, and
  first review only for the ten newest merged ones, to stay within
  GitHub's limit for requests without a token.
- History needs a full clone. A shallow clone skips hot spots rather than
  reporting wrong counts.

## The verifier

`plumb.verify` keeps a claim only if it cites at least one fact given to
its section, and every file path, route, `code name`, number and known
technology name it mentions appears in a cited fact. Dropped claims are
kept in the report with the reason, so readers can check the checker.

It cannot catch a claim that misreads a fact using only the fact's own
words (calling a monitoring tool a database, say). That needs the answer
keys and a person's judgement, which is why claim precision is measured
by hand.

## Prompts

- The model sees facts, never repo files.
- Facts sit between markers that contain a random code, and each fact is
  forced onto one line with marker-like text broken up, so text from a repo
  cannot fake the end of the facts or add a fact of its own.
- The cache key leaves out the random code, so the same facts are never
  paid for twice. Only answers that could be read are cached.

## Security

- Repo code is never executed.
- Clone size, file count and time are capped.
- The site's content security policy lists the only hosts a page may
  contact (Plumb's API, OpenRouter, Anthropic, Google Fonts) and loads no
  third-party scripts. Styles are set through the style object, never as
  markup, so no inline style is allowed either.
- A reader's model key goes from their browser to the provider only. It is
  kept in memory, or in that browser's local storage if they tick
  "Remember this key". The server never sees it.
- Each visitor may queue `PLUMB_JOBS_PER_HOUR` repos an hour, counted by a
  salted hash of their address; the queue as a whole holds
  `PLUMB_MAX_WAITING` jobs. Each job has a time limit (`PLUMB_JOB_SECONDS`),
  and its clone is deleted when it finishes.
- An internal error is reported to the visitor as "internal error", without
  its message, which could name paths on the server.
- The container runs as a non-root user, with its data in `/data`.
- The web API accepts only GitHub repos. The worker always clones from a
  `https://github.com/` URL, so a request cannot name a folder on the
  server. Commits must be hex SHAs.
- `GITHUB_TOKEN`, when set, is only sent to api.github.com.
