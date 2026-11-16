# AI providers and browser access

Plumb's web app calls the AI provider from the user's browser, so the
user's key never reaches Plumb's server. A provider only works this way if
it answers the browser's CORS preflight for its API.

`eval/provider_cors.py` sends that preflight and reports the answer. It
needs no key:

```
python eval/provider_cors.py
```

## Results

| Provider | Checked | Browser calls | Notes |
|----------|---------|---------------|-------|
| Anthropic | 16 Nov 2026 | Yes | Allows any origin when the request sends `anthropic-dangerous-direct-browser-access: true`. |
| OpenAI | Not yet | Unknown | Not reachable from the build environment. Run the script locally. |
| Google Gemini | Not yet | Unknown | Not reachable from the build environment. Run the script locally. |
| OpenRouter | Not yet | Unknown | Not reachable from the build environment. Run the script locally. |
| Groq | Not yet | Unknown | Not reachable from the build environment. Run the script locally. |

A provider that blocks browser calls is still usable through the local
command-line tool, where the key stays on the user's machine.
