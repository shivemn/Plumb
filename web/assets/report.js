// The report page: reads reports/<owner>__<name>.json and draws it.
import {
  append,
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
} from "./common.js";

const ORDER = {
  service: ["overview", "system", "flow", "entry_points", "structure", "hot_spots", "contribute", "gaps"],
  library: ["overview", "api", "system", "structure", "hot_spots", "contribute", "gaps"],
  cli: ["overview", "entry_points", "system", "structure", "hot_spots", "contribute", "gaps"],
};
const DEFAULT_ORDER = ["overview", "system", "entry_points", "structure", "hot_spots", "contribute", "gaps"];

const TITLES = {
  overview: "Overview",
  system: "System design",
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
  root.replaceChildren(
    h("div", { class: "page" }, header("report"), h("p", { class: "status", text: "This report could not be loaded. " }, h("a", { href: "./", text: "Back to the gallery" }))),
  );
});

async function start() {
  const params = new URLSearchParams(location.search);
  const slug = (params.get("r") || params.get("repo") || "").replace("/", "__");
  if (!/^[\w.-]+__[\w.-]+$/.test(slug)) {
    location.replace("./");
    return;
  }
  const report = await getJSON(`reports/${slug}.json`);
  document.title = `${report.repo.owner}/${report.repo.name} · Plumb`;
  root.replaceChildren(render(report, slug));
  if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
}

function render(report, slug) {
  const ctx = {
    repo: report.repo,
    facts: new Map(report.facts.map((f) => [f.id, f])),
    views: report.views || { stats: [] },
    kind: report.kind,
  };
  const claimsBy = new Map(report.sections.map((s) => [s.id, s.claims]));
  const overview = claimsBy.get("overview") || [];
  const lede = overview[0];

  const sections = [];
  for (const id of ORDER[report.kind] || DEFAULT_ORDER) {
    const claims = id === "overview" ? overview.slice(1) : claimsBy.get(id) || [];
    const built = SECTION[id]?.(ctx, claims, report);
    if (built) sections.push({ id, title: titleFor(id, report.kind), node: built });
  }

  const kept = report.sections.reduce((n, s) => n + s.claims.length, 0);
  const removed = report.removed.filter((r) => r.text).length;

  return h(
    "div",
    { class: "page" },
    header("report"),
    h(
      "section",
      { class: "report-head", "aria-labelledby": "repo-title" },
      h("h1", { id: "repo-title", text: `${report.repo.owner}/${report.repo.name}` }),
      lede ? h("p", { class: "lede" }, rich(lede.text)) : null,
      h(
        "dl",
        { class: "stats" },
        ctx.views.stats.map((s) => stat(s.label, s.value)),
        report.written_at ? stat("Written", niceDate(report.written_at)) : null,
        stat("Written by", modelName(report.model)),
        h(
          "div",
          {},
          h("dt", { text: "Claims checked against the code" }),
          h("dd", { class: "checked" }, tick(), `${kept} of ${kept + removed} kept, ${removed} removed`),
        ),
      ),
    ),
    h(
      "div",
      { class: "report-body" },
      h(
        "nav",
        { class: "contents", "aria-label": "Contents" },
        h("div", { class: "label", text: "Contents" }),
        sections.map((s) => h("a", { href: `#${s.id}`, text: s.title })),
        h("a", { class: "button", href: `reports/${slug}.md`, download: `${report.repo.name}-plumb.md`, text: "Export as Markdown" }),
        h("a", { class: "button", href: githubFolder(report.repo, "").replace(/\/$/, ""), text: "Open on GitHub" }),
      ),
      h(
        "main",
        { class: "report", id: "main" },
        sections.map((s) => h("section", { class: "section", id: s.id, "aria-labelledby": `${s.id}-title` }, h("h2", { id: `${s.id}-title`, text: s.title }), s.node)),
      ),
    ),
    footer(),
  );
}

function titleFor(id, kind) {
  if (id === "system" && kind !== "service") return "What it is built on";
  if (id === "flow" && kind !== "service") return "How a call moves";
  return TITLES[id];
}

