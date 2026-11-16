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

## Week 1

- [x] Repo layout, licence, README
- [x] Fact model and generated JSON Schema
- [x] CI: lint, format, type check, tests, schema drift
- [ ] Pin commits for the eval repos in `eval/repos.toml`
- [ ] Write answer keys for 3 repos, starting with your own
- [ ] Check which AI providers accept calls straight from a browser
