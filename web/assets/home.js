// Home: paste a repo, follow it as it is read, then open its report. Repos
// already analysed open at once. The layout follows the Figma design; every
// number, sentence and step on the page comes from a real report or a real
// job on the server.
import { getHealth, getJob, startJob } from "./api.js";
import { getJSON, githubFile, h, plumbMark, plural, reducedMotion, shell, svg } from "./common.js";
import { API } from "./config.js";

const root = document.getElementById("app");
let reports = [];
let featured = null; // { slug, report }: a full report for the preview window

// What the visitor sees while a job runs, and the server's steps behind each.
const STEPS = ["Reading repository structure", "Tracing imports and routes", "Mapping request paths", "Checking every explanation"];
const STEP_OF = {
  "Fetching the repo": 0,
  "Reading files and history": 0,
  "Finding services, routes and imports": 1,
  "Tracing requests through the code": 2,
  "Reading issues and pull requests": 2,
  "Writing and checking the report": 3,
};

start();

async function start() {
  try {
    reports = (await getJSON("reports/index.json")).reports || [];
  } catch {
    reports = [];
  }
  featured = await pickFeatured();
  root.replaceChildren(shell(h("main", { id: "top" }, hero(), preview(), how(), recent())));
  revealOnScroll();
  // A free host sleeps when unused; knocking now means it is likely awake
  // by the time a repo is pasted.
  if (API) getHealth().catch(() => {});
  const want = new URLSearchParams(location.search).get("repo");
  if (want) {
    document.getElementById("repo").value = want;
    submit(want);
  }
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
}

// The first stored report with a diagram, a traced request and a code map.
async function pickFeatured() {
  let fallback = null;
  for (const entry of reports) {
    try {
      const report = await getJSON(`reports/${entry.slug}.json`);
      const v = report.views || {};
      fallback ||= { slug: entry.slug, report };
      if ((v.system?.parts || []).length >= 2 && Array.isArray(v.flows) && v.flows.length && v.code_map?.rows?.length) return { slug: entry.slug, report };
    } catch {
      /* try the next one */
    }
  }
  return fallback;
}

const arrowIcon = () => svg('<path d="M5 12h13M13 6l6 6-6 6"/>', { viewBox: "0 0 24 24", "aria-hidden": "true" });

// ---------------------------------------------------------------- hero

function hero() {
  const section = h("section", {
    class: "hero page-wrap",
    id: "hero",
    onmousemove: (event) => {
      const box = section.getBoundingClientRect();
      section.style.setProperty("--pointer-x", `${((event.clientX - box.left) / box.width) * 100}%`);
      section.style.setProperty("--pointer-y", `${((event.clientY - box.top) / box.height) * 100}%`);
    },
  });
  const input = h("input", {
    id: "repo",
    name: "repo",
    type: "text",
    inputmode: "url",
    placeholder: "github.com/owner/repository",
    autocomplete: "off",
    spellcheck: "false",
    onfocus: () => section.classList.add("has-focus"),
    onblur: () => section.classList.remove("has-focus"),
  });
  const form = h(
    "form",
    {
      onsubmit: (event) => {
        event.preventDefault();
        submit(input.value);
      },
    },
    h("label", { for: "repo", text: "GitHub repository" }),
    h("span", { class: "prompt", "aria-hidden": "true", text: ">" }),
    input,
    h("button", { type: "submit" }, h("span", { text: "Analyze repo" }), arrowIcon()),
  );
  const examples = reports.slice(0, 3).map((r) =>
    h("button", {
      type: "button",
      text: r.repo,
      onclick: () => {
        input.value = r.repo;
        input.focus();
      },
    }),
  );
  section.append(
    h("div", { class: "hero-glow" }),
    plumbMark(true),
    h("p", { class: "eyebrow", text: "Repository intelligence, with receipts" }),
    h("h1", { text: "Understand a repo before you read it." }),
    h("p", { class: "hero-copy", text: "See the architecture, request flows, and files that matter—then trace every explanation back to its source." }),
    h("div", { class: "repo-box" }, form, examples.length ? h("div", { class: "example-row" }, h("span", { text: "Try an example" }), examples) : null),
    h("div", { id: "progress" }),
    h("div", { id: "message" }),
    h(
      "div",
      { class: "hero-proof", "aria-label": "What Plumb offers" },
      h("span", { text: "No sign-up" }),
      h("i"),
      h("span", { text: "Source-linked claims" }),
      h("i"),
      h("span", { text: "Public GitHub repos" }),
    ),
  );
  return section;
}

