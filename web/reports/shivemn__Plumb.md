# shivemn/Plumb

Commit cc9ebcb. Kind: service. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
16 of 17 claims kept after checking them against the code.

## In short

- This is a Python service built around a FastAPI server exposing four routes under /api for health checks and job management, backed by SQLite, with a Typer-based CLI offering eight commands including serve, worker, and analysis tools. ([f1](#f1), [f11](#f11), [f13](#f13), [f14](#f14), [f15](#f15), [f16](#f16), [f17](#f17), [f18](#f18), [f19](#f19), [f20](#f20), [f21](#f21), [f22](#f22), [f23](#f23), [f24](#f24), [f25](#f25), [f26](#f26))
- It is run via the plumb CLI commands such as serve to start the API server or worker to process jobs, while continuous integration and deployment are handled through three GitHub Actions workflows and a pyproject.toml build configuration. ([f7](#f7), [f8](#f8), [f9](#f9), [f10](#f10), [f19](#f19), [f23](#f23), [f24](#f24))

## System design

- The service stores data locally in SQLite and authenticates to GitHub using a GITHUB_TOKEN read from the environment at runtime. ([f11](#f11), [f12](#f12))

## How a request moves

- Requests enter through route handlers in core/src/plumb/server/app.py (e.g., add_job for POST /api/jobs), which then delegate to core/src/plumb/source.py for parsing and to a _view function for further processing. ([f31](#f31), [f32](#f32))

## Ways in

- The service exposes a FastAPI HTTP interface with four routes defined in core/src/plumb/server/app.py, while the main CLI entry point plumb is declared in core/pyproject.toml and dispatches eight Typer commands implemented in core/src/plumb/cli.py. ([f13](#f13), [f14](#f14), [f15](#f15), [f16](#f16), [f17](#f17), [f19](#f19), [f20](#f20), [f21](#f21), [f22](#f22), [f23](#f23), [f24](#f24), [f25](#f25), [f26](#f26))
- Separately, the eval directory contains three standalone script entry points (judge.py, provider_cors.py, run.py) that run independently of the core service and CLI. ([f27](#f27), [f28](#f28), [f29](#f29), [f30](#f30))

## Code map

- The core package (core/src/plumb) sits at the center with bidirectional dependencies to its server and writer submodules, while the separate eval module depends on core. ([f41](#f41), [f42](#f42), [f43](#f43), [f44](#f44), [f45](#f45), [f48](#f48), [f49](#f49))
- Tests in core/tests rely heavily on core (78 references) and writer (7 references), and share a common conftest.py used by 20 test files. ([f46](#f46), [f47](#f47), [f53](#f53))
- Within core, inventory.py (35 dependents), entrypoints.py (20), model.py (20), and imports.py (10) are the most reused files, making them key entry points for understanding the codebase. ([f50](#f50), [f51](#f51), [f52](#f52), [f54](#f54))

## Hot spots

- Recent development centers on the core pipeline modules — facts.py, cli.py, entrypoints.py, model.py, and pipeline.py — which together account for most commits and frequently change in tandem. ([f55](#f55), [f56](#f56), [f57](#f57), [f58](#f58), [f61](#f61), [f63](#f63), [f67](#f67), [f69](#f69), [f71](#f71), [f73](#f73))
- The tightest change coupling appears between entrypoints.py and its test file (9 co-changes), cli.py with facts.py (9), and system.py with its test file (6), indicating feature work and test updates happen together. ([f66](#f66), [f67](#f67), [f70](#f70))

## How to contribute

- Set up the project by running uv sync --locked to install locked dependencies as the CI does. ([f33](#f33))
- Run linting and format checks across both the core and eval directories with uv run ruff check . ../eval and uv run ruff format --check . ../eval. ([f34](#f34), [f35](#f35))
- Type-check the codebase with uv run pyright and run the test suite with uv run pytest. ([f36](#f36), [f37](#f37))
- Validate the generated schema matches the Python models by running uv run plumb schema and confirming no uncommitted changes with git diff --exit-code ../schema. ([f38](#f38), [f39](#f39))
- Execute the evaluation suite with uv run python ../eval/run.py as the eval workflow does. ([f40](#f40))

## Sources

- <a id="f1"></a>**f1**: Looks like a service repo: 4 route(s), consumer(s) or scheduled job(s). `core/src/plumb/server/app.py` line 67; `core/src/plumb/server/app.py` line 71; `core/src/plumb/server/app.py` line 86
- <a id="f7"></a>**f7**: GitHub Actions workflow .github/workflows/ci.yml. `.github/workflows/ci.yml`
- <a id="f8"></a>**f8**: GitHub Actions workflow .github/workflows/eval.yml. `.github/workflows/eval.yml`
- <a id="f9"></a>**f9**: GitHub Actions workflow .github/workflows/pages.yml. `.github/workflows/pages.yml`
- <a id="f10"></a>**f10**: Build or deploy file core/pyproject.toml. `core/pyproject.toml`
- <a id="f11"></a>**f11**: Database, cache or queue: SQLite (imports sqlite3). `core/src/plumb/server/jobs.py` line 14; `core/src/plumb/writer/models.py` line 23
- <a id="f12"></a>**f12**: Setting GITHUB_TOKEN is read from the environment in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 104
- <a id="f13"></a>**f13**: 4 http routes found. `core/src/plumb/server/app.py` line 67; `core/src/plumb/server/app.py` line 71; `core/src/plumb/server/app.py` line 86
- <a id="f14"></a>**f14**: HTTP route GET /api/health (fastapi) in core/src/plumb/server/app.py. `core/src/plumb/server/app.py` line 67
- <a id="f15"></a>**f15**: HTTP route POST /api/jobs (fastapi) in core/src/plumb/server/app.py. `core/src/plumb/server/app.py` line 71
- <a id="f16"></a>**f16**: HTTP route GET /api/jobs/{job_id} (fastapi) in core/src/plumb/server/app.py. `core/src/plumb/server/app.py` line 86
- <a id="f17"></a>**f17**: HTTP route GET /api/jobs/{job_id}/facts (fastapi) in core/src/plumb/server/app.py. `core/src/plumb/server/app.py` line 93
- <a id="f18"></a>**f18**: 8 commands found. `core/pyproject.toml` line 23; `core/src/plumb/cli.py` line 41; `core/src/plumb/cli.py` line 59
- <a id="f19"></a>**f19**: Command plumb (plumb.cli:app) (package) in core/pyproject.toml. `core/pyproject.toml` line 23
- <a id="f20"></a>**f20**: Command schema (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 41
- <a id="f21"></a>**f21**: Command analyse (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 59
- <a id="f22"></a>**f22**: Command report (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 137
- <a id="f23"></a>**f23**: Command serve (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 221
- <a id="f24"></a>**f24**: Command worker (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 238
- <a id="f25"></a>**f25**: Command build (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 274
- <a id="f26"></a>**f26**: Command index (typer) in core/src/plumb/cli.py. `core/src/plumb/cli.py` line 333
- <a id="f27"></a>**f27**: 3 program entrys found. `eval/judge.py` line 211; `eval/provider_cors.py` line 103; `eval/run.py` line 160
- <a id="f28"></a>**f28**: Program entry run as a script in eval/judge.py. `eval/judge.py` line 211
- <a id="f29"></a>**f29**: Program entry run as a script in eval/provider_cors.py. `eval/provider_cors.py` line 103
- <a id="f30"></a>**f30**: Program entry run as a script in eval/run.py. `eval/run.py` line 160
- <a id="f31"></a>**f31**: POST /api/jobs is handled by add_job in core/src/plumb/server/app.py; add_job calls parse_github in core/src/plumb/source.py and _view. `core/src/plumb/server/app.py` line 71; `core/src/plumb/source.py` line 45; `core/src/plumb/server/app.py` line 50
- <a id="f32"></a>**f32**: GET /api/jobs/{job_id} is handled by get_job in core/src/plumb/server/app.py; get_job calls _view. `core/src/plumb/server/app.py` line 86; `core/src/plumb/server/app.py` line 50
- <a id="f33"></a>**f33**: A CI step in job core of .github/workflows/ci.yml runs: uv sync --locked. `.github/workflows/ci.yml` line 17
- <a id="f34"></a>**f34**: A CI step in job core of .github/workflows/ci.yml runs: uv run ruff check . ../eval. `.github/workflows/ci.yml` line 18
- <a id="f35"></a>**f35**: A CI step in job core of .github/workflows/ci.yml runs: uv run ruff format --check . ../eval. `.github/workflows/ci.yml` line 19
- <a id="f36"></a>**f36**: A CI step in job core of .github/workflows/ci.yml runs: uv run pyright. `.github/workflows/ci.yml` line 20
- <a id="f37"></a>**f37**: A CI step in job core of .github/workflows/ci.yml runs: uv run pytest. `.github/workflows/ci.yml` line 21
- <a id="f38"></a>**f38**: CI step "Schema matches the Python models" in job core of .github/workflows/ci.yml runs: uv run plumb schema. `.github/workflows/ci.yml` line 24
- <a id="f39"></a>**f39**: CI step "Schema matches the Python models" in job core of .github/workflows/ci.yml runs: git diff --exit-code ../schema. `.github/workflows/ci.yml` line 25
- <a id="f40"></a>**f40**: A CI step in job eval of .github/workflows/eval.yml runs: uv run python ../eval/run.py. `.github/workflows/eval.yml` line 24
- <a id="f41"></a>**f41**: Code in core/src/plumb uses code in core/src/plumb/writer (6 references). `core/src/plumb/cli.py` line 19; `core/src/plumb/cli.py` line 20; `core/src/plumb/site.py` line 22
- <a id="f42"></a>**f42**: Code in eval uses code in core/src/plumb (6 references). `eval/judge.py` line 37; `eval/run.py` line 29; `eval/run.py` line 30
- <a id="f43"></a>**f43**: Code in core/src/plumb/server uses code in core/src/plumb (5 references). `core/src/plumb/server/app.py` line 26; `core/src/plumb/server/app.py` line 28; `core/src/plumb/server/worker.py` line 10
- <a id="f44"></a>**f44**: Code in core/src/plumb uses code in core/src/plumb/server (3 references). `core/src/plumb/cli.py` line 231; `core/src/plumb/cli.py` line 251; `core/src/plumb/cli.py` line 252
- <a id="f45"></a>**f45**: Code in core/src/plumb/writer uses code in core/src/plumb (1 reference). `core/src/plumb/writer/plan.py` line 14
- <a id="f46"></a>**f46**: Code in core/tests uses code in core/src/plumb (78 references). `core/tests/test_activity.py` line 7; `core/tests/test_activity.py` line 16; `core/tests/test_activity.py` line 17
- <a id="f47"></a>**f47**: Code in core/tests uses code in core/src/plumb/writer (7 references). `core/tests/test_site.py` line 11; `core/tests/test_verify.py` line 5; `core/tests/test_verify.py` line 6
- <a id="f48"></a>**f48**: core/src/plumb and core/src/plumb/server each use the other. `core/src/plumb/cli.py` line 231; `core/src/plumb/server/app.py` line 26
- <a id="f49"></a>**f49**: core/src/plumb and core/src/plumb/writer each use the other. `core/src/plumb/cli.py` line 19; `core/src/plumb/writer/plan.py` line 14
- <a id="f50"></a>**f50**: core/src/plumb/inventory.py is used by 35 other files. `core/src/plumb/inventory.py`; `core/src/plumb/contrib.py` line 18; `core/src/plumb/deps.py` line 17
- <a id="f51"></a>**f51**: core/src/plumb/entrypoints.py is used by 20 other files. `core/src/plumb/entrypoints.py`; `core/src/plumb/django.py` line 19; `core/src/plumb/expressmounts.py` line 18
- <a id="f52"></a>**f52**: core/src/plumb/model.py is used by 20 other files. `core/src/plumb/model.py`; `core/src/plumb/cli.py` line 15; `core/src/plumb/facts.py` line 19
- <a id="f53"></a>**f53**: core/tests/conftest.py is used by 20 other files. `core/tests/conftest.py`; `core/tests/test_contrib.py` line 6; `core/tests/test_deps.py` line 13
- <a id="f54"></a>**f54**: core/src/plumb/imports.py is used by 10 other files. `core/src/plumb/imports.py`; `core/src/plumb/django.py` line 28; `core/src/plumb/facts.py` line 16
- <a id="f55"></a>**f55**: 70 commits between 22 Aug 2026 and 20 Nov 2026. commit cc9ebcb; commit 391a3d8; commit 88506d8
- <a id="f56"></a>**f56**: core/src/plumb/facts.py changed in 18 commits by 1 author between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/facts.py`; commit 69a5fea; commit c75b94b; commit b5c3e99
- <a id="f57"></a>**f57**: core/src/plumb/cli.py changed in 15 commits by 1 author between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/cli.py`; commit 775d929; commit 2f5477d; commit 970ae3b
- <a id="f58"></a>**f58**: core/src/plumb/entrypoints.py changed in 12 commits by 1 author between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/entrypoints.py`; commit 88aaddc; commit 0ca099a; commit 7bead85
- <a id="f61"></a>**f61**: core/src/plumb/model.py changed in 8 commits by 1 author between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/model.py`; commit ee58de9; commit 5ef9fd4; commit 376e4b2
- <a id="f63"></a>**f63**: core/src/plumb/pipeline.py changed in 6 commits by 1 author between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/pipeline.py`; commit 5ef9fd4; commit 6eab98a; commit 376e4b2
- <a id="f66"></a>**f66**: core/src/plumb/entrypoints.py and core/tests/test_entrypoints.py changed in the same commit 9 times between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/entrypoints.py`; `core/tests/test_entrypoints.py`
- <a id="f67"></a>**f67**: core/src/plumb/cli.py and core/src/plumb/facts.py changed in the same commit 9 times between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/cli.py`; `core/src/plumb/facts.py`
- <a id="f69"></a>**f69**: core/src/plumb/facts.py and core/src/plumb/pipeline.py changed in the same commit 6 times between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/facts.py`; `core/src/plumb/pipeline.py`
- <a id="f70"></a>**f70**: core/src/plumb/system.py and core/tests/test_system.py changed in the same commit 6 times between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/system.py`; `core/tests/test_system.py`
- <a id="f71"></a>**f71**: core/src/plumb/facts.py and core/src/plumb/model.py changed in the same commit 6 times between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/facts.py`; `core/src/plumb/model.py`
- <a id="f73"></a>**f73**: core/src/plumb/model.py and core/src/plumb/pipeline.py changed in the same commit 5 times between 22 Aug 2026 and 20 Nov 2026. `core/src/plumb/model.py`; `core/src/plumb/pipeline.py`

## Removed

These were written by the model and failed a check.

- "The codebase centers on a core package where server/app.py defines the HTTP endpoints and cli.py registers all commands, alongside a small set of JavaScript, CSS, and HTML assets and three evaluation scripts run as standalone entry points." (overview): names something its facts do not: cli.py
