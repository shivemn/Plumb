// A repo being explained on Plumb's server: report.html?job=<id>.
// The page follows the job down a plumb line, one step at a time. When it is
// done it shows the report, or, if the server did not write one, the
// diagrams and tables with a panel to write the explanation with the
// visitor's own key.
import { ApiError, checkAnswers, getHealth, getJob, getJobPart, startJob } from "./api.js";
import { bobShape, footer, h, header, plural } from "./common.js";
import { complete, isFree, ModelError, openRouterModels, PROVIDERS, readable } from "./models.js";
import { render, show } from "./report.js";

const root = document.getElementById("app");

const STAGES = [
  "Waiting in line",
  "Fetching the repo",
  "Reading files and history",
  "Finding services, routes and imports",
  "Tracing requests through the code",
  "Reading issues and pull requests",
];

export async function showJob(id) {
  const title = h("h1", { text: "Explaining a repo" });
  const line = plumbLine(STAGES);
  const message = h("div", { "aria-live": "polite" });
  root.replaceChildren(
    h(
      "div",
      { class: "wrap" },
      header(),
      h("section", { class: "report-top" }, title, h("p", { class: "commit", text: "Plumb is reading the code. This usually takes under a minute." })),
      h("main", { class: "job" }, line.node, message),
      footer(),
    ),
  );

  let job;
  let misses = 0;
  for (;;) {
    try {
      job = await getJob(id);
      misses = 0;
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return failed(message, "This job is not on the server. It may have been cleared; start it again from the home page.");
      if (++misses > 5) return failed(message, error.message);
      await wait(1500 * misses);
      continue;
    }
    title.textContent = job.repo;
    document.title = `${job.repo} · Plumb`;
    if (job.status === "failed") {
      line.stop();
      return failed(message, job.error || "The analysis stopped.", job.repo);
    }
    if (job.status === "done") break;
    if (job.status === "queued") line.at(0, job.queue_position > 1 ? `${job.queue_position} repos in line` : "");
    else line.at(stageIndex(line, job.stage));
    await wait(1200);
  }
  line.at(line.size);
  await wait(300);
  if (job.report_url) {
    const report = await getJobPart(id, "report");
    return show(root, render(report, { download: jsonDownload(report) }));
  }
  const saved = load(`plumb:written:${id}`);
  if (saved) return show(root, render(saved, { download: jsonDownload(saved) }));
  const [facts, views] = await Promise.all([getJobPart(id, "facts"), getJobPart(id, "views").catch(() => null)]);
  const bare = { repo: facts.repo, kind: facts.kind, model: null, sections: [], removed: [], facts: [], views };
  show(root, render(bare, { lead: writer(id, job.note) }));
}

function stageIndex(line, stage) {
  if (!stage) return 1;
  const i = line.stages.indexOf(stage);
  return i === -1 ? line.add(stage) : i;
}

function failed(into, text, repo) {
  const again = repo
    ? h("button", {
        class: "pill",
        type: "button",
        text: "Try again",
        onclick: async () => {
          try {
            const job = await startJob(repo);
            location.replace(`report.html?job=${encodeURIComponent(job.id)}`);
          } catch (error) {
            into.replaceChildren(notice(error.message));
          }
        },
      })
    : null;
  into.replaceChildren(notice(text, again, h("a", { class: "pill", href: "./", text: "Explain another repo" })));
}

function notice(text, ...actions) {
  return h("div", { class: "notice reveal-in" }, h("p", { text }), actions.some(Boolean) ? h("div", { class: "actions" }, actions) : null);
}

// A vertical string with one step per line; the bob drops to the step under way.
function plumbLine(stages) {
  const list = h("ol", { class: "line" });
  const bob = h("span", { class: "bob", "aria-hidden": "true" }, bobShape());
  const node = h("div", { class: "line-wrap" }, bob, list);
  const state = {
    node,
    stages: [...stages],
    get size() {
      return this.stages.length;
    },
    add(stage) {
      this.stages.push(stage);
      list.append(item(stage));
      return this.stages.length - 1;
    },
    at(index, detail = "") {
      [...list.children].forEach((li, i) => {
        li.className = i < index ? "done" : i === index ? "now" : "later";
        li.setAttribute("aria-current", i === index ? "step" : "false");
        li.querySelector(".detail").textContent = i === index ? detail : "";
      });
      const target = list.children[Math.min(index, list.children.length - 1)];
      if (target) bob.style.transform = `translateY(${target.offsetTop + 11}px)`;
      node.classList.toggle("finished", index >= this.stages.length);
    },
    stop() {
      node.classList.add("stopped");
    },
  };
  const item = (stage) => h("li", { class: "later" }, h("span", { class: "label", text: stage }), h("span", { class: "detail" }));
  stages.forEach((s) => list.append(item(s)));
  return state;
}

