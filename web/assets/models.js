// A visitor's own model, called straight from their browser. The key goes to
// the provider and nowhere else: Plumb's server only ever sees the answers.

export const PROVIDERS = {
  openrouter: {
    label: "OpenRouter",
    keyPage: "https://openrouter.ai/keys",
    keyShape: "sk-or-…",
    model: "nvidia/nemotron-3-ultra-550b-a55b:free",
    note: "Free models cost nothing. OpenRouter allows 50 free requests a day on a new account.",
  },
  anthropic: {
    label: "Anthropic",
    keyPage: "https://console.anthropic.com/settings/keys",
    keyShape: "sk-ant-…",
    model: "claude-opus-5-5",
    note: "Billed to your Anthropic account at its usual rates.",
  },
};

export class ModelError extends Error {}

// OpenRouter's free models, largest context first. Empty if the list cannot be read.
export async function freeModels() {
  try {
    const response = await fetch("https://openrouter.ai/api/v1/models");
    const { data } = await response.json();
    return data
      .filter((m) => typeof m.id === "string" && m.id.endsWith(":free"))
      .sort((a, b) => (b.context_length || 0) - (a.context_length || 0))
      .map((m) => ({ id: m.id, name: m.name || m.id }));
  } catch {
    return [];
  }
}

async function send(url, headers, body) {
  let response;
  try {
    response = await fetch(url, { method: "POST", headers: { "content-type": "application/json", ...headers }, body: JSON.stringify(body) });
  } catch {
    throw new ModelError("The model provider could not be reached from this browser.");
  }
  if (response.ok) return response.json();
  const text = (await response.text().catch(() => "")).slice(0, 200);
  const why = {
    401: "The provider did not accept this key.",
    402: "The provider says this account has no credit left.",
    403: "The provider refused this key for this model.",
    404: "The provider does not know this model. Pick another.",
    429: "The provider's limit was reached. Wait a while, or pick another model.",
  }[response.status];
  throw new ModelError(why || `The provider answered ${response.status}: ${text}`);
}

export async function complete(provider, model, key, system, prompt, maxTokens = 2000) {
  if (provider === "anthropic") {
    const data = await send(
      "https://api.anthropic.com/v1/messages",
      { "x-api-key": key, "anthropic-version": "2023-06-01", "anthropic-dangerous-direct-browser-access": "true" },
      { model, max_tokens: maxTokens, system, messages: [{ role: "user", content: prompt }] },
    );
    return (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
  }
  const data = await send(
    "https://openrouter.ai/api/v1/chat/completions",
    { authorization: `Bearer ${key}`, "x-title": "Plumb" },
    { model, max_tokens: maxTokens, messages: [{ role: "system", content: system }, { role: "user", content: prompt }] },
  );
  if (!data.choices?.length) throw new ModelError("The model returned no answer.");
  return data.choices[0].message?.content || "";
}

// The same test the server applies: a JSON object with a list of claims.
export function readable(text) {
  const cleaned = String(text).replace(/```(?:json)?/g, "");
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end < start) return false;
  try {
    return Array.isArray(JSON.parse(cleaned.slice(start, end + 1)).claims);
  } catch {
    return false;
  }
}