function stat(label, value) {
  return h("div", {}, h("dt", { text: label }), h("dd", { text: value }));
}

function tick() {
  const span = h("span", { "aria-hidden": "true" });
  span.innerHTML =
    '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10.5l4 4 8-9"/></svg>';
  return span;
}

// Each section returns a DocumentFragment, or null when it has nothing to show.
const SECTION = {
  overview(ctx, claims) {
    if (!claims.length) return null;
    return fragment(claimList(ctx, claims));
  },

  system(ctx, claims) {
    const view = ctx.views.system;
    if (!view && !claims.length) return null;
    const parts = [];
    if (view) {
      const services = view.parts.filter((p) => p.role === "service").length;
      const stores = view.parts.filter((p) => p.role === "store").length;
      const outside = view.parts.filter((p) => p.role === "outside").length;
      const said = [
        services ? `${plural(services, "service")} ${services === 1 ? "runs" : "run"} from this repo` : null,
        stores ? plural(stores, "database, cache or queue", "databases, caches or queues") : null,
        outside ? plural(outside, "outside service") : null,
      ].filter(Boolean);
      parts.push(
        h("p", { class: "intro", text: `${sentence(said)}. Every box and arrow was found in a file, listed under the diagram.` }),
        systemDiagram(ctx, view),
        legend([
          ["", "Runs from this repo"],
          ["store", "Database, cache or queue"],
          ["outside", "Outside this repo"],
        ]),
      );
      if (!view.links_known) {
        parts.push(h("p", { class: "note", text: "No file says which service uses which store, so no arrows are drawn between them." }));
      }
      parts.push(h("h3", { text: "Where each part was found" }), partsTable(ctx, view));
    }
    if (claims.length) parts.push(claimList(ctx, claims));
    return fragment(parts);
  },

  flow(ctx, claims) {
    const flows = ctx.views.flows || [];
    if (!flows.length && !claims.length) return null;
    const parts = [];
    if (ctx.views.flows_traced) {
      parts.push(
        h("p", {
          class: "intro",
          text: `${plural(ctx.views.flows_traced, "route")} traced from the handler through the repo's own code. ${flows.length > 1 ? `${flows.length} of them` : "One"} shown here.`,
        }),
      );
    }
    if (claims.length) parts.push(claimList(ctx, claims));
    if (flows.length) parts.push(h("div", { class: "traces" }, flows.map((f) => trace(ctx, f))));
    parts.push(h("p", { class: "note", text: "Calls are followed only where the imports or declared types say where they go. Calls made through plugins, dependency injection or reflection are left out." }));
    return fragment(parts);
  },

  api(ctx, claims) {
    const names = ctx.views.api || [];
    if (!names.length && !claims.length) return null;
    const parts = [];
    if (names.length) {
      parts.push(
        h("p", { class: "intro" }, `The names code outside the library can use${ctx.views.api_root ? ", made public in " : "."}`, ctx.views.api_root ? [h("code", { text: ctx.views.api_root }), "."] : null),
      );
    }
    if (claims.length) parts.push(claimList(ctx, claims));
    if (names.length) parts.push(collapse(["Name", "Kind", "What it does", "Defined in"], apiRows(ctx, names), 12, "public names"));
    return fragment(parts);
  },

  entry_points(ctx, claims) {
    const routes = ctx.views.routes || [];
    if (!routes.length && !claims.length) return null;
    const parts = [];
    if (claims.length) parts.push(claimList(ctx, claims));
    if (routes.length) parts.push(collapse(["Kind", "Name", "Where"], routeRows(ctx, routes), 10, "ways in"));
    return fragment(parts);
  },

  structure(ctx, claims) {
    const map = ctx.views.code_map;
    if (!map && !claims.length) return null;
    const parts = [];
    if (map) {
      parts.push(
        h("p", { class: "intro", text: "The code as folders. Folders higher up use folders lower down. Each block is a file, sized by its lines, and amber marks files that change often. Select a folder to see what it uses." }),
      );
      parts.push(...codeMap(ctx, map));
    }
    if (claims.length) parts.push(claimList(ctx, claims));
    return fragment(parts);
  },

  hot_spots(ctx, claims) {
    const spots = ctx.views.hot_spots || [];
    if (!spots.length && !claims.length) return null;
    const parts = [];
    if (spots.length) {
      parts.push(h("p", { class: "intro", text: `The files that changed most between ${ctx.views.window}. Files often changed in the same commit are listed beside them.` }));
      parts.push(hotTable(ctx, spots));
    }
    if (claims.length) parts.push(claimList(ctx, claims));
    return fragment(parts);
  },

  contribute(ctx, claims) {
    if (!claims.length) return null;
    return fragment(claimList(ctx, claims, true));
  },

  gaps(ctx, _claims, report) {
    const gaps = ctx.views.gaps || [];
    const removed = report.removed.filter((r) => r.text);
    if (!gaps.length && !removed.length) return null;
    const parts = [h("p", { class: "intro", text: "The repo does not answer these, so this report does not guess." })];
    if (gaps.length) {
      parts.push(h("ul", { class: "gaps" }, gaps.map((g) => h("li", {}, h("strong", { text: `${g.title}. ` }), g.detail))));
    }
    if (removed.length) {
      parts.push(
        h(
          "details",
          { class: "more" },
          h("summary", { text: `${plural(removed.length, "sentence")} the model wrote ${removed.length === 1 ? "was" : "were"} removed because the facts did not support ${removed.length === 1 ? "it" : "them"}` }),
          h("ul", { class: "gaps removed" }, removed.map((r) => h("li", {}, rich(r.text), h("span", { class: "why", text: `Removed: ${r.reason}` })))),
        ),
      );
    }
    return fragment(parts);
  },
};