// The panel that writes the explanation with the visitor's own key.
function writer(id, note) {
  const remembered = load("plumb:writer") || {};
  let provider = PROVIDERS[remembered.provider] ? remembered.provider : "openrouter";
  let tasks = null;
  const answers = new Map();

  const why = h(
    "p",
    { class: "lead-text" },
    "The diagrams and tables below come straight from the code. A model can add a short explanation, with every sentence checked against the facts. Use your own key: it goes from this browser to the model provider and never to Plumb's server. ",
    h("a", { href: "privacy.html", text: "More on privacy" }),
  );
  const modelBox = h("div", { class: "field" });
  const key = h("input", { id: "key", type: "password", autocomplete: "off", spellcheck: "false" });
  const keyLink = h("a", { target: "_blank", rel: "noopener" });
  const remember = h("input", { id: "remember", type: "checkbox" });
  const estimate = h("p", { class: "note" });
  const go = h("button", { class: "pill primary", type: "submit", text: "Write the explanation" });
  const progress = h("div", { class: "writing" });
  const error = h("div", { "aria-live": "polite" });

  const pick = (name) => {
    provider = name;
    const p = PROVIDERS[name];
    key.placeholder = p.keyShape;
    key.value = loadText(`plumb:key:${name}`) || "";
    remember.checked = Boolean(key.value);
    keyLink.href = p.keyPage;
    keyLink.textContent = "Get a key";
    const input = h("input", {
      id: "model",
      type: "text",
      list: "model-list",
      autocomplete: "off",
      spellcheck: "false",
      value: remembered.provider === name && remembered.model ? remembered.model : p.model,
      oninput: sayEstimate,
    });
    modelBox.replaceChildren(h("label", { for: "model", text: "Model" }), input, h("datalist", { id: "model-list" }), h("p", { class: "hint", text: p.hint }));
    if (name === "openrouter") suggestModels(modelBox);
    sayEstimate();
  };
  const sayEstimate = () => {
    if (!tasks) return;
    const tokens = tasks.tasks.reduce((n, t) => n + t.estimated_tokens, 0);
    const model = modelBox.querySelector("#model")?.value.trim() || "";
    const cost = isFree(provider, model) ? "This model is free." : provider === "openrouter" ? "This model is billed to your OpenRouter account at its rates." : PROVIDERS[provider].note;
    estimate.textContent = `${plural(tasks.tasks.length, "request")}, about ${Math.round(tokens / 1000)}k input tokens in all. ${cost}`;
  };

  const choices = h(
    "div",
    { class: "choices", role: "radiogroup", "aria-label": "Model provider" },
    Object.entries(PROVIDERS).map(([name, p]) =>
      h("label", {}, h("input", { type: "radio", name: "provider", value: name, checked: name === provider, onchange: () => pick(name) }), h("span", { text: p.label })),
    ),
  );

  const form = h(
    "form",
    {
      class: "write-form",
      onsubmit: async (event) => {
        event.preventDefault();
        const model = modelBox.querySelector("#model").value.trim();
        if (!key.value.trim() || !model) {
          error.replaceChildren(notice("Add a key and a model first."));
          return;
        }
        save("plumb:writer", { provider, model });
        if (remember.checked) saveText(`plumb:key:${provider}`, key.value.trim());
        else removeKey(`plumb:key:${provider}`);
        go.disabled = true;
        error.replaceChildren();
        try {
          await write(id, tasks, answers, { provider, model, key: key.value.trim() }, progress);
        } catch (failure) {
          const text = failure instanceof ModelError || failure instanceof ApiError ? failure.message : "Something went wrong while writing.";
          const done = answers.size;
          error.replaceChildren(notice(done ? `${text} ${plural(done, "section")} already written are kept; the button carries on from there.` : text));
          go.disabled = false;
          go.textContent = "Carry on writing";
        }
      },
    },
    choices,
    modelBox,
    h("div", { class: "field" }, h("label", { for: "key", text: "Key" }), key, keyLink),
    h("label", { class: "check" }, remember, " Remember this key in this browser"),
    estimate,
    go,
  );

  const panel = h("section", { class: "writer reveal-in", "aria-labelledby": "writer-h" }, h("h2", { id: "writer-h", text: "Write the explanation" }), why, form, progress, error);
  pick(provider);

  getJobPart(id, "tasks")
    .then((t) => {
      tasks = t;
      sayEstimate();
    })
    .catch((failure) => {
      go.disabled = true;
      error.replaceChildren(notice(failure.message));
    });
  if (note) {
    // The server's own model tried and failed; say so, with its reason tucked away.
    why.prepend("Plumb's free model could not write this one just now. ");
    why.after(h("details", { class: "why-not" }, h("summary", { text: "What went wrong" }), h("p", { text: note })));
  } else {
    getHealth()
      .then((health) => {
        if (health.server_model && health.server_reports_left_today === 0) why.prepend("Plumb's free reports for today have been used. ");
      })
      .catch(() => {});
  }
  return panel;
}

