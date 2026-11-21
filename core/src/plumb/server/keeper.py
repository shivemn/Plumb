"""Keep the worker process running beside the web server.

A worker that dies, from a crash or from running out of memory, would leave
every job queued forever while the API went on answering. The keeper checks
it every few seconds and starts a new one, waiting longer each time if it
keeps dying.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Protocol

log = logging.getLogger("plumb.keeper")


class Process(Protocol):
    @property
    def exitcode(self) -> int | None: ...

    def start(self) -> None: ...
    def is_alive(self) -> bool: ...
    def terminate(self) -> None: ...


class WorkerKeeper:
    def __init__(self, make: Callable[[], Process], check_seconds: float = 5.0) -> None:
        self.make = make
        self.check_seconds = check_seconds
        self.process: Process | None = None
        self.restarts = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True, name="worker-keeper")

    def start(self) -> None:
        self._launch()
        self._thread.start()

    def alive(self) -> bool:
        return self.process is not None and self.process.is_alive()

    def check(self) -> float:
        """Start the worker again if it has stopped. Returns the seconds until the next check."""
        if self.alive():
            return self.check_seconds
        code = self.process.exitcode if self.process is not None else None
        self.restarts += 1
        log.warning("the worker stopped (exit code %s); starting it again", code)
        print(f"plumb: the worker stopped (exit code {code}); starting it again", flush=True)
        self._launch()
        return min(60.0, self.check_seconds * 2 ** min(self.restarts, 4))

    def _launch(self) -> None:
        self.process = self.make()
        self.process.start()

    def _watch(self) -> None:
        wait = self.check_seconds
        while not self._stop.wait(wait):
            wait = self.check()

    def stop(self) -> None:
        self._stop.set()
        if self.process is not None:
            self.process.terminate()