function fragment(children) {
  return append(document.createDocumentFragment(), [children]);
}

function sentence(items) {
  if (!items.length) return "Parts of the system";
  const text = items.length === 1 ? items[0] : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
  return text[0].toUpperCase() + text.slice(1);
}

// Claims, each with its sources beside it.
function claimList(ctx, claims, numbered = false) {
  return h(
    "ol",
    { class: `claims${numbered ? " numbered" : ""}` },
    claims.map((claim) => h("li", { class: "claim" }, h("p", {}, rich(claim.text)), sources(ctx, claim.fact_ids))),
  );
}

function sources(ctx, factIds) {
  const seen = new Set();
  const items = [];
  for (const id of factIds) {
    const fact = ctx.facts.get(id);
    if (!fact) continue;
    for (const ev of fact.evidence) {
      const key = JSON.stringify(ev);
      if (seen.has(key)) continue;
      seen.add(key);
      items.push(evidenceLink(ctx, ev, fact.statement));
    }
  }
  const shown = items.slice(0, 4);
  return h(
    "div",
    { class: "sources", "aria-label": "Sources" },
    shown,
    items.length > shown.length ? h("span", { text: `and ${items.length - shown.length} more` }) : null,
  );
}

function evidenceLink(ctx, ev, statement) {
  if (ev.kind === "commit") {
    return h("div", {}, h("a", { href: githubCommit(ctx.repo, ev.sha), title: statement, text: `commit ${ev.sha.slice(0, 7)}` }));
  }
  if (ev.kind === "issue") {
    return h("div", {}, h("a", { href: githubIssue(ctx.repo, ev.number), title: statement, text: `#${ev.number}` }));
  }
  return h(
    "div",
    {},
    h("a", { href: githubFile(ctx.repo, ev.path, ev.start_line, ev.end_line), title: statement }, pathText(ev.path)),
    ev.start_line ? h("span", { class: "where", text: lines(ev.start_line, ev.end_line) }) : null,
  );
}

function placeLink(ctx, place, text) {
  return h("a", { href: githubFile(ctx.repo, place.path, place.line), class: "mono" }, text || pathText(place.path));
}

function where(ctx, place) {
  return [placeLink(ctx, place), place.line ? `, line ${place.line}` : ""];
}

