# gothinkster/node-express-realworld-example-app

Commit 30b68e1. Kind: service. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
24 of 29 claims kept after checking them against the code.

## Overview

- This repository contains a single deployable service with 20 routes, consumers, or scheduled jobs. ([f1](#f1))
- The codebase consists of 31 TypeScript files, 4 SQL files, and 1 JavaScript file. ([f2](#f2), [f3](#f3), [f4](#f4))
- It uses a Dockerfile and a package.json for build and deployment. ([f6](#f6), [f7](#f7))

## System design

- The repository runs a service named node-express-realworld-example-app via Docker with the command "node api". ([f8](#f8))
- PostgreSQL is used as the database, accessed through Prisma as the datasource provider. ([f9](#f9))
- The database schema is managed through 4 Prisma migrations located in src/prisma/migrations. ([f14](#f14))

## Ways into the code

- A root route is defined in src/main.ts. ([f35](#f35))
- Three package scripts are available: start, build, and test, each delegating to nx commands. ([f36](#f36), [f37](#f37), [f38](#f38), [f39](#f39))

## Code map

- The source code contains 31 TypeScript files, 4 SQL files, and 1 JavaScript file. ([f2](#f2), [f3](#f3), [f4](#f4))
- Code is organized under src/app/routes with four route modules: article, auth, profile, and tag. ([f46](#f46), [f47](#f47), [f48](#f48), [f49](#f49))
- The src/app/routes directory uses each of the four route modules. ([f46](#f46), [f47](#f47), [f48](#f48), [f49](#f49))
- The article route uses the auth, profile, and tag routes as well as models and prisma. ([f40](#f40), [f50](#f50), [f51](#f51), [f52](#f52), [f53](#f53))
- The auth route uses the article route, models, and prisma. ([f41](#f41), [f54](#f54), [f57](#f57))
- The profile route uses the auth route. ([f42](#f42))
- The prisma code uses the auth route. ([f43](#f43))
- There are circular dependencies between article and auth routes, between article and prisma, and between auth and prisma. ([f55](#f55), [f56](#f56), [f57](#f57))
- The src directory uses both the models and routes directories. ([f44](#f44), [f45](#f45))
- The most used files are prisma-client.ts used by 5 files, http-exception.model.ts and auth.ts each used by 4 files, and article.service.ts and auth.service.ts each used by 3 files. ([f58](#f58), [f59](#f59), [f60](#f60), [f61](#f61), [f62](#f62))

## Hot spots

- There were 4 commits between 06 Oct 2023 and 04 Jan 2024. ([f63](#f63))
- src/app/routes/auth/auth.service.ts changed in 3 commits by 1 author during this period. ([f64](#f64))
- src/main.ts changed in 3 commits by 1 author during this period. ([f65](#f65))
- src/prisma/seed.ts changed in 3 commits by 1 author during this period. ([f66](#f66))
- Each of these three files changed in 3 of the 4 commits in the period. ([f63](#f63), [f64](#f64), [f65](#f65), [f66](#f66))

## How to contribute

- The project has three package scripts: npm run start runs nx serve, npm run build runs nx build, and npm run test runs nx test. ([f36](#f36), [f37](#f37), [f38](#f38), [f39](#f39))

## Sources

- <a id="f1"></a>**f1**: Looks like a service repo: 1 deployable service(s) and 20 route(s), consumer(s) or scheduled job(s). `Dockerfile` line 7; `src/app/routes/article/article.controller.ts` line 30; `src/app/routes/article/article.controller.ts` line 45
- <a id="f2"></a>**f2**: 31 source files in typescript, 1,716 lines in all. `src/app/routes/article/article.service.ts`; `src/app/routes/article/article.controller.ts`; `src/app/routes/auth/auth.service.ts`
- <a id="f3"></a>**f3**: 4 source files in sql, 163 lines in all. `src/prisma/migrations/20210924225358_initial/migration.sql`; `src/prisma/migrations/20211001143221_implicit_tags/migration.sql`; `src/prisma/migrations/20211221184529_deprecated_preview/migration.sql`
- <a id="f4"></a>**f4**: 1 source file in javascript, 3 lines in all. `jest.preset.js`
- <a id="f6"></a>**f6**: Build or deploy file Dockerfile. `Dockerfile`
- <a id="f7"></a>**f7**: Build or deploy file package.json. `package.json`
- <a id="f8"></a>**f8**: Service run from this repo: node-express-realworld-example-app (Dockerfile, runs [ "node", "api" ]). `Dockerfile` line 7
- <a id="f9"></a>**f9**: Database, cache or queue: PostgreSQL (Prisma datasource, provider postgresql). `src/prisma/schema.prisma` line 2
- <a id="f14"></a>**f14**: 4 Prisma database migrations in src/prisma/migrations. `src/prisma/migrations/20210924225358_initial/migration.sql`; `src/prisma/migrations/20211221184529_deprecated_preview/migration.sql`
- <a id="f35"></a>**f35**: HTTP route GET / (express) in src/main.ts. `src/main.ts` line 21
- <a id="f36"></a>**f36**: 3 package scripts found. `package.json` line 6; `package.json` line 7; `package.json` line 8
- <a id="f37"></a>**f37**: Package script npm run start: nx serve (npm) in package.json. `package.json` line 6
- <a id="f38"></a>**f38**: Package script npm run build: nx build (npm) in package.json. `package.json` line 7
- <a id="f39"></a>**f39**: Package script npm run test: nx test (npm) in package.json. `package.json` line 8
- <a id="f40"></a>**f40**: Code in src/app/routes/article uses code in src/app/routes/auth (2 references). `src/app/routes/article/article.controller.ts` line 2; `src/app/routes/article/author.mapper.ts` line 1
- <a id="f41"></a>**f41**: Code in src/app/routes/auth uses code in src/app/routes/article (2 references). `src/app/routes/auth/user.model.ts` line 1; `src/app/routes/auth/user.model.ts` line 2
- <a id="f42"></a>**f42**: Code in src/app/routes/profile uses code in src/app/routes/auth (2 references). `src/app/routes/profile/profile.controller.ts` line 2; `src/app/routes/profile/profile.utils.ts` line 1
- <a id="f43"></a>**f43**: Code in src/prisma uses code in src/app/routes/auth (2 references). `src/prisma/seed.ts` line 10; `src/prisma/seed.ts` line 11
- <a id="f44"></a>**f44**: Code in src uses code in src/app/models (1 reference). `src/main.ts` line 5
- <a id="f45"></a>**f45**: Code in src uses code in src/app/routes (1 reference). `src/main.ts` line 4
- <a id="f46"></a>**f46**: Code in src/app/routes uses code in src/app/routes/article (1 reference). `src/app/routes/routes.ts` line 3
- <a id="f47"></a>**f47**: Code in src/app/routes uses code in src/app/routes/auth (1 reference). `src/app/routes/routes.ts` line 4
- <a id="f48"></a>**f48**: Code in src/app/routes uses code in src/app/routes/profile (1 reference). `src/app/routes/routes.ts` line 5
- <a id="f49"></a>**f49**: Code in src/app/routes uses code in src/app/routes/tag (1 reference). `src/app/routes/routes.ts` line 2
- <a id="f50"></a>**f50**: Code in src/app/routes/article uses code in src/app/models (1 reference). `src/app/routes/article/article.service.ts` line 3
- <a id="f51"></a>**f51**: Code in src/app/routes/article uses code in src/app/routes/profile (1 reference). `src/app/routes/article/article.service.ts` line 4
- <a id="f52"></a>**f52**: Code in src/app/routes/article uses code in src/app/routes/tag (1 reference). `src/app/routes/article/article.service.ts` line 6
- <a id="f53"></a>**f53**: Code in src/app/routes/article uses code in src/prisma (1 reference). `src/app/routes/article/article.service.ts` line 2
- <a id="f54"></a>**f54**: Code in src/app/routes/auth uses code in src/app/models (1 reference). `src/app/routes/auth/auth.service.ts` line 4
- <a id="f55"></a>**f55**: src/app/routes/article and src/app/routes/auth each use the other. `src/app/routes/article/article.controller.ts` line 2; `src/app/routes/auth/user.model.ts` line 1
- <a id="f56"></a>**f56**: src/app/routes/article and src/prisma each use the other. `src/app/routes/article/article.service.ts` line 2; `src/prisma/seed.ts` line 12
- <a id="f57"></a>**f57**: src/app/routes/auth and src/prisma each use the other. `src/app/routes/auth/auth.service.ts` line 3; `src/prisma/seed.ts` line 10
- <a id="f58"></a>**f58**: src/prisma/prisma-client.ts is used by 5 other files. `src/prisma/prisma-client.ts`; `src/app/routes/article/article.service.ts` line 2; `src/app/routes/auth/auth.service.ts` line 3
- <a id="f59"></a>**f59**: src/app/models/http-exception.model.ts is used by 4 other files. `src/app/models/http-exception.model.ts`; `src/app/routes/article/article.service.ts` line 3; `src/app/routes/auth/auth.service.ts` line 4
- <a id="f60"></a>**f60**: src/app/routes/auth/auth.ts is used by 4 other files. `src/app/routes/auth/auth.ts`; `src/app/routes/article/article.controller.ts` line 2; `src/app/routes/auth/auth.controller.ts` line 2
- <a id="f61"></a>**f61**: src/app/routes/article/article.service.ts is used by 3 other files. `src/app/routes/article/article.service.ts`; `src/app/routes/article/article.controller.ts` line 3; `src/prisma/seed.ts` line 12
- <a id="f62"></a>**f62**: src/app/routes/auth/auth.service.ts is used by 3 other files. `src/app/routes/auth/auth.service.ts`; `src/app/routes/auth/auth.controller.ts` line 3; `src/prisma/seed.ts` line 11
- <a id="f63"></a>**f63**: 4 commits between 06 Oct 2023 and 04 Jan 2024. commit 30b68e1; commit 88b258c; commit 5eeccf1
- <a id="f64"></a>**f64**: src/app/routes/auth/auth.service.ts changed in 3 commits by 1 author between 06 Oct 2023 and 04 Jan 2024. `src/app/routes/auth/auth.service.ts`; commit 30b68e1; commit 5eeccf1; commit e40aeb9
- <a id="f65"></a>**f65**: src/main.ts changed in 3 commits by 1 author between 06 Oct 2023 and 04 Jan 2024. `src/main.ts`; commit 88b258c; commit 5eeccf1; commit e40aeb9
- <a id="f66"></a>**f66**: src/prisma/seed.ts changed in 3 commits by 1 author between 06 Oct 2023 and 04 Jan 2024. `src/prisma/seed.ts`; commit 88b258c; commit 5eeccf1; commit e40aeb9

## Removed

These were written by the model and failed a check.

- "The service exposes 20 HTTP routes handled by Express." (entry_points): names technology its facts do not: Express
- "Article routes provide 11 endpoints for articles, comments, and favorites in src/app/routes/article/article.controller.ts." (entry_points): states numbers its facts do not: 11
- "Auth routes provide 4 endpoints for user registration, login, and profile in src/app/routes/auth/auth.controller.ts." (entry_points): states numbers its facts do not: 4
- "Profile routes provide 3 endpoints for viewing and following profiles in src/app/routes/profile/profile.controller.ts." (entry_points): states numbers its facts do not: 3
- "Tag routes provide 1 endpoint for listing tags in src/app/routes/tag/tag.controller.ts." (entry_points): states numbers its facts do not: 1
