// Home: paste a repo, get its report. Repos already analysed open at once.
import { startJob } from "./api.js";
import { footer, getJSON, h, header, modelName, niceDate, reducedMotion, svg, whenSeen } from "./common.js";
import { API } from "./config.js";

const root = document.getElementById("app");
let reports = [];

start();

async function start() {
  try {
    reports = (await getJSON("reports/index.json")).reports || [];
  } catch {
    reports = [];
  }
  root.replaceChildren(page());
  typePlaceholder();
  const want = new URLSearchParams(location.search).get("repo");
  if (want) submit(want);
}

function page() {
  return h(
    "div",
    { class: "wrap" },
    header(),
    h("main", {}, hero(), steps(), recent()),
    footer(),
  );
}

// The plumb line hangs above the box; on submit the bob drops into it.
function plumbLine() {
  return svg(
    '<g class="swing"><line class="string" x1="20" y1="0" x2="20" y2="104"/>' +
      '<g class="drop"><path class="bob" d="M20 100 L29 111 L20 128 L11 111 Z"/></g></g>',
    { class: "plumb", viewBox: "0 0 40 132", "aria-hidden": "true" },
  );
}

function hero() {
  const input = h("input", {
    id: "repo",
    name: "repo",
    type: "text",
    inputmode: "url",
    autocomplete: "off",
    spellcheck: "false",
    placeholder: "github.com/owner/name",
  });
  const form = h(
    "form",
    {
      onsubmit: (event) => {
        event.preventDefault();
        submit(input.value);
      },
    },
    h("label", { for: "repo", text: "GitHub repo to explain" }),
    input,
    h(
      "button",
      { class: "go", type: "submit", "aria-label": "Explain this repo" },
      svg('<path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>', { viewBox: "0 0 24 24", "aria-hidden": "true" }),
    ),
  );
  const examples = reports.slice(0, 4).map((r) =>
    h("button", { type: "button", onclick: () => { input.value = r.repo; submit(r.repo); } , text: r.repo }),
  );
  return h(
    "section",
    { class: "hero", id: "hero", "aria-labelledby": "hero-title" },
    plumbLine(),
    h("h1", { id: "hero-title", text: "Understand a repo before you read it." }),
    h("p", { class: "sub", text: "Paste a GitHub repo. Plumb maps what runs, how a request moves through the code and where to start, and links every sentence to the lines it came from." }),
    h("div", { class: "ask", id: "ask" }, form, examples.length ? h("div", { class: "examples" }, h("span", { text: "Try" }), examples) : null),
    h("div", { id: "answer", "aria-live": "polite" }),
  );
}

