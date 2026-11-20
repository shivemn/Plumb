// The report page: reads reports/<owner>__<name>.json and draws it, or, with
// ?job=<id>, follows a job on Plumb's server (see job.js).
// Short text first; diagrams, traces and tables carry the detail, and every
// sentence has a small count that opens the files behind it.
import {
  append,
  bobShape,
  footer,
  getJSON,
  githubCommit,
  githubFile,
  githubFolder,
  githubIssue,
  h,
  header,
  lines,
  modelName,
  niceDate,
  pathText,
  plural,
  rich,
  whenSeen,
} from "./common.js";

const ORDER = {
  service: ["system", "flow", "entry_points", "structure", "hot_spots", "contribute", "gaps"],
  library: ["api", "system", "structure", "hot_spots", "contribute", "gaps"],
  cli: ["entry_points", "system", "structure", "hot_spots", "contribute", "gaps"],
};
const DEFAULT_ORDER = ["system", "entry_points", "structure", "hot_spots", "contribute", "gaps"];
const TITLES = {
  system: "How it connects",
  flow: "How a request moves",
  api: "What it lets your code do",
  entry_points: "Ways in",
  structure: "Code map",
  hot_spots: "Hot spots",
  contribute: "How to contribute",
  gaps: "Not determined",
};

const root = document.getElementById("app");

start().catch((error) => {
  console.error(error);
  root.replaceChildren(h("div", { class: "wrap" }, header(), h("p", { class: "status" }, "This report could not be loaded. ", h("a", { href: "./", text: "Explain another repo" }))));
});

async function start() {
  const params = new URLSearchParams(location.search);
  if (params.get("job")) {
    const { showJob } = await import("./job.js");
    return showJob(params.get("job"));
  }
  const slug = (params.get("r") || params.get("repo") || "").replace("/", "__");
  if (!/^[\w.-]+__[\w.-]+$/.test(slug)) {
    location.replace("./");
    return;
  }
  const report = await getJSON(`reports/${slug}.json`);
  document.title = `${report.repo.owner}/${report.repo.name} · Plumb`;
  show(root, render(report, { download: { href: `reports/${slug}.md`, name: `${report.repo.name}-plumb.md`, text: "Download Markdown" } }));
}

// Put a rendered report on the page and wire up its moving parts.
export function show(into, node) {
  into.replaceChildren(node);
  wireSpine();
  wireSources();
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
}

// `options.download`: a link for the spine; `options.lead`: a node shown first,
// above the summary (the panel that writes a report not yet written).
export function render(report, options = {}) {
  const ctx = { repo: report.repo, facts: new Map(report.facts.map((f) => [f.id, f])), views: report.views || { stats: [] }, kind: report.kind };
  const claimsBy = new Map(report.sections.map((s) => [s.id, s.claims]));
  const sections = [];
  for (const id of ORDER[report.kind] || DEFAULT_ORDER) {
    const node = SECTION[id]?.(ctx, claimsBy.get(id) || [], report);
    if (node) sections.push({ id, title: titleFor(id, report.kind), node });
  }
  const kept = report.sections.reduce((n, s) => n + s.claims.length, 0);
  const removed = report.removed.filter((r) => r.text).length;
  const statsWanted = ["Language", "Lines of code", "Source files", "Authors in 90 days"];
  const stats = ctx.views.stats.filter((s) => statsWanted.includes(s.label));
  const overview = claimsBy.get("overview") || [];

  return h(
    "div",
    { class: "wrap" },
    header(),
    h(
      "section",
      { class: "report-top" },
      h("h1", { text: `${report.repo.owner}/${report.repo.name}` }),
      h(
        "p",
        { class: "commit" },
        "At commit ",
        h("a", { href: githubCommit(report.repo, report.repo.commit), class: "mono", text: report.repo.commit.slice(0, 7) }),
        report.model ? (report.written_at ? `, explained on ${niceDate(report.written_at)}` : "") : ". Not explained yet",
        report.model ? ` by ${modelName(report.model)}.` : ".",
      ),
    ),
    h(
      "div",
      { class: "layout" },
      h(
        "nav",
        { class: "spine", "aria-label": "Contents" },
        h("span", { class: "bob", "aria-hidden": "true" }, bobShape()),
        h("a", { href: "#top-summary", text: "In short" }),
        sections.map((s) => h("a", { href: `#${s.id}`, text: s.title })),
        h(
          "div",
          { class: "tools" },
          options.download ? h("a", { class: "pill", href: options.download.href, download: options.download.name, text: options.download.text }) : null,
          h("a", { class: "pill", href: `https://github.com/${report.repo.owner}/${report.repo.name}`, text: "Open on GitHub" }),
        ),
      ),
      h(
        "main",
        { class: "report", id: "main" },
        options.lead || null,
        h(
          "section",
          { id: "top-summary", "aria-label": "In short" },
          overview.length ? h("p", { class: "in-short" }, prose(ctx, overview)) : null,
          h(
            "dl",
            { class: "stats" },
            stats.map((s) => h("div", {}, h("dt", { text: s.label }), h("dd", { text: s.value }))),
            report.model ? h("div", { class: "checked" }, h("dt", { text: "Sentences checked" }), h("dd", { text: `${kept} kept, ${removed} removed` })) : null,
          ),
        ),
        sections.map((s) => h("section", { class: "section", id: s.id, "aria-labelledby": `${s.id}-h` }, h("h2", { id: `${s.id}-h`, text: s.title }), s.node)),
      ),
    ),
    footer(),
  );
}