// A table showing its first rows, with the rest behind "Show all".
function collapse(head, rows, limit, noun) {
  if (rows.length <= limit) return table(head, rows);
  return fragment([
    table(head, rows.slice(0, limit)),
    h("details", { class: "more" }, h("summary", { text: `Show all ${rows.length.toLocaleString("en")} ${noun}` }), table(head, rows.slice(limit))),
  ]);
}

function table(head, rows) {
  return h(
    "div",
    { class: "table-wrap" },
    h(
      "table",
      {},
      h("thead", {}, h("tr", {}, head.map((t) => h("th", { scope: "col", text: t })))),
      h("tbody", {}, rows),
    ),
  );
}

// System diagram: callers, services in the repo, then what they use.
function drawnLinks(view) {
  const containers = new Set(view.parts.filter((p) => p.role === "container").map((p) => p.name));
  return view.links.filter((l) => !containers.has(l.source) && !containers.has(l.target));
}

function systemDiagram(ctx, view) {
  const parts = view.parts.filter((p) => p.role !== "container");
  const links = drawnLinks(view);
  const services = parts.filter((p) => p.role === "service").map((p) => p.name);
  // A repo with no service of its own is drawn as one box named after the repo.
  for (const { source: name } of links) {
    if (name !== "Clients" && !view.parts.some((p) => p.name === name) && !services.includes(name)) services.push(name);
  }
  const callers = links.some((l) => l.source === "Clients") ? ["Clients"] : [];
  const used = parts.filter((p) => p.role !== "service");
  const columns = [callers, services, used.map((p) => p.name)];
  const roleOf = new Map(parts.map((p) => [p.name, p.role]));
  roleOf.set("Clients", "callers");

  const X = [24, 312, 664];
  const W = [184, 232, 224];
  const boxH = 76;
  const gap = 28;
  const top = 56;
  const tallest = Math.max(1, ...columns.map((c) => c.length));
  const height = top + tallest * (boxH + gap) + 8;
  const width = 912;
  const pos = new Map();
  columns.forEach((names, col) => {
    const offset = top + ((tallest - names.length) * (boxH + gap)) / 2;
    names.forEach((name, i) => pos.set(name, { x: X[col], y: offset + i * (boxH + gap), w: W[col], h: boxH }));
  });

  const canvas = h("div", { class: "canvas", style: `width:${width}px;height:${height}px` });
  const labels = ["Callers", "Runs from this repo", "Storage and outside services"];
  labels.forEach((text, col) => {
    if (columns[col].length) canvas.append(h("div", { class: "col-label", style: `left:${X[col]}px`, text }));
  });

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", "links");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("aria-hidden", "true");
  const marker = document.createElementNS(ns, "marker");
  marker.setAttribute("id", "arrow");
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "9");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "7");
  marker.setAttribute("markerHeight", "7");
  marker.setAttribute("orient", "auto-start-reverse");
  const tip = document.createElementNS(ns, "path");
  tip.setAttribute("d", "M0 0L10 5L0 10z");
  tip.setAttribute("style", "fill: var(--muted); stroke: none");
  marker.append(tip);
  const defs = document.createElementNS(ns, "defs");
  defs.append(marker);
  svg.append(defs);
  canvas.append(svg);

  const drawn = new Set();
  for (const link of links) {
    const a = pos.get(link.source);
    const b = pos.get(link.target);
    if (!a || !b || drawn.has(`${link.source}>${link.target}`)) continue;
    drawn.add(`${link.source}>${link.target}`);
    const x1 = a.x + a.w;
    const y1 = a.y + a.h / 2;
    const x2 = b.x - 4;
    const y2 = b.y + b.h / 2;
    const mid = (x1 + x2) / 2;
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", `M${x1} ${y1} C${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`);
    path.setAttribute("marker-end", "url(#arrow)");
    svg.append(path);
    if (link.label && (link.source === "Clients" || links.length <= 6)) {
      canvas.append(h("div", { class: "link-label", style: `left:${mid - 34}px;top:${(y1 + y2) / 2 - 18}px`, text: link.label }));
    }
  }

  const describe = { service: "runs from this repo", store: "database, cache or queue", outside: "outside service", monitoring: "monitoring", callers: "whatever calls the routes" };
  for (const [name, p] of pos) {
    const role = roleOf.get(name) || "service";
    canvas.append(
      h(
        "div",
        { class: `part ${role}`, style: `left:${p.x}px;top:${p.y}px;width:${p.w}px;height:${p.h}px` },
        h("span", {}, h("b", { text: name }), h("small", { text: describe[role] || "" })),
      ),
    );
  }
  const names = [...pos.keys()].join(", ");
  return h("div", { class: "diagram", role: "img", "aria-label": `System diagram: ${names}. The table below lists each part and where it was found.` }, canvas);
}

