# web

The site at https://shivemn.github.io/Plumb/: a gallery of reports and a
page that draws each one. Plain HTML, CSS and JavaScript modules, with no
build step, so GitHub Pages serves this folder as it is.

- `index.html`, `assets/home.js`: paste a repo; repos with a report open at once,
  and recent reports are listed from `reports/index.json`
- `report.html`, `assets/report.js`: one report, from `reports/<owner>__<name>.json`
- `repos.toml`: the repos the gallery has reports for

Write the reports, then push; `.github/workflows/pages.yml` publishes the folder.

    cd core
    uv run plumb site build      # stops at a free model's daily limit; run again to carry on

To look at the site locally:

    python -m http.server -d web 8000
