# Roadmap

About 16 weeks at 10 to 12 hours a week.

| Weeks | Work | Done when |
|-------|------|-----------|
| 1 | Skeleton, fact model, CI, eval repos, browser-call checks per AI provider | CI green; answer keys for 3 repos |
| 2–5 | Miner, parser, dependency graph, git history, repo-kind detection | `plumb analyse` prints a fact set for every eval repo |
| 6–7 | System design detectors | Services, stores and outside APIs match the answer keys |
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

## Weeks 4 and 5 (next)

- [ ] Repo-kind detection (service, library, CLI, data, docs, small)
- [ ] TypeScript and JavaScript imports, so front ends show up in the code map
- [ ] Entry points: routes, commands, queue consumers, scheduled jobs
- [ ] Answer keys for the remaining six evaluation repos
