# Hosting

The site is static and lives on GitHub Pages. The API (`plumb serve`, with
its worker) runs on Render's free plan from `render.yaml`.

## Why Render

Checked 20 November 2026:

- Hugging Face Spaces: new Docker Spaces need a paid plan; only static
  Spaces are free.
- Render: a free Docker web service with 512 MB and a tenth of a CPU, no
  card needed. It sleeps after 15 minutes without visitors and takes about
  a minute to wake, and its disk is wiped when it sleeps.
- Koyeb, Fly.io, Cloud Run and Oracle Cloud all ask for a card.

Plumb fits in Render's free size. Run in a container held to 512 MB and a
tenth of a CPU:

| Repo | Time |
|------|------|
| pallets/itsdangerous | 8 s |
| fastapi/full-stack-fastapi-template | 10 s |
| encode/httpx | 13 s |
| spring-petclinic/spring-petclinic-rest | 11 s |
| django/django | 156 s |

Memory peaked at 234 MB, on Django.

## Setting it up

1. Sign in at render.com with GitHub. No card is needed.
2. New, then Blueprint, then pick `shivemn/Plumb`. Render reads
   `render.yaml` and asks for two values:
   - `OPENROUTER_API_KEY`: a new OpenRouter key, used only by the server.
   - `GITHUB_TOKEN`: a fine-grained token with no permissions beyond
     public repositories (read-only). Without it, GitHub allows 60 requests
     an hour from Render's shared addresses, and issue and review facts
     go missing.
3. Apply. The first build takes a few minutes. The service's address looks
   like `https://plumb-api.onrender.com`; `/api/health` should answer.
4. Put that address in `HOSTED` in `web/assets/config.js`, and in
   `connect-src` in the content security policy at the top of
   `web/index.html`, `web/report.html` and `web/privacy.html`.

Render rebuilds the API only when the server's code changes
(`buildFilter` in `render.yaml`).

## What the free plan means for visitors

- The first visitor after a quiet spell waits about a minute. The site
  wakes the server as soon as the home page opens, and says so if a repo
  is pasted before it is up.
- A sleep wipes the job table, so a report the server wrote is lost and a
  job page left open stops working. Reports in `web/reports` are not
  affected.
- The server writes at most `PLUMB_DAILY_REPORTS` reports a day with a
  free model, so the key never costs money. A restart resets that count;
  OpenRouter's own daily limit on free models still applies.
