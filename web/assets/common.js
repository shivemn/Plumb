// Shared helpers for the gallery and the report page.
// Everything from a report is set as text, never as HTML: claims were
// written by a model, so they are treated as untrusted.

export function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    // Through the style object, which the content security policy allows; a
    // style attribute in markup would be blocked.
    else if (key === "style") node.style.cssText = value;
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
  // entry → entries, but day → days
  const regular = /[^aeiou]y$/.test(noun) ? `${noun.slice(0, -1)}ies` : /(s|x|ch|sh)$/.test(noun) ? `${noun}es` : `${noun}s`;
  return `${count.toLocaleString("en")} ${count === 1 ? noun : many || regular}`;
}

const NS = "http://www.w3.org/2000/svg";

export function svg(markup, attrs = {}) {
  const node = document.createElementNS(NS, "svg");
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  node.innerHTML = markup;
  return node;
}

export function bobShape() {
  return svg('<path d="M6.5 0 L13 7 L6.5 17 L0 7 Z"/>', { width: "13", height: "17", viewBox: "0 0 13 17", "aria-hidden": "true" });
}

// The mark: a plumb line, with a branch that leaves it and merges back
// before the bob, on a tile.
export function mark(size = 28) {
  return svg(
    '<rect x="1" y="1" width="46" height="46" rx="12" fill="var(--mark-tile)" stroke="var(--mark-edge)" stroke-width="1.5"/><path d="M10 24h28" stroke="#e6ede9" stroke-opacity="0.32" stroke-width="2.6" stroke-linecap="round"/><path d="M21 1.75V29" stroke="#e6ede9" stroke-width="2.6" stroke-linecap="round"/><path d="M21 8c0 5.5 9 4.5 9 9.5s-9 5.5-9 10.5" fill="none" stroke="#e6ede9" stroke-width="2.4" stroke-linecap="round"/><circle cx="30" cy="17" r="3" fill="#e6ede9"/><path d="M21 28.5l5.5 6.5L21 43l-5.5-8z" fill="#d4a72c"/>',
    { width: String(size), height: String(size), viewBox: "0 0 48 48", "aria-hidden": "true" },
  );
}

export function brand() {
  return h("a", { class: "brand", href: "./" }, mark(), "Plumb");
}

export function header() {
  return h(
    "header",
    { class: "site-header" },
    brand(),
    h(
      "nav",
      { class: "site-nav", "aria-label": "Site" },
      h("a", { href: "./#recent", text: "Reports" }),
      h("a", { href: "https://github.com/shivemn/Plumb", text: "GitHub" }),
      themeSwitch(),
    ),
  );
}

// Light or dark. The choice is kept in this browser; until one is made, the
// page follows the system setting.
function currentTheme() {
  const chosen = document.documentElement.dataset.theme;
  if (chosen) return chosen;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function themeSwitch() {
  const button = h(
    "button",
    { class: "theme-switch", type: "button" },
    svg('<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor"/>', { viewBox: "0 0 24 24", "aria-hidden": "true" }),
  );
  const label = () => button.setAttribute("aria-label", currentTheme() === "dark" ? "Switch to light mode" : "Switch to dark mode");
  label();
  button.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    const apply = () => {
      document.documentElement.dataset.theme = next;
      label();
    };
    try {
      localStorage.setItem("plumb:theme", next);
    } catch {
      /* kept for this page only */
    }
    if (!document.startViewTransition || reducedMotion()) return apply();
    // The new theme opens as a circle from the switch.
    const box = button.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    document.documentElement.classList.add("theming");
    const transition = document.startViewTransition(apply);
    transition.ready
      .then(() =>
        document.documentElement.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 520, easing: "cubic-bezier(0.22, 1, 0.36, 1)", pseudoElement: "::view-transition-new(root)" },
        ),
      )
      .catch(() => {});
    transition.finished.finally(() => document.documentElement.classList.remove("theming"));
  });
  return button;
}

export function footer() {
  return h(
    "footer",
    { class: "site-footer" },
    h("span", { text: "Plumb explains a repo from its code, and every sentence links to the lines it came from." }),
    h("a", { href: "https://github.com/shivemn/Plumb", text: "Source" }),
    h("a", { href: "https://github.com/shivemn/Plumb/blob/main/docs/design.md", text: "How sentences are checked" }),
    h("a", { href: "privacy.html", text: "Privacy" }),
  );
}

// Run `onEnter` once when the node scrolls into view (at once if motion is reduced).
export function whenSeen(node, onEnter, margin = "0px 0px -15% 0px") {
  if (!("IntersectionObserver" in window)) return onEnter(node);
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          observer.disconnect();
          onEnter(node);
        }
      }
    },
    { rootMargin: margin },
  );
  observer.observe(node);
}

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// A path that may break after each slash, never inside a name.
export function pathText(path) {
  const parts = String(path).split("/");
  return parts.flatMap((part, i) => (i < parts.length - 1 ? [`${part}/`, document.createElement("wbr")] : [part]));
}
