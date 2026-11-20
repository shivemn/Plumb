// Where Plumb's API runs. While HOSTED is empty, the published site shows only
// the reports it ships with, and a new repo gets the command to run Plumb
// locally. On localhost the site uses the API from `docker compose up` or
// `uv run plumb serve`.
const HOSTED = "";

const local = ["localhost", "127.0.0.1"].includes(location.hostname);
export const API = local ? `${location.protocol}//${location.hostname}:8000` : HOSTED;