function partsTable(ctx, view) {
  const roles = { service: "Runs from this repo", store: "Database, cache or queue", outside: "Outside service", monitoring: "Monitoring", container: "Other container" };
  const rows = view.parts.map((p) =>
    h(
      "tr",
      {},
      h("td", { class: "name", text: p.name }),
      h("td", { text: roles[p.role] || p.role }),
      h("td", {}, p.places.slice(0, 2).map((pl, i) => [i ? h("br") : null, ...where(ctx, pl)])),
      h("td", {}, rich(p.detail)),
    ),
  );
  for (const link of drawnLinks(view)) {
    if (!link.place) continue;
    rows.push(
      h(
        "tr",
        {},
        h("td", { class: "name", text: `${link.source} to ${link.target}` }),
        h("td", { text: "Connection" }),
        h("td", {}, where(ctx, link.place)),
        h("td", { text: `${link.source} ${link.label} ${link.target}` }),
      ),
    );
  }
  return table(["Part", "What it is", "Found in", "What the file says"], rows);
}

// One traced request, as who calls whom.
function trace(ctx, flow) {
  const children = (index) => flow.steps.map((s, i) => ({ s, i })).filter(({ s }) => s.caller === index && !s.before);
  const reaches = (index) => flow.reaches.filter((r) => r.by === index);
  const item = (step, index, depth) =>
    h(
      "li",
      {},
      placeLink(ctx, step.place, step.name),
      step.before ? h("span", { class: "tag", text: " runs before the handler" }) : null,
      reaches(index).map((r) => h("div", { class: "reach" }, `reaches ${r.what}: `, placeLink(ctx, r.place, r.call))),
      depth < 4 && children(index).length ? h("ul", {}, children(index).map(({ s, i }) => item(s, i, depth + 1))) : null,
    );
  const before = flow.steps.map((s, i) => ({ s, i })).filter(({ s }) => s.before);
  return h(
    "article",
    { class: "trace" },
    h("h3", { text: flow.route }),
    h("ul", {}, before.map(({ s, i }) => item(s, i, 1)), item(flow.steps[0], 0, 0)),
  );
}

function apiRows(ctx, names) {
  return names.map((n) =>
      h(
        "tr",
        {},
        h("td", {}, h("code", { text: n.kind === "function" ? `${n.name}(${n.signature})` : n.name })),
        h("td", { text: n.kind }),
        h("td", {}, rich(n.summary || "")),
        h("td", {}, where(ctx, n.place)),
      ),
  );
}

function routeRows(ctx, routes) {
  return routes.map((r) =>
    h("tr", {}, h("td", { text: r.kind }), h("td", {}, h("code", { text: r.name }), r.framework ? h("span", { class: "tag", text: ` ${r.framework}` }) : null), h("td", {}, where(ctx, r.place))),
  );
}

function hotTable(ctx, spots) {
  const most = Math.max(...spots.map((s) => s.commits));
  return table(
    ["File", "Commits", "Authors", "Often changes with"],
    spots.map((s) =>
      h(
        "tr",
        {},
        h("td", {}, h("a", { href: githubFile(ctx.repo, s.path), class: "mono", text: s.path })),
        h("td", {}, h("span", { class: "bar" }, h("span", { style: `width:${Math.max(6, (s.commits / most) * 120)}px` }), String(s.commits))),
        h("td", { text: String(s.authors) }),
        h("td", { class: "mono" }, s.changes_with.join(", ") || "—"),
      ),
    ),
  );
}