async function suggestModels(box) {
  const models = await openRouterModels();
  const list = box.querySelector("datalist");
  if (!models.length || !list || !box.isConnected) return;
  list.replaceChildren(...models.map((m) => h("option", { value: m.id, label: m.free ? `${m.name.replace(/\s*\(free\)$/i, "")} · free` : m.name })));
}

async function write(id, tasks, answers, chosen, into) {
  const sections = tasks.tasks;
  const line = plumbLine([...sections.map((t) => t.title), "Checking every sentence"]);
  into.replaceChildren(line.node);
  into.scrollIntoView({ block: "nearest", behavior: "smooth" });
  const doneCount = () => sections.filter((t) => answers.has(t.section)).length;
  line.at(doneCount());
  // Two at a time: quick, and gentle on free models' per-minute limits.
  const queue = sections.filter((t) => !answers.has(t.section));
  const worker = async () => {
    for (let task = queue.shift(); task; task = queue.shift()) {
      let text = await complete(chosen.provider, chosen.model, chosen.key, task.system, task.prompt);
      if (!readable(text)) text = await complete(chosen.provider, chosen.model, chosen.key, task.system, task.prompt);
      answers.set(task.section, text);
      line.at(doneCount());
    }
  };
  await Promise.all([worker(), worker()]);
  line.at(sections.length);
  const report = await checkAnswers(id, {
    model: `${chosen.provider}:${chosen.model}`,
    nonce: tasks.nonce,
    answers: sections.map((t) => ({ section: t.section, text: answers.get(t.section) || "" })),
  });
  line.at(sections.length + 1);
  save(`plumb:written:${id}`, report, sessionStorage);
  await wait(300);
  show(root, render(report, { download: jsonDownload(report) }));
  window.scrollTo({ top: 0 });
}

function jsonDownload(report) {
  const blob = new Blob([JSON.stringify(report, null, 1)], { type: "application/json" });
  return { href: URL.createObjectURL(blob), name: `${report.repo.name}-plumb.json`, text: "Download JSON" };
}

const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// Browser storage may be missing or full; nothing here depends on it.
function load(name, store = name.startsWith("plumb:written:") ? sessionStorage : localStorage) {
  try {
    return JSON.parse(store.getItem(name) || "null");
  } catch {
    return null;
  }
}
function save(name, value, store = localStorage) {
  try {
    store.setItem(name, JSON.stringify(value));
  } catch {
    /* not kept */
  }
}
function loadText(name) {
  try {
    return localStorage.getItem(name);
  } catch {
    return null;
  }
}
function saveText(name, value) {
  try {
    localStorage.setItem(name, value);
  } catch {
    /* not kept */
  }
}
function removeKey(name) {
  try {
    localStorage.removeItem(name);
  } catch {
    /* nothing to remove */
  }
}
