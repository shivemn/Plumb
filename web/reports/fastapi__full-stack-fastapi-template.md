# fastapi/full-stack-fastapi-template

Commit 77e550a. Kind: service. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
17 of 19 claims kept after checking them against the code.

## In short

- The application is containerized with Docker Compose (compose.yml) and runs alongside PostgreSQL, a Traefik proxy, and supporting services for email testing, database administration, and Playwright testing. ([f25](#f25), [f30](#f30), [f31](#f31), [f33](#f33), [f34](#f34), [f35](#f35), [f36](#f36))
- The backend service starts via its Dockerfile using "fastapi run --workers 4" and the frontend uses Bun for development, building, and test scripts defined across package.json files. ([f30](#f30), [f85](#f85), [f86](#f86), [f87](#f87))

## System design

- The repository runs a FastAPI backend service backed by a PostgreSQL database with schema managed through 5 Alembic migrations. ([f30](#f30), [f31](#f31), [f51](#f51))
- External error tracking integrates with Sentry via the sentry-sdk dependency. ([f32](#f32))
- All services are configured through environment variables read from multiple Compose files and the frontend configuration, covering secrets, domain, email, and database settings. ([f37](#f37), [f38](#f38), [f39](#f39), [f40](#f40), [f41](#f41), [f42](#f42), [f43](#f43), [f44](#f44), [f45](#f45), [f46](#f46), [f47](#f47), [f48](#f48), [f49](#f49), [f50](#f50))

## How a request moves

- A request typically enters through a route handler in backend/app/api/routes/, which calls into backend/app/crud.py for data access and backend/app/core/security.py for authentication helpers, before reaching the database via session.exec, session.add, or session.get. ([f92](#f92), [f93](#f93), [f94](#f94), [f95](#f95), [f96](#f96), [f97](#f97), [f98](#f98), [f99](#f99), [f100](#f100), [f101](#f101))
- For example, POST /api/v1/users/ is handled by create_user in backend/app/api/routes/users.py, which calls get_user_by_email and create_user in backend/app/crud.py, get_password_hash in backend/app/core/security.py, and generate_new_account_email in backend/app/utils.py, with get_user_by_email reaching the database via session.exec in backend/app/crud.py. ([f94](#f94))

## Ways in

- The backend exposes 23 FastAPI routes under /api/v1 grouped into items, authentication, user management, private admin, and utility endpoints across five route modules. ([f52](#f52), [f53](#f53), [f54](#f54), [f55](#f55), [f56](#f56), [f57](#f57), [f58](#f58), [f59](#f59), [f60](#f60), [f61](#f61), [f62](#f62), [f63](#f63), [f64](#f64), [f65](#f65), [f66](#f66), [f67](#f67), [f68](#f68), [f69](#f69), [f70](#f70), [f71](#f71), [f72](#f72), [f73](#f73), [f74](#f74), [f75](#f75))
- Three Typer CLI commands for release preparation live in scripts/prepare_release.py, which also serves as a direct script entry point alongside initial_data.py and add_latest_release_date.py. ([f76](#f76), [f77](#f77), [f78](#f78), [f79](#f79), [f80](#f80), [f81](#f81), [f82](#f82), [f83](#f83))
- Frontend development, build, and test workflows run via Bun package scripts, with a root workspace script proxying to the frontend and a separate react-email package for email template development. ([f84](#f84), [f85](#f85), [f86](#f86), [f87](#f87), [f88](#f88), [f89](#f89), [f90](#f90), [f91](#f91))

## Code map

- The backend centers on a trio of mutually dependent directories — app, app/api, and app/core — with app/core/config.py and app/models.py as the two most widely imported files across the service. ([f133](#f133), [f139](#f139), [f140](#f140), [f141](#f141), [f142](#f142), [f143](#f143), [f144](#f144), [f149](#f149), [f150](#f150))
- The frontend organizes components in layers: ui sits at the base and is imported by Admin, Items, Common, UserSettings, and the route modules, while routes also pull in Common and hooks, and the top-level src imports routes back. ([f127](#f127), [f128](#f128), [f129](#f129), [f130](#f130), [f134](#f134), [f135](#f135), [f136](#f136), [f137](#f137), [f138](#f138), [f145](#f145))
- : Across the frontend, lib/utils.ts, client/index.ts, and components/ui/button.tsx are the three most reused modules, each referenced by 18–27 other files. ([f146](#f146), [f147](#f147), [f148](#f148))

## Hot spots

Nothing in this section could be supported by what was found.

## How to contribute

- Frontend tests run with `bunx playwright test` in the frontend directory or `bun run test` from the repository root. ([f87](#f87), [f89](#f89))
- Start the frontend dev server with `bun run dev` in the frontend directory or `bun run dev` from the root. ([f85](#f85), [f88](#f88))
- CI updates pre-commit hooks using `uv run prek update --freeze --cooldown-days 7`. ([f102](#f102))
- Pull requests were merged a median of 43 hours after opening across 19 recent PRs. ([f126](#f126))

## Sources

- <a id="f25"></a>**f25**: Build or deploy file compose.yml. `compose.yml`
- <a id="f30"></a>**f30**: Service run from this repo: backend (Dockerfile, runs ["fastapi", "run", "--workers", "4"]; Compose service built from .). `backend/Dockerfile` line 1; `compose.override.yml` line 34; `compose.yml` line 49
- <a id="f31"></a>**f31**: Database, cache or queue: PostgreSQL (dependency psycopg; setting mentions postgresql://; setting mentions postgres://; setting mentions postgresql+psycopg://; Compose service db, image postgres:18). `backend/pyproject.toml` line 15; `.env` line 18; `backend/app/core/config.py` line 37; `backend/app/core/config.py` line 39; `compose.yml` line 20
- <a id="f32"></a>**f32**: Outside service: Sentry (dependency sentry-sdk). `backend/pyproject.toml` line 18
- <a id="f33"></a>**f33**: Other container: adminer (Compose service, image adminer). `compose.yml` line 34
- <a id="f34"></a>**f34**: Other container: mailpit (Compose service, image axllent/mailpit). `compose.override.yml` line 71
- <a id="f35"></a>**f35**: Other container: playwright (Compose service built from ., used for tests). `compose.override.yml` line 77
- <a id="f36"></a>**f36**: Other container: proxy (Compose service, image traefik:v3.7). `compose.override.yml` line 3; `compose.yml` line 3
- <a id="f37"></a>**f37**: Setting CI is read from the environment in compose.override.yml, frontend/playwright.config.ts. `compose.override.yml` line 95; `frontend/playwright.config.ts` line 19
- <a id="f38"></a>**f38**: Setting DOMAIN is read from the environment in compose.deploy.yml, compose.yml. `compose.deploy.yml` line 41; `compose.yml` line 44
- <a id="f39"></a>**f39**: Setting EMAILS_FROM_EMAIL is read from the environment in compose.yml. `compose.yml` line 63
- <a id="f40"></a>**f40**: Setting FIRST_SUPERUSER is read from the environment in compose.override.yml, compose.yml. `compose.override.yml` line 88; `compose.yml` line 58
- <a id="f41"></a>**f41**: Setting FIRST_SUPERUSER_PASSWORD is read from the environment in compose.override.yml, compose.yml. `compose.override.yml` line 89; `compose.yml` line 59
- <a id="f42"></a>**f42**: Setting PLAYWRIGHT_BASE_URL is read from the environment in frontend/playwright.config.ts. `frontend/playwright.config.ts` line 4
- <a id="f43"></a>**f43**: Setting POSTGRES_PASSWORD is read from the environment in compose.yml. `compose.yml` line 31
- <a id="f44"></a>**f44**: Setting PROJECT_NAME is read from the environment in compose.yml. `compose.yml` line 56
- <a id="f45"></a>**f45**: Setting SECRET_KEY is read from the environment in compose.yml. `compose.yml` line 57
- <a id="f46"></a>**f46**: Setting SENTRY_DSN is read from the environment in compose.yml. `compose.yml` line 65
- <a id="f47"></a>**f47**: Setting SMTP_HOST is read from the environment in compose.yml. `compose.yml` line 60
- <a id="f48"></a>**f48**: Setting SMTP_PASSWORD is read from the environment in compose.yml. `compose.yml` line 62
- <a id="f49"></a>**f49**: Setting SMTP_USER is read from the environment in compose.yml. `compose.yml` line 61
- <a id="f50"></a>**f50**: Setting VITE_API_URL is read from the environment in frontend/src/main.tsx. `frontend/src/main.tsx` line 18
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
- <a id="f96"></a>**f96**: POST /api/v1/password-recovery/{email} is handled by recover_password in backend/app/api/routes/login.py; recover_password calls get_user_by_email in backend/app/crud.py, generate_password_reset_token in backend/app/utils.py, generate_reset_password_email and send_email; generate_reset_password_email calls render_email_template; get_user_by_email reaches the database (session.exec in backend/app/crud.py). `backend/app/api/routes/login.py` line 53; `backend/app/crud.py` line 34; `backend/app/utils.py` line 105; `backend/app/utils.py` line 70; `backend/app/utils.py` line 34; `backend/app/crud.py` line 36
- <a id="f97"></a>**f97**: POST /api/v1/password-recovery-html-content/{email} is handled by recover_password_html_content in backend/app/api/routes/login.py; recover_password_html_content calls get_user_by_email in backend/app/crud.py, generate_password_reset_token in backend/app/utils.py and generate_reset_password_email; generate_reset_password_email calls render_email_template; get_user_by_email reaches the database (session.exec in backend/app/crud.py). `backend/app/api/routes/login.py` line 100; `backend/app/crud.py` line 34; `backend/app/utils.py` line 105; `backend/app/utils.py` line 70; `backend/app/utils.py` line 25; `backend/app/crud.py` line 36
- <a id="f98"></a>**f98**: PATCH /api/v1/users/me/password is handled by update_password_me in backend/app/api/routes/users.py; update_password_me calls verify_password in backend/app/core/security.py and get_password_hash; update_password_me reaches the database (session.add in backend/app/api/routes/users.py). `backend/app/api/routes/users.py` line 103; `backend/app/core/security.py` line 29; `backend/app/core/security.py` line 35; `backend/app/api/routes/users.py` line 119
- <a id="f99"></a>**f99**: POST /api/v1/private/users/ is handled by create_user in backend/app/api/routes/private.py; create_user calls get_password_hash in backend/app/core/security.py; create_user reaches the database (session.add in backend/app/api/routes/private.py). `backend/app/api/routes/private.py` line 23; `backend/app/core/security.py` line 35; `backend/app/api/routes/private.py` line 35
- <a id="f100"></a>**f100**: GET /api/v1/items/ is handled by read_items in backend/app/api/routes/items.py; read_items reaches the database (session.exec in backend/app/api/routes/items.py). `backend/app/api/routes/items.py` line 13; `backend/app/api/routes/items.py` line 23
- <a id="f101"></a>**f101**: GET /api/v1/items/{id} is handled by read_item in backend/app/api/routes/items.py; read_item reaches the database (session.get in backend/app/api/routes/items.py). `backend/app/api/routes/items.py` line 48; `backend/app/api/routes/items.py` line 53
- <a id="f102"></a>**f102**: CI step "Bump pre-commit hooks" in job bump-pre-commit-hooks of .github/workflows/bump-pre-commit-hooks.yml runs: uv run prek update --freeze --cooldown-days 7. `.github/workflows/bump-pre-commit-hooks.yml` line 38
- <a id="f126"></a>**f126**: Recently closed pull requests were merged a median of 43 hours after being opened (19 merged pull requests measured). issue 2529; issue 2525; issue 2521
- <a id="f127"></a>**f127**: Code in frontend/src/components/ui uses code in frontend/src/lib (23 references). `frontend/src/components/ui/alert.tsx` line 4; `frontend/src/components/ui/avatar.tsx` line 4; `frontend/src/components/ui/badge.tsx` line 5
- <a id="f128"></a>**f128**: Code in frontend/src/components/Admin uses code in frontend/src/components/ui (20 references). `frontend/src/components/Admin/AddUser.tsx` line 9; `frontend/src/components/Admin/AddUser.tsx` line 10; `frontend/src/components/Admin/AddUser.tsx` line 11
- <a id="f129"></a>**f129**: Code in frontend/src/components/Items uses code in frontend/src/components/ui (18 references). `frontend/src/components/Items/AddItem.tsx` line 9; `frontend/src/components/Items/AddItem.tsx` line 10; `frontend/src/components/Items/AddItem.tsx` line 20
- <a id="f130"></a>**f130**: Code in frontend/src/routes uses code in frontend/src/components/ui (15 references). `frontend/src/routes/_layout.tsx` line 5; `frontend/src/routes/login.tsx` line 12; `frontend/src/routes/login.tsx` line 20
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

## Removed

These were written by the model and failed a check.

- "This repository contains a full-stack FastAPI service with a Python backend (28 files) and a TypeScript frontend (96 files) that exposes 23 REST API routes for items, users, authentication, and utilities." (overview): names technology its facts do not: FastAPI
- "The stack includes supporting containers for database administration (adminer), email testing (mailpit), end-to-end testing (playwright), and a Traefik reverse proxy all orchestrated via Docker Compose." (system): names technology its facts do not: Docker