// Code map: rows of folders, each folder a set of blocks, one per file.
function codeMap(ctx, map) {
  const all = map.rows.flat();
  const prefix = commonPrefix(all.map((f) => f.path));
  const label = (path) => (prefix && path.startsWith(prefix) ? path.slice(prefix.length) || path : path);
  const most = Math.max(1, ...all.flatMap((f) => f.blocks.map((b) => b.lines)));
  const status = h("p", { class: "note", "aria-live": "polite" });
  const buttons = new Map();

  const select = (folder) => {
    for (const [path, button] of buttons) {
      button.classList.toggle("selected", path === folder.path);
      button.classList.toggle("used", folder.uses.includes(path));
      button.setAttribute("aria-pressed", String(path === folder.path));
    }
    const uses = folder.uses.map(label);
    status.replaceChildren(
      "Selected: ",
      h("code", { text: label(folder.path) }),
      uses.length ? `. It uses ${uses.join(", ")}.` : ". It uses no other folder on the map.",
      " ",
      h("a", { href: githubFolder(ctx.repo, folder.path), text: "Open on GitHub" }),
    );
  };

  const rowNames = map.rows.length === 1 ? ["Folders"] : map.rows.map((_, i) => (i === 0 ? "Top" : i === map.rows.length - 1 ? "Used by the rows above" : "Middle"));
  const rows = map.rows.map((row, i) =>
    h(
      "div",
      { class: "map-row" },
      h("div", { class: "row-label", text: rowNames[i] }),
      h("div", { class: "row-folders" }, row.map((folder) => {
        const button = h(
          "button",
          { type: "button", class: "folder", style: `flex-grow:${Math.max(1, Math.round(Math.sqrt(folder.lines) / 10))}`, "aria-pressed": "false", onclick: () => select(folder) },
          h("span", { class: "folder-head" }, h("span", { class: "folder-name", text: label(folder.path) }), h("span", { class: "count", text: plural(folder.files, "file") })),
          h(
            "span",
            { class: "blocks", "aria-hidden": "true" },
            folder.blocks.map((b) =>
              h("span", {
                class: b.commits >= map.hot ? "hot" : b.commits >= map.warm ? "warm" : "",
                style: `width:${Math.round(10 + 110 * Math.sqrt(b.lines / most))}px`,
                title: `${b.path}: ${plural(b.lines, "line")}, changed in ${plural(b.commits, "commit")}`,
              }),
            ),
          ),
        );
        buttons.set(folder.path, button);
        return button;
      })),
    ),
  );

  const parts = [];
  if (prefix) parts.push(h("p", { class: "note" }, "Folders under ", h("code", { text: prefix.replace(/\/$/, "") }), "."));
  parts.push(
    h(
      "div",
      { class: "map" },
      rows,
      legend([
        ["file", "A file"],
        ["warm", `Changed in ${map.warm} to ${map.hot - 1} commits in 90 days`],
        ["hot", `Changed in ${map.hot} or more`],
        ["selected", "Selected"],
        ["used", "Used by the selection"],
      ]),
    ),
    status,
    h("p", { class: "note", text: `The map shows ${plural(map.shown_files, "source file")}. ${map.left_out}` }),
  );
  return parts;
}

function commonPrefix(paths) {
  if (paths.length < 2) return "";
  const split = paths.map((p) => p.split("/"));
  const first = split[0];
  let n = 0;
  while (n < first.length - 1 && split.every((s) => s.length > n + 1 && s[n] === first[n])) n += 1;
  return n ? `${first.slice(0, n).join("/")}/` : "";
}

function legend(items) {
  return h("div", { class: "legend" }, items.map(([cls, text]) => h("span", {}, h("i", { class: cls, "aria-hidden": "true" }), text)));
}
