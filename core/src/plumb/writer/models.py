"""Talk to AI providers, with a cache so the same prompt is never paid for twice.

Anthropic has its own client. Every other provider speaks the OpenAI chat
format, so one client covers them, each with its own address and key:

    openrouter  OPENROUTER_API_KEY  free models end in ":free"
    groq        GROQ_API_KEY        free tier with a daily token limit
    gemini      GEMINI_API_KEY      free tier for Flash models
    openai      OPENAI_API_KEY
    ollama      (no key)            models on your own machine; OLLAMA_HOST
                                    changes the address from localhost:11434

Keys come from the environment and are only ever put in request headers:
never logged, cached or written into an error message. An Anthropic key
that is not scoped to one workspace also needs ANTHROPIC_WORKSPACE_ID,
sent as the anthropic-workspace-id header.
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
                    hint = ""
                    if "anthropic-workspace-id" in response.text:
                        hint = (
                            " Set ANTHROPIC_WORKSPACE_ID, or create a key scoped to one workspace."
                        )
                    raise ModelError(
                        f"{self.name}: provider answered {response.status_code}: "
                        f"{response.text[:300]}{hint}"
                    )
            time.sleep(delay)
            delay *= 2
        raise ModelError(f"{self.name}: no answer")  # not reached


@dataclass
class AnthropicClient(_HttpClient):
    workspace: str = ""

    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        headers = {
            "x-api-key": self.key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if self.workspace:
            headers["anthropic-workspace-id"] = self.workspace
        data = self._post(
            ANTHROPIC_URL,
            headers,
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
class ChatClient(_HttpClient):
    """Any provider with an OpenAI-style /chat/completions endpoint."""

    url: str = ""
    # OpenAI's newer models only accept max_completion_tokens; others take max_tokens.
    token_field: str = "max_tokens"

    def complete(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        headers = {"content-type": "application/json"}
        if self.key:
            headers["authorization"] = f"Bearer {self.key}"
        data = self._post(
            self.url,
            headers,
            {
                "model": self.model,
                self.token_field: max_tokens,
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


@dataclass(frozen=True)
class Provider:
    url: str
    key_variable: str | None  # None: no key needed
    token_field: str = "max_tokens"


PROVIDERS: dict[str, Provider] = {
    "openrouter": Provider("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "groq": Provider("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "gemini": Provider(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "GEMINI_API_KEY",
    ),
    "openai": Provider(
        "https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY", "max_completion_tokens"
    ),
    "ollama": Provider("http://localhost:11434/v1/chat/completions", None),
}


def make_client(spec: str, env: dict[str, str] | None = None) -> ModelClient:
    """Build a client from "provider:model", reading the key from the environment."""
    provider, sep, model = spec.partition(":")
    names = ["anthropic", *PROVIDERS]
    if not sep or not model or provider not in names:
        choices = ", ".join(f"{p}:<model>" for p in names)
        raise ModelError(f"model must look like {choices}, not {spec!r}")
    environment = env if env is not None else dict(os.environ)
    if provider == "anthropic":
        key = environment.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ModelError("set ANTHROPIC_API_KEY to use anthropic models")
        workspace = environment.get("ANTHROPIC_WORKSPACE_ID", "")
        return AnthropicClient(name=spec, model=model, key=key, workspace=workspace)
    settings = PROVIDERS[provider]
    key = environment.get(settings.key_variable, "") if settings.key_variable else ""
    if settings.key_variable and not key:
        raise ModelError(f"set {settings.key_variable} to use {provider} models")
    url = settings.url
    if provider == "ollama" and environment.get("OLLAMA_HOST"):
        host = environment["OLLAMA_HOST"].rstrip("/")
        host = host if host.startswith("http") else f"http://{host}"
        url = f"{host}/v1/chat/completions"
    # Local models are slow on a laptop, so they get longer to answer.
    timeout = 600 if provider == "ollama" else 120
    return ChatClient(
        name=spec,
        model=model,
        key=key,
        timeout=timeout,
        url=url,
        token_field=settings.token_field,
    )


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
