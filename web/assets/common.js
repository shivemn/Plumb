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

// The mark: a plumb line with its bob. `hero` is the large one that swings.
export function plumbMark(hero = false) {
  return svg(
    `<g class="${hero ? "plumb-swing" : ""}"><line class="plumb-string" x1="20" y1="0" x2="20" y2="103"/>` +
      '<path class="plumb-bob" d="M20 99 29 111 20 129 11 111Z"/></g>',
    { class: hero ? "plumb-mark" : "plumb-mark-small", viewBox: "0 0 40 132", "aria-hidden": "true" },
  );
}

export function brand() {
  return h("a", { class: "brand", href: "./", "aria-label": "Plumb home" }, plumbMark(), h("span", { text: "Plumb" }));
}

export function header() {
  // On the home page the links scroll; elsewhere they lead back to it.
  const home = /\/(index\.html)?$/.test(location.pathname) ? "" : "./";
  return h(
    "header",
    { class: "site-header page-wrap" },
    brand(),
    h(
      "nav",
      { class: "nav-links", "aria-label": "Main navigation" },
      h("a", { href: `${home}#preview`, text: "See a report" }),
      h("a", { href: `${home}#how`, text: "How it works" }),
      h("a", { href: `${home}#recent`, text: "Recent" }),
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
    { class: "theme-toggle", type: "button" },
    svg('<circle cx="12" cy="12" r="3.5"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/>', { viewBox: "0 0 24 24", "aria-hidden": "true" }),
  );
  const label = () => button.setAttribute("aria-label", currentTheme() === "dark" ? "Switch to light theme" : "Switch to dark theme");
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
    {},
    h(
      "div",
      { class: "page-wrap footer-inner" },
      h("div", { class: "brand" }, plumbMark(), h("span", { text: "Plumb" })),
      h("p", { text: "Know where to look before you start reading." }),
      h(
        "div",
        {},
        h("a", { href: "https://github.com/shivemn/Plumb", text: "GitHub" }),
        h("a", { href: "https://github.com/shivemn/Plumb/blob/main/docs/design.md", text: "Method" }),
        h("a", { href: "privacy.html", text: "Privacy" }),
      ),
    ),
  );
}

// The page frame: header, the page's own content, and the footer.
export function shell(...content) {
  return h("div", { class: "site-shell" }, header(), ...content, footer());
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