// "https://github.com/a/b.git", "github.com/a/b/tree/main", "a/b" -> "a/b"
export function parseRepo(text) {
  const cleaned = String(text).trim().replace(/^git@github\.com:/, "").replace(/^https?:\/\//, "").replace(/^(www\.)?github\.com\//, "");
  const match = cleaned.match(/^([A-Za-z0-9-]{1,39})\/([A-Za-z0-9._-]{1,100}?)(?:\.git)?(?:[/?#].*)?$/);
  return match ? `${match[1]}/${match[2]}` : null;
}

async function submit(text) {
  const ask = document.getElementById("ask");
  const answer = document.getElementById("answer");
  const repo = parseRepo(text);
  if (!repo) {
    ask.classList.remove("shake");
    void ask.offsetWidth;
    ask.classList.add("shake");
    answer.replaceChildren(h("div", { class: "notice reveal-in" }, "Paste a GitHub repo as ", h("code", { text: "owner/name" }), " or its full address, such as ", h("code", { text: "https://github.com/encode/httpx" }), "."));
    return;
  }
  const known = reports.find((r) => r.repo.toLowerCase() === repo.toLowerCase());
  if (known) return dropTo(`report.html?r=${encodeURIComponent(known.slug)}`);
  if (!API) return runLocally(answer, repo, `${repo} has not been analysed yet.`, " Analysing new repos here is being switched on. Until then you can run Plumb on your own machine with a free model:");
  const form = ask.querySelector("form");
  if (form.getAttribute("aria-busy") === "true") return;
  form.setAttribute("aria-busy", "true");
  try {
    const job = await startJob(repo);
    dropTo(`report.html?job=${encodeURIComponent(job.id)}`);
  } catch (error) {
    form.removeAttribute("aria-busy");
    if (error.status === 0) return runLocally(answer, repo, error.message, " You can also run Plumb on your own machine:");
    answer.replaceChildren(h("div", { class: "notice reveal-in" }, error.message));
  }
}

// The bob drops into the box, then the next page opens.
function dropTo(url) {
  if (reducedMotion()) return location.assign(url);
  document.getElementById("hero").classList.add("dropping");
  setTimeout(() => location.assign(url), 480);
}

function runLocally(answer, repo, title, text) {
  answer.replaceChildren(
    h(
      "div",
      { class: "notice reveal-in" },
      h("strong", { text: title }),
      text,
      h("pre", {}, h("code", { text: `git clone https://github.com/shivemn/Plumb\ncd Plumb/core && uv sync\nuv run plumb report ${repo} --model openrouter:<free-model>` })),
    ),
  );
}

// The placeholder types out repos that already have reports, until the box is used.
function typePlaceholder() {
  const input = document.getElementById("repo");
  const names = reports.map((r) => `github.com/${r.repo}`);
  if (!input || !names.length || reducedMotion()) return;
  let stopped = false;
  input.addEventListener("focus", () => {
    stopped = true;
    input.placeholder = "github.com/owner/name";
  });
  let n = 0;
  const show = async () => {
    while (!stopped) {
      const name = names[n++ % names.length];
      for (let i = 1; i <= name.length && !stopped; i++) {
        input.placeholder = name.slice(0, i);
        await wait(38);
      }
      await wait(1800);
      for (let i = name.length; i >= 11 && !stopped; i--) {
        input.placeholder = name.slice(0, i);
        await wait(18);
      }
    }
  };
  setTimeout(show, 900);
}

const wait = (ms) => new Promise((done) => setTimeout(done, ms));

function steps() {
  const list = h(
    "ol",
    { class: "steps" },
    step("Facts first, without AI", "Plumb reads the repo itself: Compose files, dependencies, routes, imports, calls and the history of every file."),
    step("A model explains the facts", "A model, free ones included, turns the facts into a short explanation and must cite a fact for every sentence."),
    step("Every sentence is checked", "A sentence naming a file, route, number or technology its facts do not contain is removed, and listed at the end."),
  );
  return h("section", { class: "band", "aria-labelledby": "how-title" }, h("h2", { id: "how-title", text: "How it works" }), list);
}

function step(title, text) {
  return h("li", {}, h("h3", { text: title }), h("p", { text }));
}

function recent() {
  const list = reports.length
    ? h(
        "ul",
        { class: "recent" },
        reports.map((r) =>
          h(
            "li",
            {},
            h(
              "a",
              {
                href: `report.html?r=${encodeURIComponent(r.slug)}`,
                onclick: (event) => {
                  // The repo name carries over into the report's title.
                  event.currentTarget.querySelector(".repo").style.viewTransitionName = "repo-title";
                },
              },
              h("span", { class: "repo", text: r.repo }),
              h("span", { class: "summary", text: (r.summary || "").replaceAll("`", "") }),
              h("span", { class: "meta", text: [r.kind, niceDate(r.written_at)].filter(Boolean).join(", ") }),
            ),
          ),
        ),
      )
    : h("p", { class: "note", text: "No reports yet." });
  const section = h(
    "section",
    { class: "band", id: "recent", "aria-labelledby": "recent-title" },
    h("h2", { id: "recent-title", text: "Recently explained" }),
    list,
    reports.length ? h("p", { class: "note", text: `Written by ${modelName(reports[0].model)}. Open one to see the sentences that were removed.` }) : null,
  );
  return section;
}

export { whenSeen };
