# fastapi/full-stack-fastapi-template

Commit 77e550a. Kind: service. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
49 of 49 claims kept after checking them against the code.

## Overview

- This repository contains a service with one deployable service and 23 routes, consumers, or scheduled jobs. ([f1](#f1))
- The codebase is written primarily in TypeScript with 96 source files and Python with 28 source files. ([f2](#f2), [f3](#f3))
- It uses Docker and docker-compose for deployment, with a backend Dockerfile and compose.yml configuration. ([f23](#f23), [f25](#f25))
- The project includes GitHub Actions workflows for testing, deployment, and release automation. ([f8](#f8), [f11](#f11), [f12](#f12), [f20](#f20), [f21](#f21))

## System design

- The backend service runs FastAPI with four workers and is built from the repository Dockerfile. ([f30](#f30))
- PostgreSQL runs as the db service using the postgres:18 image and is accessed via psycopg. ([f31](#f31))
- Sentry is used as an outside service with the sentry-sdk dependency. ([f32](#f32))
- Adminer runs as a Compose service using the adminer image. ([f33](#f33))
- Mailpit runs as a Compose service using the axllent/mailpit image. ([f34](#f34))
- Playwright runs as a Compose service built from the repository and is used for tests. ([f35](#f35))
- A proxy runs as a Compose service using the traefik:v3.7 image. ([f36](#f36))
- There are five Alembic database migrations in backend/app/alembic/versions. ([f51](#f51))

## How a request moves

- A typical request passes through backend/app/api/routes then backend/app then backend/app/core. ([f92](#f92))
- 19 of 23 traced routes reach the database. ([f93](#f93))
- POST /api/v1/users/ is handled by create_user in backend/app/api/routes/users.py. ([f94](#f94))
- create_user calls get_user_by_email in backend/app/crud.py, create_user in backend/app/crud.py, generate_new_account_email in backend/app/utils.py and send_email. ([f94](#f94))
- create_user in backend/app/crud.py calls get_password_hash in backend/app/core/security.py. ([f94](#f94))
- get_user_by_email reaches the database via session.exec in backend/app/crud.py. ([f94](#f94))
- POST /api/v1/login/access-token is handled by login_access_token in backend/app/api/routes/login.py. ([f95](#f95))
- login_access_token calls authenticate in backend/app/crud.py and create_access_token in backend/app/core/security.py. ([f95](#f95))
- authenticate calls get_user_by_email and verify_password. ([f95](#f95))
- authenticate reaches the database via session.add in backend/app/crud.py. ([f95](#f95))

## Ways into the code

- The backend exposes 23 HTTP routes across five route modules: items, login, private, users, and utils. ([f52](#f52), [f53](#f53), [f54](#f54), [f55](#f55), [f56](#f56), [f57](#f57), [f58](#f58), [f59](#f59), [f60](#f60), [f61](#f61), [f62](#f62), [f63](#f63), [f64](#f64), [f65](#f65), [f66](#f66), [f67](#f67), [f68](#f68), [f69](#f69), [f70](#f70), [f71](#f71), [f72](#f72), [f73](#f73), [f74](#f74), [f75](#f75))
- Three Typer CLI commands are defined in scripts/prepare_release.py: prepare, current-version, and release-notes. ([f76](#f76), [f77](#f77), [f78](#f78), [f79](#f79))
- Three Python scripts serve as program entry points: backend/app/initial_data.py, scripts/add_latest_release_date.py, and scripts/prepare_release.py. ([f80](#f80), [f81](#f81), [f82](#f82), [f83](#f83))
- Seven package scripts are defined across frontend/package.json, packages/react-email/package.json, and the root package.json for development, building, and testing. ([f84](#f84), [f85](#f85), [f86](#f86), [f87](#f87), [f88](#f88), [f89](#f89), [f90](#f90), [f91](#f91))

## Code map

- The repository contains 96 TypeScript source files totaling 10,010 lines, 28 Python source files totaling 1,736 lines, 1 CSS file with 124 lines, 8 shell files with 76 lines, and 3 HTML files with 16 lines. ([f2](#f2), [f3](#f3), [f4](#f4), [f5](#f5), [f6](#f6))
- Frontend components in Admin, Items, UserSettings, and Common all depend on the ui component library with 20, 18, 10, and 8 references respectively. ([f128](#f128), [f129](#f129), [f134](#f134), [f135](#f135))
- The frontend ui component library depends on frontend/src/lib with 23 references. ([f127](#f127))
- Frontend routes depend on the ui component library with 15 references, on the Common component with 7 references, and on hooks with 7 references. ([f130](#f130), [f136](#f136), [f137](#f137))
- Frontend src and frontend/src/routes have a bidirectional dependency with 6 references from src to routes. ([f138](#f138), [f145](#f145))
- The frontend client/client module depends on client/core with 14 references. ([f131](#f131))
- In the react-email package, emails depend on ui with 12 references. ([f132](#f132))
- Backend app/api/routes depends on backend/app with 10 references. ([f133](#f133))
- Backend app depends on backend/app/core with 5 references, and these two have a bidirectional dependency. ([f139](#f139), [f143](#f143))
- Backend app/api and backend/app/api/routes have a bidirectional dependency, each with 5 references to the other. ([f140](#f140), [f141](#f141), [f144](#f144))
- Backend app and backend/app/api have a bidirectional dependency. ([f142](#f142))
- The most depended-upon files are frontend/src/lib/utils.ts used by 27 files, frontend/src/client/index.ts used by 20 files, frontend/src/components/ui/button.tsx used by 18 files, backend/app/core/config.py used by 16 files, and backend/app/models.py used by 16 files. ([f146](#f146), [f147](#f147), [f148](#f148), [f149](#f149), [f150](#f150))

## Hot spots

Nothing in this section could be supported by what was found.

## How to contribute

- Run the frontend development server with bun run dev in the frontend directory. ([f85](#f85))
- Build the frontend with bun run build in the frontend directory. ([f86](#f86))
- Run frontend tests with bun run test in the frontend directory. ([f87](#f87))
- Run the frontend development server from the repository root with bun run dev. ([f88](#f88))
- Run frontend tests from the repository root with bun run test. ([f89](#f89))
- Build react-email templates with bun run build in the packages/react-email directory. ([f90](#f90))
- Run react-email development server on port 3333 with bun run dev in the packages/react-email directory. ([f91](#f91))
- CI updates pre-commit hooks with uv run prek update --freeze --cooldown-days 7. ([f102](#f102))
- CI extracts release version with uv run python scripts/prepare_release.py current-version. ([f121](#f121))
- CI generates release notes with uv run python scripts/prepare_release.py release-notes. ([f122](#f122))
- Recently closed pull requests were merged a median of 43 hours after being opened. ([f126](#f126))

## Sources

- <a id="f1"></a>**f1**: Looks like a service repo: 1 deployable service(s) and 23 route(s), consumer(s) or scheduled job(s). `backend/Dockerfile` line 1; `backend/app/api/routes/items.py` line 13; `backend/app/api/routes/items.py` line 48
- <a id="f2"></a>**f2**: 96 source files in typescript, 10,010 lines in all. `frontend/src/client/types.gen.ts`; `frontend/src/components/ui/sidebar.tsx`; `frontend/src/client/sdk.gen.ts`
- <a id="f3"></a>**f3**: 28 source files in python, 1,736 lines in all. `backend/app/api/routes/users.py`; `scripts/prepare_release.py`; `backend/app/models.py`
- <a id="f4"></a>**f4**: 1 source file in css, 124 lines in all. `frontend/src/index.css`
- <a id="f5"></a>**f5**: 8 source files in shell, 76 lines in all. `scripts/test-local.sh`; `scripts/test.sh`; `scripts/generate-client.sh`
- <a id="f6"></a>**f6**: 3 source files in html, 16 lines in all. `frontend/index.html`; `backend/app/email-templates/new_account.html`; `backend/app/email-templates/reset_password.html`
- <a id="f8"></a>**f8**: GitHub Actions workflow .github/workflows/add-to-project.yml. `.github/workflows/add-to-project.yml`
- <a id="f11"></a>**f11**: GitHub Actions workflow .github/workflows/deploy-docker-compose.yml. `.github/workflows/deploy-docker-compose.yml`
- <a id="f12"></a>**f12**: GitHub Actions workflow .github/workflows/deploy.yml. `.github/workflows/deploy.yml`
- <a id="f20"></a>**f20**: GitHub Actions workflow .github/workflows/test-backend.yml. `.github/workflows/test-backend.yml`
- <a id="f21"></a>**f21**: GitHub Actions workflow .github/workflows/test-docker-compose.yml. `.github/workflows/test-docker-compose.yml`
- <a id="f23"></a>**f23**: Build or deploy file backend/Dockerfile. `backend/Dockerfile`
- <a id="f25"></a>**f25**: Build or deploy file compose.yml. `compose.yml`
- <a id="f30"></a>**f30**: Service run from this repo: backend (Dockerfile, runs ["fastapi", "run", "--workers", "4"]; Compose service built from .). `backend/Dockerfile` line 1; `compose.override.yml` line 34; `compose.yml` line 49
- <a id="f31"></a>**f31**: Database, cache or queue: PostgreSQL (dependency psycopg; setting mentions postgresql://; setting mentions postgres://; setting mentions postgresql+psycopg://; Compose service db, image postgres:18). `backend/pyproject.toml` line 15; `.env` line 18; `backend/app/core/config.py` line 37; `backend/app/core/config.py` line 39; `compose.yml` line 20
- <a id="f32"></a>**f32**: Outside service: Sentry (dependency sentry-sdk). `backend/pyproject.toml` line 18
- <a id="f33"></a>**f33**: Other container: adminer (Compose service, image adminer). `compose.yml` line 34
- <a id="f34"></a>**f34**: Other container: mailpit (Compose service, image axllent/mailpit). `compose.override.yml` line 71
- <a id="f35"></a>**f35**: Other container: playwright (Compose service built from ., used for tests). `compose.override.yml` line 77
- <a id="f36"></a>**f36**: Other container: proxy (Compose service, image traefik:v3.7). `compose.override.yml` line 3; `compose.yml` line 3
- <a id="f51"></a>**f51**: 5 Alembic database migrations in backend/app/alembic/versions. `backend/app/alembic/versions/1a31ce608336_add_cascade_delete_relationships.py`; `backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py`
- <a id="f52"></a>**f52**: 23 http routes found. `backend/app/api/routes/items.py` line 13; `backend/app/api/routes/items.py` line 48; `backend/app/api/routes/items.py` line 61
- <a id="f53"></a>**f53**: HTTP route GET /api/v1/items/ (fastapi) in backend/app/api/routes/items.py. `backend/app/api/routes/items.py` line 13
- <a id="f54"></a>**f54**: HTTP route GET /api/v1/items/{id} (fastapi) in backend/app/api/routes/items.py. `backend/app/api/routes/items.py` line 48
- <a id="f55"></a>**f55**: HTTP route POST /api/v1/items/ (fastapi) in backend/app/api/routes/items.py. `backend/app/api/routes/items.py` line 61
- <a id="f56"></a>**f56**: HTTP route PUT /api/v1/items/{id} (fastapi) in backend/app/api/routes/items.py. `backend/app/api/routes/items.py` line 75
- <a id="f57"></a>**f57**: HTTP route DELETE /api/v1/items/{id} (fastapi) in backend/app/api/routes/items.py. `backend/app/api/routes/items.py` line 99
- <a id="f58"></a>**f58**: HTTP route POST /api/v1/login/access-token (fastapi) in backend/app/api/routes/login.py. `backend/app/api/routes/login.py` line 23
- <a id="f59"></a>**f59**: HTTP route POST /api/v1/login/test-token (fastapi) in backend/app/api/routes/login.py. `backend/app/api/routes/login.py` line 45
- <a id="f60"></a>**f60**: HTTP route POST /api/v1/password-recovery/{email} (fastapi) in backend/app/api/routes/login.py. `backend/app/api/routes/login.py` line 53
- <a id="f61"></a>**f61**: HTTP route POST /api/v1/reset-password/ (fastapi) in backend/app/api/routes/login.py. `backend/app/api/routes/login.py` line 77
- <a id="f62"></a>**f62**: HTTP route POST /api/v1/password-recovery-html-content/{email} (fastapi) in backend/app/api/routes/login.py. `backend/app/api/routes/login.py` line 100
- <a id="f63"></a>**f63**: HTTP route POST /api/v1/private/users/ (fastapi) in backend/app/api/routes/private.py. `backend/app/api/routes/private.py` line 23
- <a id="f64"></a>**f64**: HTTP route GET /api/v1/users/ (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 32
- <a id="f65"></a>**f65**: HTTP route POST /api/v1/users/ (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 54
- <a id="f66"></a>**f66**: HTTP route PATCH /api/v1/users/me (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 81
- <a id="f67"></a>**f67**: HTTP route PATCH /api/v1/users/me/password (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 103
- <a id="f68"></a>**f68**: HTTP route GET /api/v1/users/me (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 124
- <a id="f69"></a>**f69**: HTTP route DELETE /api/v1/users/me (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 132
- <a id="f70"></a>**f70**: HTTP route POST /api/v1/users/signup (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 146
- <a id="f71"></a>**f71**: HTTP route GET /api/v1/users/{user_id} (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 162
- <a id="f72"></a>**f72**: HTTP route PATCH /api/v1/users/{user_id} (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 182
- <a id="f73"></a>**f73**: HTTP route DELETE /api/v1/users/{user_id} (fastapi) in backend/app/api/routes/users.py. `backend/app/api/routes/users.py` line 214
- <a id="f74"></a>**f74**: HTTP route POST /api/v1/utils/test-email/ (fastapi) in backend/app/api/routes/utils.py. `backend/app/api/routes/utils.py` line 11
- <a id="f75"></a>**f75**: HTTP route GET /api/v1/utils/health-check/ (fastapi) in backend/app/api/routes/utils.py. `backend/app/api/routes/utils.py` line 29
- <a id="f76"></a>**f76**: 3 commands found. `scripts/prepare_release.py` line 103; `scripts/prepare_release.py` line 133; `scripts/prepare_release.py` line 153
- <a id="f77"></a>**f77**: Command prepare (typer) in scripts/prepare_release.py. `scripts/prepare_release.py` line 103
- <a id="f78"></a>**f78**: Command current-version (typer) in scripts/prepare_release.py. `scripts/prepare_release.py` line 133
- <a id="f79"></a>**f79**: Command release-notes (typer) in scripts/prepare_release.py. `scripts/prepare_release.py` line 153
- <a id="f80"></a>**f80**: 3 program entrys found. `backend/app/initial_data.py` line 22; `scripts/add_latest_release_date.py` line 39; `scripts/prepare_release.py` line 174
- <a id="f81"></a>**f81**: Program entry run as a script in backend/app/initial_data.py. `backend/app/initial_data.py` line 22
- <a id="f82"></a>**f82**: Program entry run as a script in scripts/add_latest_release_date.py. `scripts/add_latest_release_date.py` line 39
- <a id="f83"></a>**f83**: Program entry run as a script in scripts/prepare_release.py. `scripts/prepare_release.py` line 174
- <a id="f84"></a>**f84**: 7 package scripts found. `frontend/package.json` line 7; `frontend/package.json` line 8; `frontend/package.json` line 12
- <a id="f85"></a>**f85**: Package script bun run dev: vite (bun) in frontend/package.json. `frontend/package.json` line 7
- <a id="f86"></a>**f86**: Package script bun run build: tsc -p tsconfig.build.json && vite build (bun) in frontend/package.json. `frontend/package.json` line 8
- <a id="f87"></a>**f87**: Package script bun run test: bunx playwright test (bun) in frontend/package.json. `frontend/package.json` line 12
- <a id="f88"></a>**f88**: Package script bun run dev: bun run --filter frontend dev (bun) in package.json. `package.json` line 9
- <a id="f89"></a>**f89**: Package script bun run test: bun run --filter frontend test (bun) in package.json. `package.json` line 11
- <a id="f90"></a>**f90**: Package script bun run build: email build (bun) in packages/react-email/package.json. `packages/react-email/package.json` line 6
- <a id="f91"></a>**f91**: Package script bun run dev: email dev --port 3333 (bun) in packages/react-email/package.json. `packages/react-email/package.json` line 7
- <a id="f92"></a>**f92**: 5 of 23 traced routes pass through backend/app/api/routes then backend/app then backend/app/core. `backend/app/api/routes/login.py` line 24; `backend/app/api/routes/login.py` line 78; `backend/app/api/routes/users.py` line 57
- <a id="f93"></a>**f93**: 19 of 23 traced routes reach the database. `backend/app/api/routes/items.py` line 23
- <a id="f94"></a>**f94**: POST /api/v1/users/ is handled by create_user in backend/app/api/routes/users.py; create_user in backend/app/api/routes/users.py calls get_user_by_email in backend/app/crud.py, create_user in backend/app/crud.py, generate_new_account_email in backend/app/utils.py and send_email; create_user in backend/app/crud.py calls get_password_hash in backend/app/core/security.py; 1 more step not shown; get_user_by_email reaches the database (session.exec in backend/app/crud.py). `backend/app/api/routes/users.py` line 54; `backend/app/crud.py` line 34; `backend/app/crud.py` line 10; `backend/app/utils.py` line 87; `backend/app/utils.py` line 34; `backend/app/crud.py` line 36
- <a id="f95"></a>**f95**: POST /api/v1/login/access-token is handled by login_access_token in backend/app/api/routes/login.py; login_access_token calls authenticate in backend/app/crud.py and create_access_token in backend/app/core/security.py; authenticate calls get_user_by_email and verify_password; authenticate reaches the database (session.add in backend/app/crud.py). `backend/app/api/routes/login.py` line 23; `backend/app/crud.py` line 45; `backend/app/core/security.py` line 22; `backend/app/crud.py` line 34; `backend/app/core/security.py` line 29; `backend/app/crud.py` line 57
- <a id="f102"></a>**f102**: CI step "Bump pre-commit hooks" in job bump-pre-commit-hooks of .github/workflows/bump-pre-commit-hooks.yml runs: uv run prek update --freeze --cooldown-days 7. `.github/workflows/bump-pre-commit-hooks.yml` line 38
- <a id="f121"></a>**f121**: CI step "Extract release details" in job create-draft-release of .github/workflows/create-draft-release.yml runs: version="$(uv run python scripts/prepare_release.py current-version)". `.github/workflows/create-draft-release.yml` line 39
- <a id="f122"></a>**f122**: CI step "Extract release details" in job create-draft-release of .github/workflows/create-draft-release.yml runs: uv run python scripts/prepare_release.py release-notes > draft-release-notes.md. `.github/workflows/create-draft-release.yml` line 40
- <a id="f126"></a>**f126**: Recently closed pull requests were merged a median of 43 hours after being opened (19 merged pull requests measured). issue 2529; issue 2525; issue 2521
- <a id="f127"></a>**f127**: Code in frontend/src/components/ui uses code in frontend/src/lib (23 references). `frontend/src/components/ui/alert.tsx` line 4; `frontend/src/components/ui/avatar.tsx` line 4; `frontend/src/components/ui/badge.tsx` line 5
- <a id="f128"></a>**f128**: Code in frontend/src/components/Admin uses code in frontend/src/components/ui (20 references). `frontend/src/components/Admin/AddUser.tsx` line 9; `frontend/src/components/Admin/AddUser.tsx` line 10; `frontend/src/components/Admin/AddUser.tsx` line 11
- <a id="f129"></a>**f129**: Code in frontend/src/components/Items uses code in frontend/src/components/ui (18 references). `frontend/src/components/Items/AddItem.tsx` line 9; `frontend/src/components/Items/AddItem.tsx` line 10; `frontend/src/components/Items/AddItem.tsx` line 20
- <a id="f130"></a>**f130**: Code in frontend/src/routes uses code in frontend/src/components/ui (15 references). `frontend/src/routes/_layout.tsx` line 5; `frontend/src/routes/login.tsx` line 12; `frontend/src/routes/login.tsx` line 20
- <a id="f131"></a>**f131**: Code in frontend/src/client/client uses code in frontend/src/client/core (14 references). `frontend/src/client/client/client.gen.ts` line 6; `frontend/src/client/client/client.gen.ts` line 7; `frontend/src/client/client/client.gen.ts` line 8
- <a id="f132"></a>**f132**: Code in packages/react-email/emails uses code in packages/react-email/ui (12 references). `packages/react-email/emails/new_account.tsx` line 2; `packages/react-email/emails/new_account.tsx` line 3; `packages/react-email/emails/new_account.tsx` line 4
- <a id="f133"></a>**f133**: Code in backend/app/api/routes uses code in backend/app (10 references). `backend/app/api/routes/items.py` line 8; `backend/app/api/routes/login.py` line 8; `backend/app/api/routes/login.py` line 12
- <a id="f134"></a>**f134**: Code in frontend/src/components/UserSettings uses code in frontend/src/components/ui (10 references). `frontend/src/components/UserSettings/ChangePassword.tsx` line 7; `frontend/src/components/UserSettings/ChangePassword.tsx` line 15; `frontend/src/components/UserSettings/ChangePassword.tsx` line 16
- <a id="f135"></a>**f135**: Code in frontend/src/components/Common uses code in frontend/src/components/ui (8 references). `frontend/src/components/Common/Appearance.tsx` line 4; `frontend/src/components/Common/Appearance.tsx` line 5; `frontend/src/components/Common/Appearance.tsx` line 11
- <a id="f136"></a>**f136**: Code in frontend/src/routes uses code in frontend/src/components/Common (7 references). `frontend/src/routes/__root.tsx` line 4; `frontend/src/routes/__root.tsx` line 5; `frontend/src/routes/_layout.tsx` line 3
- <a id="f137"></a>**f137**: Code in frontend/src/routes uses code in frontend/src/hooks (7 references). `frontend/src/routes/_layout.tsx` line 10; `frontend/src/routes/login.tsx` line 23; `frontend/src/routes/recover-password.tsx` line 23
- <a id="f138"></a>**f138**: Code in frontend/src uses code in frontend/src/routes (6 references). `frontend/src/routeTree.gen.ts` line 11; `frontend/src/routeTree.gen.ts` line 12; `frontend/src/routeTree.gen.ts` line 13
- <a id="f139"></a>**f139**: Code in backend/app uses code in backend/app/core (5 references). `backend/app/crud.py` line 6; `backend/app/initial_data.py` line 5; `backend/app/main.py` line 9
- <a id="f140"></a>**f140**: Code in backend/app/api uses code in backend/app/api/routes (5 references). `backend/app/api/main.py` line 3; `backend/app/api/main.py` line 3; `backend/app/api/main.py` line 3
- <a id="f141"></a>**f141**: Code in backend/app/api/routes uses code in backend/app/api (5 references). `backend/app/api/routes/items.py` line 7; `backend/app/api/routes/login.py` line 9; `backend/app/api/routes/private.py` line 6
- <a id="f142"></a>**f142**: backend/app and backend/app/api each use the other. `backend/app/main.py` line 8; `backend/app/api/deps.py` line 14
- <a id="f143"></a>**f143**: backend/app and backend/app/core each use the other. `backend/app/crud.py` line 6; `backend/app/core/db.py` line 3
- <a id="f144"></a>**f144**: backend/app/api and backend/app/api/routes each use the other. `backend/app/api/main.py` line 3; `backend/app/api/routes/items.py` line 7
- <a id="f145"></a>**f145**: frontend/src and frontend/src/routes each use the other. `frontend/src/routeTree.gen.ts` line 11; `frontend/src/routes/recover-password.tsx` line 25
- <a id="f146"></a>**f146**: frontend/src/lib/utils.ts is used by 27 other files. `frontend/src/lib/utils.ts`; `frontend/src/components/Admin/columns.tsx` line 6; `frontend/src/components/Common/Logo.tsx` line 4
- <a id="f147"></a>**f147**: frontend/src/client/index.ts is used by 20 other files. `frontend/src/client/index.ts`; `frontend/src/components/Admin/AddUser.tsx` line 8; `frontend/src/components/Admin/DeleteUser.tsx` line 6
- <a id="f148"></a>**f148**: frontend/src/components/ui/button.tsx is used by 18 other files. `frontend/src/components/ui/button.tsx`; `frontend/src/components/Admin/AddUser.tsx` line 9; `frontend/src/components/Admin/DeleteUser.tsx` line 7
- <a id="f149"></a>**f149**: backend/app/core/config.py is used by 16 other files. `backend/app/core/config.py`; `backend/app/alembic/env.py` line 23; `backend/app/api/deps.py` line 12
- <a id="f150"></a>**f150**: backend/app/models.py is used by 16 other files. `backend/app/models.py`; `backend/app/alembic/env.py` line 22; `backend/app/api/deps.py` line 14