function titleFor(id, kind) {
  if (id === "system" && kind !== "service") return "What it is built on";
  return TITLES[id];
}

// The bob slides along the contents to the section in view.
function wireSpine() {
  const spine = document.querySelector(".spine");
  const bob = spine?.querySelector(".bob");
  const links = [...(spine?.querySelectorAll("a[href^='#']") || [])];
  const targets = links.map((a) => document.getElementById(a.getAttribute("href").slice(1))).filter(Boolean);
  const mark = (id) => {
    for (const a of links) {
      const on = a.getAttribute("href") === `#${id}`;
      a.setAttribute("aria-current", on ? "true" : "false");
      if (on && bob) bob.style.transform = `translateY(${a.offsetTop + a.offsetHeight / 2 - 8}px)`;
      if (on && getComputedStyle(spine).display === "flex") a.scrollIntoView({ block: "nearest", inline: "center" });
    }
  };
  // The current section is the last one whose top has passed a third of the
  // way down the window. Short sections at the end may never get there, so
  // at the bottom of the page the last section is current.
  let current = "";
  let queued = false;
  const update = () => {
    queued = false;
    if (!targets.length) return;
    const line = innerHeight / 3;
    let id = targets[0].id;
    for (const t of targets) if (t.getBoundingClientRect().top <= line) id = t.id;
    const root = document.documentElement;
    if (root.scrollTop > 0 && root.scrollTop + innerHeight >= root.scrollHeight - 4) id = targets.at(-1).id;
    if (id !== current) {
      current = id;
      mark(id);
    }
  };
  const later = () => {
    if (!queued) {
      queued = true;
      requestAnimationFrame(update);
    }
  };
  addEventListener("scroll", later, { passive: true });
  addEventListener("resize", later);
  update();
}

// One source list open at a time; Escape or a click elsewhere closes it.
function wireSources() {
  document.addEventListener("toggle", (event) => {
    const opened = event.target;
    if (!(opened instanceof HTMLDetailsElement) || !opened.classList.contains("src") || !opened.open) return;
    for (const other of document.querySelectorAll("details.src[open]")) if (other !== opened) other.open = false;
  }, true);
  document.addEventListener("click", (event) => {
    if (!event.target.closest("details.src")) for (const d of document.querySelectorAll("details.src[open]")) d.open = false;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") for (const d of document.querySelectorAll("details.src[open]")) d.open = false;
  });
}

function fragment(children) {
  return append(document.createDocumentFragment(), [children]);
}

// Sentences run together as prose, each followed by its source count.
// Past `limit`, the rest wait behind "Read more".
function prose(ctx, claims, limit = 3) {
  const sentence = (c, i) => [i ? " " : "", rich(c.text), sources(ctx, c.fact_ids)];
  const shown = claims.slice(0, limit).map(sentence);
  const rest = claims.slice(limit);
  if (!rest.length) return shown;
  const more = h("button", {
    type: "button",
    class: "more-text",
    text: `Read ${plural(rest.length, "more sentence")}`,
    onclick: () => more.replaceWith(h("span", { class: "extra" }, rest.map((c, i) => sentence(c, i + 1)))),
  });
  return [shown, " ", more];
}

