"""Server settings from environment variables, so a host can set them without flags."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from plumb.server.app import Settings
from plumb.server.worker import ServerWriter
from plumb.writer.models import ModelError, ResponseCache, make_client


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    try:
        return int(env.get(name, default))
    except ValueError:
        return default


def server_settings(env: Mapping[str, str]) -> Settings:
    origins = env.get("PLUMB_ALLOWED_ORIGINS", "https://shivemn.github.io")
    return Settings(
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        jobs_per_hour=_int(env, "PLUMB_JOBS_PER_HOUR", 10),
        max_waiting=_int(env, "PLUMB_MAX_WAITING", 25),
        trust_proxy=env.get("PLUMB_TRUST_PROXY", "") in ("1", "true", "yes"),
        client_ip_header=env.get("PLUMB_CLIENT_IP_HEADER", "").strip().lower() or None,
        server_model=env.get("PLUMB_MODEL") or None,
        daily_reports=_int(env, "PLUMB_DAILY_REPORTS", 6),
    )


def server_writer(env: Mapping[str, str], cache: Path) -> ServerWriter | None:
    """The server's own model, or None when PLUMB_MODEL or its key is missing."""
    spec = env.get("PLUMB_MODEL")
    if not spec:
        return None
    try:
        client = make_client(spec, dict(env))
    except ModelError:
        return None
    return ServerWriter(client, ResponseCache(cache), _int(env, "PLUMB_DAILY_REPORTS", 6))


def worker_seconds(env: Mapping[str, str]) -> int:
    return _int(env, "PLUMB_JOB_SECONDS", 300)


def worker_max_files(env: Mapping[str, str], default: int) -> int:
    """Repos with more tracked files are refused; a small host needs a lower cap."""
    return _int(env, "PLUMB_MAX_FILES", default)
