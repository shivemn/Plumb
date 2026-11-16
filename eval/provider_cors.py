"""Check which AI providers accept requests made straight from a web page.

Plumb's web app sends prompts to the provider from the user's browser, so
the key never reaches Plumb's server. That only works if the provider
answers a browser's CORS preflight. This script sends the same preflight a
browser would and reports what came back. It needs no API key.

    python eval/provider_cors.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

ORIGIN = "https://plumb.example"


@dataclass(frozen=True)
class Provider:
    name: str
    url: str
    headers: tuple[str, ...]


PROVIDERS = (
    Provider(
        "Anthropic",
        "https://api.anthropic.com/v1/messages",
        ("x-api-key", "anthropic-version", "content-type", "anthropic-dangerous-direct-browser-access"),
    ),
    Provider(
        "OpenAI",
        "https://api.openai.com/v1/chat/completions",
        ("authorization", "content-type"),
    ),
    Provider(
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        ("x-goog-api-key", "content-type"),
    ),
    Provider(
        "OpenRouter",
        "https://openrouter.ai/api/v1/chat/completions",
        ("authorization", "content-type"),
    ),
    Provider(
        "Groq",
        "https://api.groq.com/openai/v1/chat/completions",
        ("authorization", "content-type"),
    ),
)


def preflight(provider: Provider) -> dict[str, object]:
    request = urllib.request.Request(
        provider.url,
        method="OPTIONS",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": ",".join(provider.headers),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status, headers = response.status, response.headers
    except urllib.error.HTTPError as error:
        status, headers = error.code, error.headers
    except (urllib.error.URLError, TimeoutError) as error:
        return {"provider": provider.name, "error": str(error)}

    allow_origin = headers.get("access-control-allow-origin")
    allow_headers = (headers.get("access-control-allow-headers") or "").lower()
    missing = [
        name for name in provider.headers if allow_headers != "*" and name not in allow_headers
    ]
    return {
        "provider": provider.name,
        "status": status,
        "allow_origin": allow_origin,
        "allow_headers": allow_headers or None,
        "missing_headers": missing,
        "browser_ok": allow_origin in ("*", ORIGIN) and not missing,
    }


def main() -> int:
    results = [preflight(provider) for provider in PROVIDERS]
    json.dump(results, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
