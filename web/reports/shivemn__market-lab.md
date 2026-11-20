# shivemn/market-lab

Commit 129b31b. Kind: service. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
52 of 53 claims kept after checking them against the code.

## Overview

- This is a service repository with one deployable service and 30 routes, consumers, or scheduled jobs. ([f1](#f1))
- The codebase consists of 43 Python source files and 52 TypeScript source files, along with 5 CSS files and 1 HTML file. ([f2](#f2), [f3](#f3), [f4](#f4), [f5](#f5))
- Build and deployment are configured via Dockerfile, package.json, pyproject.toml, render.yaml, and web/package.json. ([f9](#f9), [f10](#f10), [f11](#f11), [f12](#f12), [f13](#f13))
- Continuous integration uses a GitHub Actions workflow at .github/workflows/ci.yml. ([f8](#f8))

## System design

- The repository runs a service named market-lab as a Render web service from a Dockerfile. ([f14](#f14))
- The service executes a command that creates a /data directory and starts marketlab serve on host 0.0.0.0 with a configurable port. ([f14](#f14))
- The service reads the PORT setting from the environment. ([f14](#f14), [f18](#f18))
- PostgreSQL is available as a database option through the psycopg dependency. ([f15](#f15))
- SQLite is available as a database option through the sqlite3 import. ([f16](#f16))
- The service serves static web assets from the web/dist directory. ([f14](#f14))
- The service is configured to run behind a proxy. ([f14](#f14))

## How a request moves

- 18 of 30 traced routes pass through src/marketlab/api then src/marketlab. ([f66](#f66))
- POST /api/worlds is handled by start_world in src/marketlab/api/app.py which calls world_json, which calls PracticeWorld.statement, PracticeWorld.positions, PracticeWorld.today and instrument_json in src/marketlab/world.py. ([f67](#f67))
- POST /api/runs is handled by start_run in src/marketlab/api/app.py which calls summary, which calls instrument_json. ([f69](#f69))

## Ways into the code

- The service exposes 30 HTTP routes defined in src/marketlab/api/app.py and src/marketlab/cluster.py. ([f19](#f19), [f20](#f20), [f48](#f48), [f49](#f49))
- Routes are grouped under /api/auth for authentication, /api/runs for run management, /api/sessions for session operations, /api/worlds for world management, and /api/accounts and /api/config for other resources. ([f20](#f20), [f21](#f21), [f22](#f22), [f23](#f23), [f24](#f24), [f25](#f25), [f26](#f26), [f27](#f27), [f28](#f28), [f29](#f29), [f30](#f30), [f31](#f31), [f32](#f32), [f33](#f33), [f34](#f34), [f35](#f35), [f36](#f36), [f37](#f37), [f38](#f38), [f39](#f39), [f40](#f40), [f41](#f41), [f42](#f42), [f43](#f43), [f44](#f44), [f45](#f45), [f46](#f46))
- Two WebSocket routes are available: /ws/runs/{run_id} in app.py and a catch-all /ws/{rest:path} in cluster.py. ([f47](#f47), [f48](#f48))
- A catch-all HTTP route handling GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS on /{path:path} is defined in cluster.py. ([f49](#f49))
- Seven CLI commands are registered via argparse in src/marketlab/cli.py: run, show, serve, cluster, costs, and replay, plus a package-level marketlab command. ([f50](#f50), [f51](#f51), [f52](#f52), [f53](#f53), [f54](#f54), [f55](#f55), [f56](#f56), [f57](#f57))
- Three standalone program entry points exist as scripts: benchmarks/bench_exchange.py, tools/loadtest.py, and tools/serve_for_loadtest.py. ([f58](#f58), [f59](#f59), [f60](#f60), [f61](#f61))
- The web frontend provides three npm package scripts in web/package.json: dev (vite), build (tsc --noEmit && vite build), and test (vitest run). ([f62](#f62), [f63](#f63), [f64](#f64), [f65](#f65))

## Code map

- The repository contains 43 Python source files totalling 7,213 lines, 52 TypeScript source files totalling 5,447 lines, 5 CSS files totalling 680 lines, and 1 HTML file of 17 lines. ([f2](#f2), [f3](#f3), [f4](#f4), [f5](#f5))
- In the web frontend, code in web/src/components depends on web/src/lib with 82 references. ([f79](#f79))
- Code in web/src depends on web/src/components with 9 references and on web/src/lib with 7 references. ([f80](#f80), [f82](#f82))
- In the Python backend, src/marketlab depends on src/marketlab/core with 8 references, on src/marketlab/sim with 5 references, on src/marketlab/ledger with 3 references, and on src/marketlab/api with 1 reference. ([f81](#f81), [f84](#f84), [f85](#f85), [f92](#f92))
- The src/marketlab/api module depends on src/marketlab with 6 references and on src/marketlab/core with 1 reference. ([f83](#f83), [f93](#f93))
- The src/marketlab/ledger module depends on src/marketlab with 3 references and on src/marketlab/core with 2 references. ([f86](#f86), [f88](#f88))
- The src/marketlab/sim module depends on src/marketlab with 3 references and on src/marketlab/core with 2 references. ([f87](#f87), [f89](#f89))
- The tools directory depends on src/marketlab with 2 references, and benchmarks depends on src/marketlab/core with 1 reference. ([f90](#f90), [f91](#f91))
- There are mutual dependencies between src/marketlab and each of src/marketlab/api, src/marketlab/ledger, and src/marketlab/sim. ([f94](#f94), [f95](#f95), [f96](#f96))
- The most depended-upon files are src/marketlab/core/__init__.py used by 42 files, web/src/lib/format.ts used by 25 files, web/src/lib/market.ts used by 24 files, src/marketlab/ledger/__init__.py used by 19 files, and tests/helpers.py used by 17 files. ([f97](#f97), [f98](#f98), [f99](#f99), [f100](#f100), [f101](#f101))

## Hot spots

- The repository had 32 commits between 09 Aug 2026 and 07 Nov 2026. ([f102](#f102))
- web/src/components/PracticeView.tsx changed in 14 commits, the most of any file. ([f103](#f103))
- src/marketlab/api/app.py changed in 13 commits. ([f104](#f104))
- web/src/desk.css changed in 10 commits. ([f105](#f105))
- web/src/App.tsx changed in 9 commits. ([f106](#f106))
- src/marketlab/ledger/ledger.py, tests/unit/test_api_worlds.py, and web/src/components/PriceChart.tsx each changed in 8 commits. ([f107](#f107), [f108](#f108), [f109](#f109))
- src/marketlab/cli.py, src/marketlab/world.py, and web/src/lib/world.ts each changed in 7 commits. ([f110](#f110), [f111](#f111), [f112](#f112))
- web/src/components/PracticeView.tsx and web/src/desk.css changed together in 7 commits. ([f113](#f113))
- src/marketlab/ledger/ledger.py and tests/unit/test_ledger.py changed together in 6 commits. ([f114](#f114))
- src/marketlab/world.py and tests/unit/test_api_worlds.py changed together in 6 commits. ([f115](#f115))
- web/src/components/PracticeView.tsx changed with web/src/lib/world.ts, web/src/components/PriceChart.tsx, web/src/App.tsx, and src/marketlab/api/app.py each in 6 commits. ([f116](#f116), [f117](#f117), [f118](#f118), [f119](#f119))
- src/marketlab/cli.py and src/marketlab/ledger/ledger.py changed together in 5 commits. ([f120](#f120))
- src/marketlab/world.py and web/src/components/PracticeView.tsx changed together in 5 commits. ([f121](#f121))
- src/marketlab/api/app.py and src/marketlab/ledger/ledger.py changed together in 5 commits. ([f122](#f122))

## How to contribute

- Install dependencies with `python -m pip install --upgrade pip` followed by `pip install -e ".[dev,api,postgres]"`. ([f71](#f71), [f72](#f72))
- Run linting with `ruff check .`. ([f73](#f73))
- Run type checking with `mypy`. ([f74](#f74))
- Run tests with `pytest`. ([f75](#f75))
- For the web frontend, run `npm ci` then `npm test` and `npm run build` as CI does. ([f76](#f76), [f77](#f77), [f78](#f78))
- Frontend development uses `npm run dev` (vite) and `npm run build` (tsc --noEmit && vite build). ([f63](#f63), [f64](#f64))
- Frontend tests run via `npm run test` (vitest run). ([f65](#f65))

## Sources

- <a id="f1"></a>**f1**: Looks like a service repo: 1 deployable service(s) and 30 route(s), consumer(s) or scheduled job(s). `Dockerfile` line 2; `src/marketlab/api/app.py` line 535; `src/marketlab/api/app.py` line 547
- <a id="f2"></a>**f2**: 43 source files in python, 7,213 lines in all. `src/marketlab/api/app.py`; `src/marketlab/world.py`; `src/marketlab/ledger/ledger.py`
- <a id="f3"></a>**f3**: 52 source files in typescript, 5,447 lines in all. `web/src/components/PracticeView.tsx`; `web/src/components/PriceChart.tsx`; `web/src/components/AuctionView.tsx`
- <a id="f4"></a>**f4**: 5 source files in css, 680 lines in all. `web/src/desk.css`; `web/src/styles.css`; `web/src/look.css`
- <a id="f5"></a>**f5**: 1 source file in html, 17 lines in all. `web/index.html`
- <a id="f8"></a>**f8**: GitHub Actions workflow .github/workflows/ci.yml. `.github/workflows/ci.yml`
- <a id="f9"></a>**f9**: Build or deploy file Dockerfile. `Dockerfile`
- <a id="f10"></a>**f10**: Build or deploy file package.json. `package.json`
- <a id="f11"></a>**f11**: Build or deploy file pyproject.toml. `pyproject.toml`
- <a id="f12"></a>**f12**: Build or deploy file render.yaml. `render.yaml`
- <a id="f13"></a>**f13**: Build or deploy file web/package.json. `web/package.json`
- <a id="f14"></a>**f14**: Service run from this repo: market-lab (Dockerfile, runs ["sh", "-c", "mkdir -p /data && marketlab serve --host 0.0.0.0 --port ${PORT} --db \"${DATABASE_URL:-/data/practice.db}\" --web web/dist --behind-proxy"]; Render web service). `Dockerfile` line 2; `render.yaml` line 5
- <a id="f15"></a>**f15**: Database, cache or queue: PostgreSQL (dependency psycopg). `pyproject.toml` line 19
- <a id="f16"></a>**f16**: Database, cache or queue: SQLite (imports sqlite3). `src/marketlab/ledger/ledger.py` line 16
- <a id="f18"></a>**f18**: Setting PORT is read from the environment in Dockerfile. `Dockerfile` line 19
- <a id="f19"></a>**f19**: 30 http routes found. `src/marketlab/api/app.py` line 535; `src/marketlab/api/app.py` line 547; `src/marketlab/api/app.py` line 586
- <a id="f20"></a>**f20**: HTTP route GET /api/config (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 535
- <a id="f21"></a>**f21**: HTTP route POST /api/auth/enter (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 547
- <a id="f22"></a>**f22**: HTTP route POST /api/auth/guest (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 586
- <a id="f23"></a>**f23**: HTTP route GET /api/auth/me (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 601
- <a id="f24"></a>**f24**: HTTP route POST /api/auth/logout (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 608
- <a id="f25"></a>**f25**: HTTP route GET /api/health (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 616
- <a id="f26"></a>**f26**: HTTP route POST /api/runs (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 620
- <a id="f27"></a>**f27**: HTTP route GET /api/runs/{run_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 643
- <a id="f28"></a>**f28**: HTTP route GET /api/runs/{run_id}/events (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 647
- <a id="f29"></a>**f29**: HTTP route GET /api/runs/{run_id}/ends (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 655
- <a id="f30"></a>**f30**: HTTP route GET /api/runs/{run_id}/state (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 659
- <a id="f31"></a>**f31**: HTTP route POST /api/sessions (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 663
- <a id="f32"></a>**f32**: HTTP route GET /api/sessions/{session_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 692
- <a id="f33"></a>**f33**: HTTP route GET /api/sessions/{session_id}/market (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 697
- <a id="f34"></a>**f34**: HTTP route GET /api/sessions/{session_id}/statement (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 702
- <a id="f35"></a>**f35**: HTTP route POST /api/sessions/{session_id}/advance (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 707
- <a id="f36"></a>**f36**: HTTP route POST /api/sessions/{session_id}/orders (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 723
- <a id="f37"></a>**f37**: HTTP route DELETE /api/sessions/{session_id}/orders/{order_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 742
- <a id="f38"></a>**f38**: HTTP route DELETE /api/sessions/{session_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 758
- <a id="f39"></a>**f39**: HTTP route POST /api/worlds (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 766
- <a id="f40"></a>**f40**: HTTP route GET /api/accounts/{owner}/days (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 798
- <a id="f41"></a>**f41**: HTTP route GET /api/worlds/{world_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 808
- <a id="f42"></a>**f42**: HTTP route GET /api/worlds/{world_id}/statement (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 813
- <a id="f43"></a>**f43**: HTTP route POST /api/worlds/{world_id}/advance (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 848
- <a id="f44"></a>**f44**: HTTP route POST /api/worlds/{world_id}/orders (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 865
- <a id="f45"></a>**f45**: HTTP route DELETE /api/worlds/{world_id}/orders/{symbol}/{order_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 880
- <a id="f46"></a>**f46**: HTTP route DELETE /api/worlds/{world_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 893
- <a id="f47"></a>**f47**: HTTP route WEBSOCKET /ws/runs/{run_id} (fastapi) in src/marketlab/api/app.py. `src/marketlab/api/app.py` line 903
- <a id="f48"></a>**f48**: HTTP route WEBSOCKET /ws/{rest:path} (fastapi) in src/marketlab/cluster.py. `src/marketlab/cluster.py` line 104
- <a id="f49"></a>**f49**: HTTP route GET,POST,PUT,PATCH,DELETE,HEAD,OPTIONS /{path:path} (fastapi) in src/marketlab/cluster.py. `src/marketlab/cluster.py` line 139
- <a id="f50"></a>**f50**: 7 commands found. `pyproject.toml` line 15; `src/marketlab/cli.py` line 44; `src/marketlab/cli.py` line 52
- <a id="f51"></a>**f51**: Command marketlab (marketlab.cli:main) (package) in pyproject.toml. `pyproject.toml` line 15
- <a id="f52"></a>**f52**: Command run (argparse) in src/marketlab/cli.py. `src/marketlab/cli.py` line 44
- <a id="f53"></a>**f53**: Command show (argparse) in src/marketlab/cli.py. `src/marketlab/cli.py` line 52
- <a id="f54"></a>**f54**: Command serve (argparse) in src/marketlab/cli.py. `src/marketlab/cli.py` line 59
- <a id="f55"></a>**f55**: Command cluster (argparse) in src/marketlab/cli.py. `src/marketlab/cli.py` line 77
- <a id="f56"></a>**f56**: Command costs (argparse) in src/marketlab/cli.py. `src/marketlab/cli.py` line 89
- <a id="f57"></a>**f57**: Command replay (argparse) in src/marketlab/cli.py. `src/marketlab/cli.py` line 97
- <a id="f58"></a>**f58**: 3 program entrys found. `benchmarks/bench_exchange.py` line 329; `tools/loadtest.py` line 167; `tools/serve_for_loadtest.py` line 30
- <a id="f59"></a>**f59**: Program entry run as a script in benchmarks/bench_exchange.py. `benchmarks/bench_exchange.py` line 329
- <a id="f60"></a>**f60**: Program entry run as a script in tools/loadtest.py. `tools/loadtest.py` line 167
- <a id="f61"></a>**f61**: Program entry run as a script in tools/serve_for_loadtest.py. `tools/serve_for_loadtest.py` line 30
- <a id="f62"></a>**f62**: 3 package scripts found. `web/package.json` line 7; `web/package.json` line 8; `web/package.json` line 9
- <a id="f63"></a>**f63**: Package script npm run dev: vite (npm) in web/package.json. `web/package.json` line 7
- <a id="f64"></a>**f64**: Package script npm run build: tsc --noEmit && vite build (npm) in web/package.json. `web/package.json` line 8
- <a id="f65"></a>**f65**: Package script npm run test: vitest run (npm) in web/package.json. `web/package.json` line 9
- <a id="f66"></a>**f66**: 18 of 30 traced routes pass through src/marketlab/api then src/marketlab. `src/marketlab/api/app.py` line 548; `src/marketlab/api/app.py` line 587; `src/marketlab/api/app.py` line 609
- <a id="f67"></a>**f67**: POST /api/worlds is handled by start_world in src/marketlab/api/app.py; start_world calls world_json; world_json calls PracticeWorld.statement in src/marketlab/world.py, PracticeWorld.positions, PracticeWorld.today and instrument_json; 4 more steps not shown. `src/marketlab/api/app.py` line 766; `src/marketlab/api/app.py` line 329; `src/marketlab/world.py` line 507; `src/marketlab/world.py` line 510; `src/marketlab/world.py` line 515
- <a id="f69"></a>**f69**: POST /api/runs is handled by start_run in src/marketlab/api/app.py; start_run calls summary; summary calls instrument_json. `src/marketlab/api/app.py` line 620; `src/marketlab/api/app.py` line 196; `src/marketlab/api/app.py` line 185
- <a id="f71"></a>**f71**: CI step "Install" in job test of .github/workflows/ci.yml runs: python -m pip install --upgrade pip. `.github/workflows/ci.yml` line 21
- <a id="f72"></a>**f72**: CI step "Install" in job test of .github/workflows/ci.yml runs: pip install -e ".[dev,api,postgres]". `.github/workflows/ci.yml` line 22
- <a id="f73"></a>**f73**: CI step "Lint" in job test of .github/workflows/ci.yml runs: ruff check . `.github/workflows/ci.yml` line 24
- <a id="f74"></a>**f74**: CI step "Type check" in job test of .github/workflows/ci.yml runs: mypy. `.github/workflows/ci.yml` line 26
- <a id="f75"></a>**f75**: CI step "Tests" in job test of .github/workflows/ci.yml runs: pytest. `.github/workflows/ci.yml` line 28
- <a id="f76"></a>**f76**: A CI step in job web of .github/workflows/ci.yml runs: npm ci. `.github/workflows/ci.yml` line 74
- <a id="f77"></a>**f77**: A CI step in job web of .github/workflows/ci.yml runs: npm test. `.github/workflows/ci.yml` line 75
- <a id="f78"></a>**f78**: A CI step in job web of .github/workflows/ci.yml runs: npm run build. `.github/workflows/ci.yml` line 76
- <a id="f79"></a>**f79**: Code in web/src/components uses code in web/src/lib (82 references). `web/src/components/AccountStrip.tsx` line 1; `web/src/components/AccountStrip.tsx` line 2; `web/src/components/AccountStrip.tsx` line 3
- <a id="f80"></a>**f80**: Code in web/src uses code in web/src/components (9 references). `web/src/App.tsx` line 2; `web/src/App.tsx` line 3; `web/src/App.tsx` line 4
- <a id="f81"></a>**f81**: Code in src/marketlab uses code in src/marketlab/core (8 references). `src/marketlab/cli.py` line 19; `src/marketlab/codec.py` line 17; `src/marketlab/costs.py` line 23
- <a id="f82"></a>**f82**: Code in web/src uses code in web/src/lib (7 references). `web/src/App.tsx` line 10; `web/src/App.tsx` line 11; `web/src/App.tsx` line 12
- <a id="f83"></a>**f83**: Code in src/marketlab/api uses code in src/marketlab (6 references). `src/marketlab/api/app.py` line 60; `src/marketlab/api/app.py` line 61; `src/marketlab/api/app.py` line 63
- <a id="f84"></a>**f84**: Code in src/marketlab uses code in src/marketlab/sim (5 references). `src/marketlab/cli.py` line 24; `src/marketlab/factors.py` line 20; `src/marketlab/news.py` line 30
- <a id="f85"></a>**f85**: Code in src/marketlab uses code in src/marketlab/ledger (3 references). `src/marketlab/cli.py` line 153; `src/marketlab/session.py` line 20; `src/marketlab/world.py` line 29
- <a id="f86"></a>**f86**: Code in src/marketlab/ledger uses code in src/marketlab (3 references). `src/marketlab/ledger/fills.py` line 13; `src/marketlab/ledger/gateway.py` line 36; `src/marketlab/ledger/gateway.py` line 37
- <a id="f87"></a>**f87**: Code in src/marketlab/sim uses code in src/marketlab (3 references). `src/marketlab/sim/agents.py` line 34; `src/marketlab/sim/runner.py` line 24; `src/marketlab/sim/runner.py` line 26
- <a id="f88"></a>**f88**: Code in src/marketlab/ledger uses code in src/marketlab/core (2 references). `src/marketlab/ledger/fills.py` line 12; `src/marketlab/ledger/gateway.py` line 24
- <a id="f89"></a>**f89**: Code in src/marketlab/sim uses code in src/marketlab/core (2 references). `src/marketlab/sim/agents.py` line 23; `src/marketlab/sim/runner.py` line 25
- <a id="f90"></a>**f90**: Code in tools uses code in src/marketlab (2 references). `tools/loadtest.py` line 22; `tools/loadtest.py` line 113
- <a id="f91"></a>**f91**: Code in benchmarks uses code in src/marketlab/core (1 reference). `benchmarks/bench_exchange.py` line 38
- <a id="f92"></a>**f92**: Code in src/marketlab uses code in src/marketlab/api (1 reference). `src/marketlab/cli.py` line 123
- <a id="f93"></a>**f93**: Code in src/marketlab/api uses code in src/marketlab/core (1 reference). `src/marketlab/api/app.py` line 62
- <a id="f94"></a>**f94**: src/marketlab and src/marketlab/api each use the other. `src/marketlab/cli.py` line 123; `src/marketlab/api/app.py` line 60
- <a id="f95"></a>**f95**: src/marketlab and src/marketlab/ledger each use the other. `src/marketlab/cli.py` line 153; `src/marketlab/ledger/fills.py` line 13
- <a id="f96"></a>**f96**: src/marketlab and src/marketlab/sim each use the other. `src/marketlab/cli.py` line 24; `src/marketlab/sim/agents.py` line 34
- <a id="f97"></a>**f97**: src/marketlab/core/__init__.py is used by 42 other files. `src/marketlab/core/__init__.py`; `benchmarks/bench_exchange.py` line 38; `src/marketlab/api/app.py` line 62
- <a id="f98"></a>**f98**: web/src/lib/format.ts is used by 25 other files. `web/src/lib/format.ts`; `web/src/components/AccountStrip.tsx` line 1; `web/src/components/Activity.tsx` line 3
- <a id="f99"></a>**f99**: web/src/lib/market.ts is used by 24 other files. `web/src/lib/market.ts`; `web/src/App.tsx` line 10; `web/src/components/Activity.tsx` line 4
- <a id="f100"></a>**f100**: src/marketlab/ledger/__init__.py is used by 19 other files. `src/marketlab/ledger/__init__.py`; `src/marketlab/api/app.py` line 64; `src/marketlab/session.py` line 20
- <a id="f101"></a>**f101**: tests/helpers.py is used by 17 other files. `tests/helpers.py`; `tests/export_fixture.py` line 20; `tests/property/test_auction_model.py` line 30
- <a id="f102"></a>**f102**: 32 commits between 09 Aug 2026 and 07 Nov 2026. commit 129b31b; commit bd44488; commit 97cbfa1
- <a id="f103"></a>**f103**: web/src/components/PracticeView.tsx changed in 14 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `web/src/components/PracticeView.tsx`; commit b212e4a; commit b1a75f6; commit 1264d94
- <a id="f104"></a>**f104**: src/marketlab/api/app.py changed in 13 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/api/app.py`; commit 129b31b; commit bd44488; commit b83c943
- <a id="f105"></a>**f105**: web/src/desk.css changed in 10 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `web/src/desk.css`; commit b1a75f6; commit c958090; commit fc88513
- <a id="f106"></a>**f106**: web/src/App.tsx changed in 9 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `web/src/App.tsx`; commit b1a75f6; commit 1b45851; commit 7cfc523
- <a id="f107"></a>**f107**: src/marketlab/ledger/ledger.py changed in 8 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/ledger/ledger.py`; commit bd44488; commit c002169; commit 1b45851
- <a id="f108"></a>**f108**: tests/unit/test_api_worlds.py changed in 8 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `tests/unit/test_api_worlds.py`; commit bd44488; commit 1264d94; commit b83c943
- <a id="f109"></a>**f109**: web/src/components/PriceChart.tsx changed in 8 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `web/src/components/PriceChart.tsx`; commit fc88513; commit 7cfc523; commit 8adb832
- <a id="f110"></a>**f110**: src/marketlab/cli.py changed in 7 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/cli.py`; commit c002169; commit 1b45851; commit 0e133d4
- <a id="f111"></a>**f111**: src/marketlab/world.py changed in 7 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/world.py`; commit bd44488; commit 1264d94; commit b83c943
- <a id="f112"></a>**f112**: web/src/lib/world.ts changed in 7 commits by 1 author between 09 Aug 2026 and 07 Nov 2026. `web/src/lib/world.ts`; commit 1264d94; commit b83c943; commit 1b45851
- <a id="f113"></a>**f113**: web/src/components/PracticeView.tsx and web/src/desk.css changed in the same commit 7 times between 09 Aug 2026 and 07 Nov 2026. `web/src/components/PracticeView.tsx`; `web/src/desk.css`
- <a id="f114"></a>**f114**: src/marketlab/ledger/ledger.py and tests/unit/test_ledger.py changed in the same commit 6 times between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/ledger/ledger.py`; `tests/unit/test_ledger.py`
- <a id="f115"></a>**f115**: src/marketlab/world.py and tests/unit/test_api_worlds.py changed in the same commit 6 times between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/world.py`; `tests/unit/test_api_worlds.py`
- <a id="f116"></a>**f116**: web/src/components/PracticeView.tsx and web/src/lib/world.ts changed in the same commit 6 times between 09 Aug 2026 and 07 Nov 2026. `web/src/components/PracticeView.tsx`; `web/src/lib/world.ts`
- <a id="f117"></a>**f117**: web/src/components/PracticeView.tsx and web/src/components/PriceChart.tsx changed in the same commit 6 times between 09 Aug 2026 and 07 Nov 2026. `web/src/components/PracticeView.tsx`; `web/src/components/PriceChart.tsx`
- <a id="f118"></a>**f118**: web/src/App.tsx and web/src/components/PracticeView.tsx changed in the same commit 6 times between 09 Aug 2026 and 07 Nov 2026. `web/src/App.tsx`; `web/src/components/PracticeView.tsx`
- <a id="f119"></a>**f119**: src/marketlab/api/app.py and web/src/components/PracticeView.tsx changed in the same commit 6 times between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/api/app.py`; `web/src/components/PracticeView.tsx`
- <a id="f120"></a>**f120**: src/marketlab/cli.py and src/marketlab/ledger/ledger.py changed in the same commit 5 times between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/cli.py`; `src/marketlab/ledger/ledger.py`
- <a id="f121"></a>**f121**: src/marketlab/world.py and web/src/components/PracticeView.tsx changed in the same commit 5 times between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/world.py`; `web/src/components/PracticeView.tsx`
- <a id="f122"></a>**f122**: src/marketlab/api/app.py and src/marketlab/ledger/ledger.py changed in the same commit 5 times between 09 Aug 2026 and 07 Nov 2026. `src/marketlab/api/app.py`; `src/marketlab/ledger/ledger.py`

## Removed

These were written by the model and failed a check.

- "The service connects to a database using a DATABASE_URL environment variable that defaults to a SQLite file at /data/practice.db." (system): names technology its facts do not: SQLite
