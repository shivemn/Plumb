// Shared helpers for the gallery and the report page.
// Everything from a report is set as text, never as HTML: claims were
// written by a model, so they are treated as untrusted.

export function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  append(node, children);
  return node;
}

export function append(node, children) {
  for (const child of children.flat(Infinity)) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// Text with `backticks` shown as code.
export function rich(text) {
  const parts = String(text).split(/(`[^`]+`)/g);
  return parts.map((part) =>
    part.length > 2 && part.startsWith("`") && part.endsWith("`") ? h("code", { text: part.slice(1, -1) }) : part,
  );
}

export async function getJSON(url) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.json();
}

export function githubFile(repo, path, start, end) {
  const base = `https://github.com/${repo.owner}/${repo.name}/blob/${repo.commit}/${encodePath(path)}`;
  if (!start) return base;
  return end && end !== start ? `${base}#L${start}-L${end}` : `${base}#L${start}`;
}

export function githubFolder(repo, path) {
  return `https://github.com/${repo.owner}/${repo.name}/tree/${repo.commit}/${encodePath(path)}`;
}

export function githubCommit(repo, sha) {
  return `https://github.com/${repo.owner}/${repo.name}/commit/${sha}`;
}

export function githubIssue(repo, number) {
  return `https://github.com/${repo.owner}/${repo.name}/issues/${number}`;
}

function encodePath(path) {
  return String(path).split("/").map(encodeURIComponent).join("/");
}

export function lines(start, end) {
  if (!start) return "";
  return end && end !== start ? `lines ${start} to ${end}` : `line ${start}`;
}

// "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free" -> "nemotron-3-ultra-550b-a55b (free, via OpenRouter)"
export function modelName(spec) {
  const [provider, ...rest] = String(spec).split(":");
  let model = rest.join(":");
  const free = model.endsWith(":free");
  if (free) model = model.slice(0, -5);
  const short = model.includes("/") ? model.split("/").pop() : model;
  const via = { openrouter: "OpenRouter", anthropic: "Anthropic", groq: "Groq", gemini: "Google", openai: "OpenAI", ollama: "Ollama" }[provider] || provider;
  const notes = [free ? "free" : null, `via ${via}`].filter(Boolean).join(", ");
  return `${short} (${notes})`;
}

export function niceDate(iso) {
  if (!iso) return "";
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function plural(count, noun, many) {
  return `${count.toLocaleString("en")} ${count === 1 ? noun : many || `${noun}s`}`;
}

export function brand() {
  return h(
    "a",
    { class: "brand", href: "./" },
    logo(),
    "Plumb",
  );
}

function logo() {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", "22");
  svg.setAttribute("height", "22");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML =
    '<path d="M12 2v9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>' +
    '<path d="M12 11l-5 9h10z" fill="currentColor"/>';
  return svg;
}

export function header(current) {
  return h(
    "header",
    { class: "site-header" },
    brand(),
    h(
      "nav",
      { class: "site-nav", "aria-label": "Site" },
      h("a", { href: "./", "aria-current": current === "gallery" ? "page" : null, text: "Gallery" }),
      h("a", { href: "./#try", text: "Analyse a repo" }),
      h("a", { href: "https://github.com/shivemn/Plumb", text: "GitHub" }),
    ),
  );
}

export function footer() {
  return h(
    "footer",
    { class: "site-footer" },
    h("span", { text: "Plumb explains a repo from its code. Every claim links to the lines it came from." }),
    h("a", { href: "https://github.com/shivemn/Plumb", text: "Source on GitHub" }),
    h("a", { href: "https://github.com/shivemn/Plumb/blob/main/docs/design.md", text: "How claims are checked" }),
  );
}

// A path that may break after each slash, never inside a name.
export function pathText(path) {
  const parts = String(path).split("/");
  return parts.flatMap((part, i) => (i < parts.length - 1 ? [`${part}/`, document.createElement("wbr")] : [part]));
}