// "https://github.com/a/b.git", "github.com/a/b/tree/main", "a/b" -> "a/b"
export function parseRepo(text) {
  const cleaned = String(text).trim().replace(/^git@github\.com:/, "").replace(/^https?:\/\//, "").replace(/^(www\.)?github\.com\//, "");
  const match = cleaned.match(/^([A-Za-z0-9-]{1,39})\/([A-Za-z0-9._-]{1,100}?)(?:\.git)?(?:[/?#].*)?$/);
  return match ? `${match[1]}/${match[2]}` : null;
}

function say(...content) {
  const box = document.getElementById("message");
  box.replaceChildren(content.length ? h("p", { class: "form-message", role: "status" }, ...content) : "");
}

function setBusy(busy) {
  const hero = document.getElementById("hero");
  const form = hero.querySelector("form");
  const button = form.querySelector("button[type=submit]");
  hero.classList.toggle("is-analyzing", busy);
  form.setAttribute("aria-busy", String(busy));
  button.disabled = busy;
  button.replaceChildren(...(busy ? [h("span", { text: "Reading…" }), h("i", { class: "spinner", "aria-hidden": "true" })] : [h("span", { text: "Analyze repo" }), arrowIcon()]));
}

// The steps panel under the box. `step` is the one under way; `note` its status.
function showProgress(step, note = "Working…") {
  const box = document.getElementById("progress");
  if (step === null) return box.replaceChildren();
  const share = `${(Math.min(step, STEPS.length - 1) / (STEPS.length - 1)) * 100}%`;
  let panel = box.querySelector(".analysis-progress");
  if (!panel) {
    panel = h(
      "div",
      { class: "analysis-progress", "aria-live": "polite" },
      h("div", { class: "progress-line", "aria-hidden": "true" }, h("span"), h("i")),
      h("ol", {}, STEPS.map((s) => h("li", {}, h("span", { text: s }), h("small")))),
    );
    box.replaceChildren(panel);
  }
  panel.querySelector(".progress-line > span").style.height = share;
  panel.querySelector(".progress-line > i").style.top = share;
  [...panel.querySelectorAll("li")].forEach((li, i) => {
    li.className = i < step ? "complete" : i === step ? "current" : "";
    li.querySelector("small").textContent = i < step ? "Complete" : i === step ? note : "Waiting";
  });
}

async function submit(text) {
  const form = document.querySelector("#hero form");
  if (form.getAttribute("aria-busy") === "true") return;
  const repo = parseRepo(text);
  if (!repo) return say("Enter a repository as owner/name or paste its GitHub URL.");
  say();
  const known = reports.find((r) => r.repo.toLowerCase() === repo.toLowerCase());
  if (known) {
    setBusy(true);
    return later(reducedMotion() ? 0 : 600).then(() => location.assign(`report.html?r=${encodeURIComponent(known.slug)}`));
  }
  if (!API) {
    return say(
      h("strong", { text: `${repo} has not been analysed yet. ` }),
      "Analysing new repos here is being switched on; until then, run Plumb on your own machine: ",
      h("code", { text: `uv run plumb report ${repo} --model openrouter:<free-model>` }),
    );
  }
  setBusy(true);
  showProgress(0);
  // A sleeping server holds the first request while it starts.
  const slow = setTimeout(() => say("Waking Plumb's server. It sleeps when nobody has used it for a while and takes about a minute to start; your repo goes in as soon as it is up."), 2500);
  const started = Date.now();
  let job = null;
  try {
    while (!job) {
      try {
        job = await startJob(repo);
      } catch (error) {
        if (error.waking && Date.now() - started < 120_000) {
          await later(5000);
          continue;
        }
        throw error;
      }
    }
    clearTimeout(slow);
    say();
    await follow(job.id);
  } catch (error) {
    clearTimeout(slow);
    setBusy(false);
    showProgress(null);
    say(error.message || "Something went wrong while reading the repo.");
  }
}

// Follow the job until it is done, then open its report.
async function follow(id) {
  let misses = 0;
  for (;;) {
    let job;
    try {
      job = await getJob(id);
      misses = 0;
    } catch (error) {
      if (++misses > 5) throw error;
      await later(1500 * misses);
      continue;
    }
    if (job.status === "failed") throw new Error(job.error || "The analysis stopped.");
    if (job.status === "done") {
      showProgress(STEPS.length);
      await later(reducedMotion() ? 0 : 500);
      return location.assign(`report.html?job=${encodeURIComponent(job.id)}`);
    }
    if (job.status === "queued") showProgress(0, job.queue_position > 1 ? `${job.queue_position} in line` : "Waiting…");
    else showProgress(STEP_OF[job.stage] ?? 0);
    await later(1200);
  }
}

const later = (ms) => new Promise((done) => setTimeout(done, ms));

// ---------------------------------------------------------------- preview

function preview() {
  return h(
    "section",
    { class: "preview-section page-wrap reveal", id: "preview" },
    h(
      "div",
      { class: "section-intro reveal-child" },
      h("p", { class: "eyebrow", text: "A map, not another wall of code" }),
      h("h2", { text: "Start with the shape of the system." }),
      h("p", { text: "Plumb gives you the mental model first, then lets you move from explanation to evidence without losing context." }),
    ),
    featured ? reportWindow(featured.slug, featured.report) : null,
  );
}

function reportWindow(slug, report) {
  const repo = report.repo;
  const name = `${repo.owner}/${repo.name}`;
  const link = (hash) => `report.html?r=${encodeURIComponent(slug)}${hash}`;
  const v = report.views || {};
  const stat = (label) => (v.stats || []).find((s) => s.label === label)?.value;
  const kept = report.sections.reduce((n, s) => n + s.claims.length, 0);
  const written = kept + report.removed.filter((r) => r.text).length;
  const lead = report.sections.find((s) => s.id === "overview")?.claims[0];

  return h(
    "div",
    { class: "report-window reveal-child" },
    h(
      "div",
      { class: "window-bar" },
      h("div", { class: "window-dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")),
      h("span", { text: `${name} · ${repo.commit.slice(0, 7)}` }),
      h("span", { class: "report-status", text: "Every sentence checked" }),
    ),
    h(
      "div",
      { class: "report-layout" },
      h(
        "aside",
        { class: "report-nav" },
        h("div", { class: "mini-line" }, h("span")),
        h("a", { class: "active", href: link("#top-summary"), text: "Overview" }),
        h("a", { href: link("#system"), text: "How it connects" }),
        h("a", { href: link("#flow"), text: "Request flow" }),
        h("a", { href: link("#structure"), text: "Code map" }),
        h("a", { href: link("#contribute"), text: "Start here" }),
      ),
      h(
        "div",
        { class: "report-content" },
        h(
          "div",
          { class: "report-heading" },
          h("div", {}, h("p", { class: "report-kicker", text: "Repository overview" }), h("h3", { class: name.length > 22 ? "long" : "", text: name })),
          h("a", { href: `https://github.com/${name}` }, "Open GitHub ", h("span", { text: "↗" })),
        ),
        lead ? h("div", { class: "report-lead" }, lead.text, sources(report, lead)) : null,
        h(
          "dl",
          { class: "repo-stats" },
          h("div", {}, h("dt", { text: "Primary language" }), h("dd", { text: stat("Language") || "—" })),
          h("div", {}, h("dt", { text: "Files mapped" }), h("dd", { text: stat("Source files") || "—" })),
          h("div", {}, h("dt", { text: "Sentences kept" }), h("dd", { class: "verified", text: `${kept} / ${written}` })),
        ),
        systemCard(report, link),
      ),
    ),
  );
}

// The count after a sentence, and the evidence behind it.
function sources(report, claim) {
  const facts = claim.fact_ids.map((id) => report.facts.find((f) => f.id === id)).filter(Boolean);
  const wrap = h("span", { class: "source-wrap" });
  const chip = h("button", { class: "source-chip", type: "button", "aria-expanded": "false", text: plural(facts.length, "source") });
  const pop = h(
    "div",
    { class: "source-popover" },
    h("strong", { text: "Evidence behind this sentence" }),
    facts.slice(0, 4).map((f) => {
      const e = (f.evidence || []).find((x) => x.path) || {};
      const lines = e.start_line ? `:${e.start_line}${e.end_line && e.end_line !== e.start_line ? `–${e.end_line}` : ""}` : "";
      return h(
        "a",
        { href: e.path ? githubFile(report.repo, e.path, e.start_line, e.end_line) : `https://github.com/${report.repo.owner}/${report.repo.name}` },
        h("code", { text: `${e.path || "repository"}${lines}` }),
        h("span", { text: f.statement }),
      );
    }),
  );
  chip.addEventListener("click", () => {
    const open = chip.getAttribute("aria-expanded") !== "true";
    chip.setAttribute("aria-expanded", String(open));
    if (open) wrap.append(pop);
    else pop.remove();
  });
  wrap.append(chip);
  return wrap;
}

function systemCard(report, link) {
  const v = report.views;
  const titles = { map: "How the parts connect", flow: "How a request moves", code: "Where the important code lives" };
  const body = h("div");
  const strong = h("strong");
  const tabs = ["map", "flow", "code"].map((key) =>
    h("button", {
      type: "button",
      role: "tab",
      text: { map: "Map", flow: "Flow", code: "Code" }[key],
      onclick: () => choose(key),
    }),
  );
  const choose = (key) => {
    strong.textContent = titles[key];
    tabs.forEach((t) => t.classList.toggle("active", t.textContent.toLowerCase() === key));
    tabs.forEach((t) => t.setAttribute("aria-selected", String(t.textContent.toLowerCase() === key)));
    body.replaceChildren(key === "map" ? systemMap(v.system) : key === "flow" ? requestTrace(v.flows[0], report) : codeMap(v.code_map));
  };
  choose("map");
  const start = startHere(report, link);
  return h(
    "div",
    { class: "architecture-card", id: "architecture" },
    h(
      "div",
      { class: "card-title" },
      h("div", {}, h("span", { text: "From the code" }), strong),
      h("div", { class: "map-tabs", role: "tablist", "aria-label": "Report preview" }, tabs),
    ),
    body,
    start,
  );
}

const ROLE_TEXT = { service: "runs from this repo", store: "stores data", outside: "outside service", monitoring: "monitoring", container: "supporting container" };

function systemMap(system) {
  const parts = system?.parts || [];
  const service = parts.find((p) => p.role === "service");
  const callers = (system?.links || []).find((l) => l.source === "Clients" && (!service || l.target === service.name));
  const after = parts.find((p) => p.role === "store") || parts.find((p) => p.role === "outside");
  const nodes = [
    callers ? { name: "Clients", note: callers.label ? `calls over ${callers.label}` : "call the routes" } : null,
    service ? { name: service.name, note: ROLE_TEXT.service } : null,
    after ? { name: after.name, note: ROLE_TEXT[after.role] } : null,
  ].filter(Boolean);
  const map = h("div", { class: "system-map animated-map" });
  nodes.forEach((n, i) => {
    if (i) map.append(h("div", { class: "map-arrow" }, h("i")));
    map.append(h("div", { class: `map-node${i === 1 ? " transport" : ""}` }, h("span", { text: `0${i + 1}` }), h("strong", { text: n.name }), h("small", { text: n.note })));
  });
  return map;
}

function requestTrace(flow, report) {
  const rows = [[flow.route, `${flow.place.path}:${flow.place.line}`]];
  for (const step of flow.steps.filter((s) => s.caller === null || s.caller === 0).slice(0, 2)) rows.push([`${step.name}()`, `${step.place.path}:${step.place.line}`]);
  const reach = (flow.reaches || [])[0];
  if (reach) rows.push([reach.call, `reaches ${reach.what}`]);
  return h(
    "div",
    { class: "request-trace" },
    rows.map(([name, note], i) =>
      h(
        "div",
        { style: `--i: ${i}` },
        h("span", { text: `0${i + 1}` }),
        h("code", { text: name }),
        h("small", {}, note.includes(":") ? h("a", { href: githubFile(report.repo, note.split(":")[0], Number(note.split(":")[1])), text: note }) : note),
      ),
    ),
  );
}

function codeMap(map) {
  const folders = (map?.rows || []).flat().sort((a, b) => b.lines - a.lines).slice(0, 4);
  return h(
    "div",
    { class: "code-map" },
    folders.map((f, i) =>
      h(
        "button",
        { type: "button", style: `--i: ${i}` },
        h("span", {}, h("code", { text: `${f.path}/` }), h("small", { text: `${plural(f.files, "file")}, ${f.lines.toLocaleString("en")} lines` })),
        h("i", {}, f.blocks.slice(0, 9).map((b, j) => h("b", { style: `width: ${Math.max(10, Math.min(48, Math.round(Math.sqrt(b.lines) * 2.4)))}px; --i: ${j}` }))),
      ),
    ),
  );
}

function startHere(report, link) {
  const flow = (report.views.flows || [])[0];
  if (!flow) return null;
  return h(
    "div",
    { class: "file-path" },
    h("span", { text: "Start here" }),
    h("code", { text: flow.place.path }),
    h("p", { text: `Where ${flow.route} is handled.` }),
    h("a", { href: githubFile(report.repo, flow.place.path, flow.place.line), "aria-label": "Open the file on GitHub", text: "↗" }),
  );
}

// ---------------------------------------------------------------- how it works

function how() {
  const steps = [
    ["01", "Read the structure", "Plumb traces routes, imports, calls, dependencies, and the history of important files."],
    ["02", "Build the explanation", "The raw facts become a concise map of what runs, how data moves, and where to begin."],
    ["03", "Verify every claim", "Each sentence links back to evidence in the repository. Unsupported claims are removed."],
  ];
  return h(
    "section",
    { class: "how-section reveal", id: "how" },
    h(
      "div",
      { class: "page-wrap" },
      h("div", { class: "section-intro compact" }, h("p", { class: "eyebrow", text: "How it works" }), h("h2", { text: "Facts first. Explanation second." })),
      h(
        "ol",
        { class: "steps-grid reveal-child" },
        steps.map(([n, title, text]) => h("li", {}, h("span", { text: n }), h("div", {}, h("h3", { text: title }), h("p", { text })))),
      ),
    ),
  );
}

// ---------------------------------------------------------------- recent

function recent() {
  if (!reports.length) return null;
  const SHOWN = 3;
  const list = h("div", { class: "recent-list reveal-child" });
  const draw = (all) => list.replaceChildren(...(all ? reports : reports.slice(0, SHOWN)).map(row));
  draw(false);
  const more =
    reports.length > SHOWN
      ? h("button", {
          type: "button",
          text: "View all reports",
          onclick: (event) => {
            const all = event.currentTarget.dataset.all !== "true";
            event.currentTarget.dataset.all = String(all);
            event.currentTarget.textContent = all ? "Show fewer" : "View all reports";
            draw(all);
          },
        })
      : null;
  return h(
    "section",
    { class: "recent-section page-wrap reveal", id: "recent" },
    h("div", { class: "section-heading-row" }, h("div", {}, h("p", { class: "eyebrow", text: "From the workbench" }), h("h2", { text: "Recently explained" })), more),
    list,
  );
}

function row(r, i) {
  const kind = [r.language, r.kind === "service" ? "service" : r.kind === "library" ? "library" : r.kind].filter(Boolean).join(" ");
  return h(
    "a",
    { href: `report.html?r=${encodeURIComponent(r.slug)}` },
    h("span", { class: "report-index", text: String(i + 1).padStart(2, "0") }),
    h("div", { class: "recent-name" }, h("strong", { text: r.repo }), h("span", { text: kind.charAt(0).toUpperCase() + kind.slice(1) })),
    h("p", { text: r.summary }),
    h("time", { datetime: r.written_at || "", text: whenWritten(r.written_at) }),
    h("span", { class: "row-arrow", text: "→" }),
  );
}

function whenWritten(iso) {
  if (!iso) return "";
  const day = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(day.getTime())) return iso;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((today - day) / 86_400_000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return day.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

// ---------------------------------------------------------------- motion

// Sections rise in as they are reached.
function revealOnScroll() {
  const sections = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window) || reducedMotion()) {
    sections.forEach((s) => s.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.14 },
  );
  sections.forEach((s) => observer.observe(s));
}