function sources(ctx, factIds) {
  const seen = new Set();
  const links = [];
  const said = [];
  for (const id of factIds) {
    const fact = ctx.facts.get(id);
    if (!fact) continue;
    said.push(fact.statement);
    for (const ev of fact.evidence) {
      const key = JSON.stringify(ev);
      if (seen.has(key)) continue;
      seen.add(key);
      links.push(evidenceLink(ctx, ev));
    }
  }
  if (!links.length) return null;
  return h(
    "details",
    { class: "src" },
    h("summary", { "aria-label": `${plural(links.length, "source")}`, text: String(links.length) }),
    h("div", { class: "pop", role: "group", "aria-label": "Sources" }, links.slice(0, 8), links.length > 8 ? h("span", { text: `and ${links.length - 8} more` }) : null, h("span", { class: "said", text: `From: ${said.join(" · ")}`.slice(0, 400) })),
  );
}

function evidenceLink(ctx, ev) {
  if (ev.kind === "commit") return h("a", { href: githubCommit(ctx.repo, ev.sha), text: `commit ${ev.sha.slice(0, 7)}` });
  if (ev.kind === "issue") return h("a", { href: githubIssue(ctx.repo, ev.number), text: `#${ev.number}` });
  return h("a", { href: githubFile(ctx.repo, ev.path, ev.start_line, ev.end_line) }, pathText(ev.path), ev.start_line ? h("span", { text: `  ${lines(ev.start_line, ev.end_line)}` }) : null);
}

function placeLink(ctx, place, text) {
  return h("a", { href: githubFile(ctx.repo, place.path, place.line) }, text || pathText(place.path));
}

function drawer(label, content) {
  return h("details", { class: "drawer" }, h("summary", { text: label }), h("div", { class: "inner" }, content));
}

