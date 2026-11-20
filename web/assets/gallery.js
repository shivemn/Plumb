// The gallery: reports/index.json as a list of cards.
import { footer, getJSON, h, header, modelName, niceDate } from "./common.js";

const root = document.getElementById("app");

start().catch((error) => {
  console.error(error);
  root.replaceChildren(page([h("p", { class: "status", text: "The list of reports could not be loaded." })]));
});

async function start() {
  let reports = [];
  try {
    reports = (await getJSON("reports/index.json")).reports || [];
  } catch {
    reports = [];
  }
  root.replaceChildren(
    page([
      h(
        "section",
        { class: "hero", "aria-labelledby": "hero-title" },
        h("h1", { id: "hero-title", text: "Understand a codebase before you read it." }),
        h("p", { text: "Plumb explains a GitHub repo: what runs, what it talks to, how a request moves through the code, which parts change most and how to start contributing. Every sentence links to the lines of code it came from." }),
      ),
      h(
        "section",
        { class: "how", "aria-label": "How it works" },
        step("Facts first, without AI", "Plumb reads the repo itself: Compose files, dependencies, routes, imports, and the history of every file."),
        step("A model writes from the facts", "The model sees only those facts, and must cite one for every sentence it writes."),
        step("Every sentence is checked", "Sentences naming a file, route, number or technology the cited facts do not contain are removed, and shown at the end."),
      ),
      h(
        "section",
        { class: "gallery", "aria-labelledby": "gallery-title" },
        h("h2", { id: "gallery-title", text: "Reports" }),
        reports.length
          ? h("ul", { class: "cards" }, reports.map(card))
          : h("p", { class: "note", text: "No reports yet. They are being written; check back soon." }),
      ),
      h(
        "section",
        { class: "try", id: "try", "aria-labelledby": "try-title" },
        h("h2", { id: "try-title", text: "Analyse your own repo" }),
        h("p", { text: "Submitting a repo here, with your own model key that never leaves your browser, is coming next. Until then, Plumb runs on your machine with a free model:" }),
        h("pre", {}, h("code", { text: "git clone https://github.com/shivemn/Plumb\ncd Plumb/core\nuv sync\nuv run plumb report owner/name --model openrouter:<free-model>" })),
      ),
    ]),
  );
}

function page(children) {
  return h("div", { class: "page" }, header("gallery"), h("main", {}, children), footer());
}

function step(title, text) {
  return h("div", {}, h("h2", { text: title }), h("p", { text }));
}

function card(entry) {
  const total = entry.kept + entry.removed;
  return h(
    "li",
    {},
    h(
      "a",
      { class: "card", href: `report.html?r=${encodeURIComponent(entry.slug)}` },
      h("span", { class: "repo", text: entry.repo }),
      h("span", {}, h("span", { class: "chip", text: entry.kind })),
      entry.summary ? h("p", { class: "summary", text: entry.summary.replaceAll("`", "") }) : null,
      h(
        "span",
        { class: "meta" },
        h("span", { text: `${entry.kept} of ${total} claims kept` }),
        entry.written_at ? h("span", { text: niceDate(entry.written_at) }) : null,
        h("span", { text: modelName(entry.model) }),
      ),
    ),
  );
}
