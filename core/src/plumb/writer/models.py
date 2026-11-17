"""Talk to AI providers, with a cache so the same prompt is never paid for twice.

Keys come from the environment (ANTHROPIC_API_KEY, OPENROUTER_API_KEY) and
are only ever put in request headers: never logged, cached or written into
an error message.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

import httpx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_RETRY_STATUS = {429, 500, 502, 503, 504, 529}


class ModelError(RuntimeError):
    """The provider could not be reached or refused the request."""


class ModelClient(Protocol):
    name: str  # provider:model, shown on the report

    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str: ...


@dataclass
class _HttpClient:
    name: str
    model: str
    key: str
    timeout: float = 120
    retries: int = 2

    def _post(self, url: str, headers: dict[str, str], body: dict[str, object]) -> object:
        delay = 2.0
        for attempt in range(self.retries + 1):
            try:
                response = httpx.post(url, headers=headers, json=body, timeout=self.timeout)
            except httpx.HTTPError as error:
                if attempt == self.retries:
                    raise ModelError(
                        f"{self.name}: could not reach the provider ({error})"
                    ) from None
            else:
                if response.status_code == 200:
                    return cast("object", response.json())
                if response.status_code not in _RETRY_STATUS or attempt == self.retries:
                    raise ModelError(
                        f"{self.name}: provider answered {response.status_code}: "
                        f"{response.text[:300]}"
                    )
            time.sleep(delay)
            delay *= 2
        raise ModelError(f"{self.name}: no answer")  # not reached


@dataclass
class AnthropicClient(_HttpClient):
    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        data = self._post(
            ANTHROPIC_URL,
            {
                "x-api-key": self.key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        blocks = cast("list[dict[str, object]]", cast("dict[str, object]", data).get("content", []))
        return "".join(str(b.get("text", "")) for b in blocks if b.get("type") == "text")


@dataclass
class OpenRouterClient(_HttpClient):
    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        data = self._post(
            OPENROUTER_URL,
            {"authorization": f"Bearer {self.key}", "content-type": "application/json"},
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        choices = cast(
            "list[dict[str, object]]", cast("dict[str, object]", data).get("choices", [])
        )
        if not choices:
            raise ModelError(f"{self.name}: the provider returned no answer")
        message = cast("dict[str, object]", choices[0].get("message", {}))
        return str(message.get("content") or "")


_PROVIDERS = {
    "anthropic": (AnthropicClient, "ANTHROPIC_API_KEY"),
    "openrouter": (OpenRouterClient, "OPENROUTER_API_KEY"),
}


def make_client(spec: str, env: dict[str, str] | None = None) -> ModelClient:
    """Build a client from "provider:model", reading the key from the environment."""
    provider, sep, model = spec.partition(":")
    if not sep or not model or provider not in _PROVIDERS:
        choices = ", ".join(f"{p}:<model>" for p in _PROVIDERS)
        raise ModelError(f"model must look like {choices}, not {spec!r}")
    kind, variable = _PROVIDERS[provider]
    key = (env if env is not None else dict(os.environ)).get(variable, "")
    if not key:
        raise ModelError(f"set {variable} to use {provider} models")
    return kind(name=spec, model=model, key=key)


class ResponseCache:
    """Answers keyed by a hash of the model and the exact prompt."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, model TEXT, "
            "created REAL, text TEXT)"
        )

    @staticmethod
    def key(model: str, system: str, prompt: str) -> str:
        return hashlib.sha256("\0".join((model, system, prompt)).encode()).hexdigest()

    def get(self, key: str) -> str | None:
        row = self._db.execute("SELECT text FROM answers WHERE key = ?", (key,)).fetchone()
        return cast("str", row[0]) if row else None

    def put(self, key: str, model: str, text: str) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO answers VALUES (?, ?, ?, ?)", (key, model, time.time(), text)
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()
