# Roadmap

About 16 weeks at 10 to 12 hours a week.

| Weeks | Work | Done when |
|-------|------|-----------|
| 1 | Skeleton, fact model, CI, eval repos, browser-call checks per AI provider | CI green; answer keys for 3 repos |
| 2–5 | Miner, parser, dependency graph, git history, repo-kind detection | `plumb analyse` prints a fact set for every eval repo |
| 6–7 | System design detectors | Services, stores and outside APIs match the answer keys (stores done) |
| 8–9 | Prompt planner, writing layer, verifier, scoring | Full report locally, with precision and recall published |
| 10–12 | Website: report page, diagrams, gallery | Live site with pre-analysed repos |
| 13 | Model picker, bring-your-own-key, cost estimate | Anyone can analyse a repo with their own key or a free model |
| 14–15 | Go miner and speed comparison | Identical output to the Python miner; benchmark written up |
| 16 | Hardening, docs, launch | Public release |

## Week 1 (done)

- [x] Repo layout, licence, README
- [x] Fact model and generated JSON Schema
- [x] CI: lint, format, type check, tests, schema drift
- [x] Pin commits for the eval repos in `eval/repos.toml`
- [x] Answer keys for 3 repos: credit-event-pipeline, market-lab, spring-petclinic
- [x] Browser-access check for AI providers (`eval/provider_cors.py`). Anthropic
      confirmed; the others still need running from a normal network.

## Weeks 2 and 3 (done)

- [x] Fetch repos safely: blobless clone, size and time limits, pinned commits
- [x] File inventory: language, category, vendored and generated files skipped
- [x] Git history: hot spots, authors, files that change together
- [x] `plumb analyse` writes a fact set, every fact with evidence
- [x] Python imports with tree-sitter, resolved to repo files
- [x] Java imports and same-package references, resolved to repo files
- [x] Dependency graph grouped into components
- [x] `eval/run.py` runs all evaluation repos and scores module recall

## Weeks 4 to 6 (done)

- [x] TypeScript and JavaScript imports, with tsconfig path aliases
- [x] Entry points: FastAPI and Flask routes, Typer, Click and argparse commands,
      Celery tasks, Spring routes, Kafka, RabbitMQ and JMS consumers, scheduled
      jobs, Java mains, Express and Next.js routes, package.json commands
- [x] Example and docs code kept apart from source
- [x] Dependencies from pyproject, requirements, pom.xml, Gradle and package.json
- [x] Services from Dockerfiles, Compose, render.yaml and Procfiles
- [x] Databases, caches, queues and outside services from dependencies,
      config and code; settings read from the environment
- [x] Repo kind: service, library, CLI, data, website, docs, small
- [x] Answer keys for all nine evaluation repos; kind, routes and stores
      scored automatically (27 of 27 checks pass)

## Weeks 7 to 9 (done)

- [x] Spring settings placeholders (`${pipeline.topic}`) resolved from
      application.yml and application.properties
- [x] Route prefixes joined from routers mounted in other files, including
      aliased imports and prefixes taken from settings classes
- [x] Imports read from Astro, Vue and Svelte files
- [x] Database migration folders (Alembic, Flyway, Django, Prisma, Liquibase, Knex)
- [x] Three held-out repos, keys written before Plumb ran on them. First run:
      5 of 9 checks. After fixing what they exposed: 9 of 9 (see below)
- [x] Report format, fact topics, prompt planner, Anthropic and OpenRouter
      clients, answer cache
- [x] Verifier: drops claims that cite missing facts or name files, routes,
      code, numbers or technologies their facts do not contain
- [x] `plumb report`, with `--dry-run` and Markdown export

### What the held-out repos showed

Their first run failed 4 of 9 checks, and every failure was a real gap:

- FastAPI routes with an empty path (`@router.get("")`) were skipped.
- A prefix from a lower-case settings field (`api_prefix`) and a router
  imported under another name were not followed.
- PostgreSQL behind Prisma was missed: Prisma's schema file was not read.
- httpie's packaging Dockerfile was taken for a service, and its commands
  in setup.cfg were not read.

One answer key was wrong, not Plumb: the Express key missed `GET /` in
`src/main.ts`. After the fixes these three repos have been tuned against
too, so new held-out repos are needed for an honest score.

## 18 November

- [x] Express route prefixes from `app.use("/api", router)`, across files
- [x] Anthropic keys not scoped to a workspace (`ANTHROPIC_WORKSPACE_ID`)
- [x] Setup and test commands from Makefiles, CI workflows and contribution
      guides, and a "How to contribute" section in every report
- [x] Evaluation runs in CI on pull requests and weekly, and fails when a
      check drops

## Weeks 10 to 12 (done)

The website moved to the next block. These weeks went into what the
report says, so the site has more to show when it is built, and into the
server it will call.

- [x] Three new held-out repos (Django RealWorld, Spring PetClinic REST,
      httpx). First run: 3 of 9 checks. After fixing what they exposed:
      9 of 9 (see below)
- [x] Django URL patterns and database settings; routes from OpenAPI files
- [x] Starter issues, and median time to first review and to merge, from
      GitHub (optional `GITHUB_TOKEN`, answers cached for a day)
- [x] Public API of Python, Java and JavaScript/TypeScript libraries, and a
      "What it lets your code do" section for libraries
- [x] Request tracing from route handler to the database for Python and
      Spring, and a "How a request moves" section for services
- [x] `eval/judge.py`: judge kept claims by hand and score claim precision
- [x] Web API with a job queue and a worker (`plumb serve`, `plumb worker`)
- [ ] First real reports with a model and a published claim precision.
      Needs an API key; the judging tool is ready

### What the second held-out round showed

- Django routes live in `urlpatterns`, not decorators, and the database is
  named by `ENGINE` in settings: neither was read.
- PetClinic REST declares its routes in an OpenAPI file and implements
  generated interfaces, so only 1 of 38 routes was found. HSQLDB was not in
  the catalogue.
- httpx was called a CLI because of its `httpx` command, which only works
  with the optional `[cli]` extra.

These three are now tuned against too.

## Weeks 13 to 16 (next)

- [ ] Website: report page, system design and code map diagrams, gallery
- [ ] Bring-your-own-key in the browser: model picker, cost estimate,
      verifier run in the page
- [ ] Go miner and speed comparison
- [ ] Job table on PostgreSQL, rate limits, deploy
- [ ] First published claim precision, and a third held-out round
