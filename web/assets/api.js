// Calls to Plumb's own server. Errors carry a sentence a visitor can act on.
import { API } from "./config.js";

export class ApiError extends Error {
  // `waking`: the server did not answer as itself, which on a free host
  // usually means it is starting after a sleep. Worth trying again shortly.
  constructor(message, status, waking = false) {
    super(message);
    this.status = status;
    this.waking = waking;
  }
}

const ASLEEP = "Plumb's server could not be reached. Check your connection, then try again.";

async function call(path, init = {}) {
  let response;
  try {
    response = await fetch(API + path, init);
  } catch {
    throw new ApiError(ASLEEP, 0, true);
  }
  let body;
  try {
    body = await response.json();
  } catch {
    // A host's own page (a gateway error, or a "starting up" screen), not Plumb.
    throw new ApiError(ASLEEP, response.status, true);
  }
  if (!response.ok) {
    const detail = body?.detail;
    const text = typeof detail === "string" && detail ? detail : `The server answered ${response.status}.`;
    throw new ApiError(text.charAt(0).toUpperCase() + text.slice(1).replace(/([^.])$/, "$1."), response.status);
  }
  return body;
}

const post = (path, body) => call(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
const job = (id) => `/api/jobs/${encodeURIComponent(id)}`;

export const startJob = (repo) => post("/api/jobs", { repo });
export const getJob = (id) => call(job(id));
export const getJobPart = (id, part) => call(`${job(id)}/${part}`); // facts, views, report, tasks
export const getHealth = () => call("/api/health");
export const checkAnswers = (id, body) => post(`${job(id)}/verify`, body);