function table(head, rows) {
  return h("table", {}, h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col", text: t })))), h("tbody", {}, rows));
}

const SECTION = {
  system(ctx, claims) {
    const view = ctx.views.system;
    const drawable = view && view.parts.some((p) => p.role !== "container");
    if (!drawable && !claims.length) return null;
    return fragment([
      claims.length ? h("p", { class: "prose" }, prose(ctx, claims)) : null,
      drawable ? systemFigure(ctx, view) : null,
    ]);
  },

  flow(ctx, claims) {
    const flows = ctx.views.flows || [];
    if (!flows.length && !claims.length) return null;
    const [first, ...rest] = flows;
    return fragment([
      claims.length ? h("p", { class: "prose" }, prose(ctx, claims)) : null,
      first ? trace(ctx, first) : null,
      rest.length ? drawer(`Show ${plural(rest.length, "more trace")}`, rest.map((f) => trace(ctx, f))) : null,
      ctx.views.flows_traced ? h("p", { class: "note", text: `${plural(ctx.views.flows_traced, "route")} traced. Calls are followed only where imports or declared types say where they go.` }) : null,
    ]);
  },

  api(ctx, claims) {
    const names = ctx.views.api || [];
    if (!names.length && !claims.length) return null;
    const rows = names.map((n) =>
      h("tr", {}, h("td", {}, h("code", { text: n.kind === "function" ? `${n.name}(${n.signature})` : n.name })), h("td", { class: "tag", text: n.kind }), h("td", {}, rich(n.summary || "")), h("td", {}, placeLink(ctx, n.place))),
    );
    return fragment([
      claims.length ? h("p", { class: "prose" }, prose(ctx, claims)) : null,
      names.length ? drawer(`All ${plural(names.length, "public name")}${ctx.views.api_root ? `, from ${ctx.views.api_root}` : ""}`, table(["Name", "Kind", "What it does", "Defined in"], rows)) : null,
    ]);
  },

  entry_points(ctx, claims) {
    const routes = ctx.views.routes || [];
    if (!routes.length && !claims.length) return null;
    const counts = new Map();
    for (const r of routes) counts.set(r.kind, (counts.get(r.kind) || 0) + 1);
    const label = [...counts].map(([k, n]) => plural(n, k.startsWith("HTTP") ? k : k.toLowerCase())).join(", ");
    const rows = routes.map((r) => h("tr", {}, h("td", {}, h("code", { text: r.name }), r.framework ? h("span", { class: "tag", text: `  ${r.framework}` }) : null), h("td", { class: "tag", text: r.kind }), h("td", {}, placeLink(ctx, r.place))));
    return fragment([
      claims.length ? h("p", { class: "prose" }, prose(ctx, claims)) : null,
      routes.length ? drawer(`All ${label}`, table(["Name", "Kind", "Where"], rows)) : null,
    ]);
  },

  structure(ctx, claims) {
    const map = ctx.views.code_map;
    if (!map && !claims.length) return null;
    return fragment([
      claims.length ? h("p", { class: "prose" }, prose(ctx, claims)) : null,
      map ? codeMap(ctx, map) : null,
    ]);
  },

  hot_spots(ctx, claims) {
    const spots = (ctx.views.hot_spots || []).slice(0, 5);
    if (!spots.length && !claims.length) return null;
    const most = Math.max(1, ...spots.map((s) => s.commits));
    const list = h(
      "ul",
      { class: "hot-list" },
      spots.map((s) =>
        h(
          "li",
          {},
          h("a", { href: githubFile(ctx.repo, s.path), title: s.changes_with.length ? `Often changes with ${s.changes_with.join(", ")}` : "" }, pathText(s.path)),
          h("span", { class: "bar", style: `width:${Math.max(6, (s.commits / most) * 100)}%` }),
          h("span", { class: "n", text: String(s.commits) }),
        ),
      ),
    );
    return fragment([
      claims.length ? h("p", { class: "prose" }, prose(ctx, claims)) : null,
      spots.length ? list : null,
      spots.length && ctx.views.window ? h("p", { class: "note", text: `Commits per file between ${ctx.views.window}.` }) : null,
    ]);
  },

  contribute(ctx, claims) {
    if (!claims.length) return null;
    return h("ol", { class: "steps-list" }, claims.slice(0, 5).map((c) => h("li", {}, rich(c.text), sources(ctx, c.fact_ids))));
  },

  gaps(ctx, _claims, report) {
    const gaps = ctx.views.gaps || [];
    const removed = report.removed.filter((r) => r.text);
    if (!gaps.length && !removed.length) return null;
    return fragment([
      gaps.length ? h("ul", { class: "gaps" }, gaps.map((g) => h("li", {}, h("strong", { text: `${g.title}. ` }), g.detail))) : null,
      removed.length
        ? drawer(
            `${plural(removed.length, "sentence")} removed because the facts did not support ${removed.length === 1 ? "it" : "them"}`,
            h("ul", { class: "gaps removed" }, removed.map((r) => h("li", {}, rich(r.text), h("span", { class: "why", text: r.reason })))),
          )
        : null,
    ]);
  },
};

// System diagram: callers, what runs from the repo, then what it uses.
function systemFigure(ctx, view) {
  const containers = new Set(view.parts.filter((p) => p.role === "container").map((p) => p.name));
  const links = view.links.filter((l) => !containers.has(l.source) && !containers.has(l.target));
  const parts = view.parts.filter((p) => p.role !== "container");
  const services = parts.filter((p) => p.role === "service").map((p) => p.name);
  for (const { source } of links) if (source !== "Clients" && !view.parts.some((p) => p.name === source) && !services.includes(source)) services.push(source);
  const callers = links.some((l) => l.source === "Clients") ? ["Clients"] : [];
  const columns = [callers, services, parts.filter((p) => p.role !== "service").map((p) => p.name)];
  const partBy = new Map(parts.map((p) => [p.name, p]));

  const X = [16, 262, 518];
  const W = [160, 210, 206];
  const boxH = 68;
  const gap = 22;
  const top = 50;
  const tallest = Math.max(1, ...columns.map((c) => c.length));
  const height = top + tallest * (boxH + gap) + 4;
  const width = 740;
  const pos = new Map();
  columns.forEach((names, col) => {
    const offset = top + ((tallest - names.length) * (boxH + gap)) / 2;
    names.forEach((name, i) => pos.set(name, { x: X[col], y: offset + i * (boxH + gap), w: W[col], h: boxH }));
  });

  const canvas = h("div", { class: "canvas", style: `width:${width}px;height:${height}px` });
  ["Callers", "Runs from this repo", "Data and outside services"].forEach((text, col) => {
    if (columns[col].length) canvas.append(h("div", { class: "col-label", style: `left:${X[col]}px`, text }));
  });
  const ns = "http://www.w3.org/2000/svg";
  const layer = document.createElementNS(ns, "svg");
  layer.setAttribute("class", "links");
  layer.setAttribute("width", String(width));
  layer.setAttribute("height", String(height));
  layer.setAttribute("aria-hidden", "true");
  layer.innerHTML = '<defs><marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="tip" d="M0 0L10 5L0 10z"/></marker></defs>';
  canvas.append(layer);

  const drawn = new Set();
  let index = 0;
  for (const link of links) {
    const a = pos.get(link.source);
    const b = pos.get(link.target);
    const key = `${link.source}>${link.target}`;
    if (!a || !b || drawn.has(key)) continue;
    drawn.add(key);
    const x1 = a.x + a.w;
    const y1 = a.y + a.h / 2;
    const x2 = b.x - 4;
    const y2 = b.y + b.h / 2;
    const mid = (x1 + x2) / 2;
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", `M${x1} ${y1} C${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`);
    path.setAttribute("marker-end", "url(#tip)");
    path.style.setProperty("--i", String(index++));
    layer.append(path);
    if (x2 - x1 >= 64 && (link.source === "Clients" || links.length <= 5)) canvas.append(h("div", { class: "link-label", style: `left:${mid - 30}px;top:${(y1 + y2) / 2 - 16}px`, text: link.label }));
  }

  const detail = h("div", { "aria-live": "polite" });
  const describe = { service: "runs from this repo", store: "stores data", outside: "outside service", monitoring: "monitoring", callers: "whatever calls the routes" };
  let i = 0;
  for (const [name, p] of pos) {
    const part = partBy.get(name);
    const role = name === "Clients" ? "callers" : part?.role || "service";
    const box = h(
      "button",
      {
        type: "button",
        class: `part ${role}`,
        style: `left:${p.x}px;top:${p.y}px;width:${p.w}px;height:${p.h}px;--i:${i++}`,
        "aria-pressed": "false",
        onclick: (event) => {
          for (const b of canvas.querySelectorAll(".part")) b.setAttribute("aria-pressed", "false");
          event.currentTarget.setAttribute("aria-pressed", "true");
          detail.replaceChildren(partDetail(ctx, name, part, links));
        },
      },
      h("span", {}, h("b", { text: name }), h("small", { text: describe[role] || "" })),
    );
    canvas.append(box);
  }
  const figure = h("div", { class: "diagram", role: "group", "aria-label": "System diagram. Select a part to see where it was found." }, canvas);
  queueMicrotask(() => {
    for (const path of layer.querySelectorAll("path[d]")) if (path.getTotalLength) path.style.setProperty("--len", String(Math.ceil(path.getTotalLength())));
    whenSeen(figure, () => figure.classList.add("drawn"));
  });
  return h(
    "div",
    { class: "figure" },
    figure,
    h("div", { class: "legend" }, h("span", {}, h("i"), "Runs from this repo"), h("span", {}, h("i", { class: "store" }), "Stores data"), h("span", {}, h("i", { class: "outside" }), "Outside this repo"), h("span", { text: "Select a part to see where it was found." })),
    view.links_known ? null : h("p", { class: "note", text: "No file says which service uses which store, so no arrows are drawn between them." }),
    detail,
  );
}

function partDetail(ctx, name, part, links) {
  const uses = links.filter((l) => l.source === name);
  if (!part) {
    return h("div", { class: "part-detail reveal-in" }, h("b", { text: name }), uses.length ? ` calls ${uses.map((l) => l.target).join(", ")}.` : "");
  }
  return h(
    "div",
    { class: "part-detail reveal-in" },
    h("b", { text: name }),
    `: ${part.detail}`,
    h("div", {}, part.places.map((pl, i) => [i ? ", " : "Found in ", placeLink(ctx, pl, `${pl.path}${pl.line ? `:${pl.line}` : ""}`)])),
  );
}

// One traced request as a call tree that unfolds when it comes into view.
function trace(ctx, flow) {
  let n = 0;
  const children = (index) => flow.steps.map((s, i) => ({ s, i })).filter(({ s }) => s.caller === index && !s.before);
  const item = (step, index, depth) =>
    h(
      "li",
      { style: `--i:${n++}` },
      placeLink(ctx, step.place, step.name),
      step.before ? h("span", { class: "tag", text: "  runs before the handler" }) : null,
      flow.reaches.filter((r) => r.by === index).map((r) => h("div", { class: "reach" }, `reaches ${r.what}: `, placeLink(ctx, r.place, r.call))),
      depth < 4 && children(index).length ? h("ul", {}, children(index).map(({ s, i }) => item(s, i, depth + 1))) : null,
    );
  const before = flow.steps.map((s, i) => ({ s, i })).filter(({ s }) => s.before);
  const node = h("article", { class: "trace" }, h("h3", { text: flow.route }), h("ul", {}, before.map(({ s, i }) => item(s, i, 1)), item(flow.steps[0], 0, 0)));
  whenSeen(node, () => node.classList.add("unfold"));
  return node;
}

// Code map: rows of folders, one block per file; select a folder to see what it uses.
function codeMap(ctx, map) {
  const all = map.rows.flat();
  const prefix = commonPrefix(all.map((f) => f.path));
  const label = (path) => (prefix && path.startsWith(prefix) ? path.slice(prefix.length) || path : path);
  const most = Math.max(1, ...all.flatMap((f) => f.blocks.map((b) => b.lines)));
  const status = h("p", { class: "note", "aria-live": "polite", text: "Select a folder to see which folders it uses." });
  const buttons = new Map();
  const box = h("div", { class: "map" });
  let selected = null;
  const select = (folder) => {
    selected = selected === folder.path ? null : folder.path;
    box.classList.toggle("focused", Boolean(selected));
    for (const [path, button] of buttons) {
      button.classList.toggle("selected", path === selected);
      button.classList.toggle("used", Boolean(selected) && folder.uses.includes(path));
      button.setAttribute("aria-pressed", String(path === selected));
    }
    if (!selected) return status.replaceChildren("Select a folder to see which folders it uses.");
    const uses = folder.uses.map(label);
    status.replaceChildren(h("code", { text: label(folder.path) }), uses.length ? ` uses ${uses.join(", ")}. ` : " uses no other folder on the map. ", h("a", { href: githubFolder(ctx.repo, folder.path), text: "Open the folder on GitHub" }));
  };
  const rowNames = map.rows.length === 1 ? [""] : map.rows.map((_, i) => (i === 0 ? "Uses below" : i === map.rows.length - 1 ? "Used above" : ""));
  let i = 0;
  for (const [r, row] of map.rows.entries()) {
    box.append(
      h(
        "div",
        { class: "map-row" },
        h("div", { class: "row-label", text: rowNames[r] }),
        h(
          "div",
          { class: "row-folders" },
          row.map((folder) => {
            const button = h(
              "button",
              { type: "button", class: "folder", style: `flex-grow:${Math.max(1, Math.round(Math.sqrt(folder.lines) / 12))}`, "aria-pressed": "false", onclick: () => select(folder) },
              h("span", { class: "folder-head" }, h("span", { class: "folder-name", text: label(folder.path) }), h("span", { class: "count", text: plural(folder.files, "file") })),
              h(
                "span",
                { class: "blocks", "aria-hidden": "true" },
                folder.blocks.map((b) => h("span", { class: b.commits >= map.hot ? "hot" : b.commits >= map.warm ? "warm" : "", style: `width:${Math.round(8 + 80 * Math.sqrt(b.lines / most))}px;--i:${i++}`, title: `${b.path}: ${plural(b.lines, "line")}, ${plural(b.commits, "commit")} in 90 days` })),
              ),
            );
            buttons.set(folder.path, button);
            return button;
          }),
        ),
      ),
    );
  }
  whenSeen(box, () => box.classList.add("grown"));
  return h(
    "div",
    { class: "figure" },
    prefix ? h("p", { class: "note", style: "margin:0 0 10px" }, "Folders under ", h("code", { text: prefix.replace(/\/$/, "") })) : null,
    box,
    h("div", { class: "legend" }, h("span", {}, h("i", { class: "file" }), "A file, sized by its lines"), h("span", {}, h("i", { class: "warm" }), `${map.warm} to ${map.hot - 1} commits in 90 days`), h("span", {}, h("i", { class: "hot" }), `${map.hot} or more`)),
    status,
  );
}

function commonPrefix(paths) {
  if (paths.length < 2) return "";
  const split = paths.map((p) => p.split("/"));
  let n = 0;
  while (n < split[0].length - 1 && split.every((s) => s.length > n + 1 && s[n] === split[0][n])) n += 1;
  return n ? `${split[0].slice(0, n).join("/")}/` : "";
}
