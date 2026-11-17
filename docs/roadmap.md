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

## Weeks 7 to 9 (next)

- [ ] Resolve settings placeholders (`${pipeline.topic}`) from config files
- [ ] Router prefixes added in other files (`include_router(..., prefix=...)`)
- [ ] Three held-out repos that Plumb was not developed against, to check
      the scores are not just fitted to the nine
- [ ] Prompt planner, writing layer and verifier
