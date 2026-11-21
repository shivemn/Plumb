from __future__ import annotations

from plumb.server.keeper import WorkerKeeper


class FakeProcess:
    def __init__(self, lives: list[bool]) -> None:
        self.lives = lives
        self.exitcode: int | None = None
        self.started = False

    def start(self) -> None:
        self.started = True

    def is_alive(self) -> bool:
        alive = self.lives.pop(0) if self.lives else True
        if not alive:
            self.exitcode = -9
        return alive

    def terminate(self) -> None:
        self.exitcode = -15


def test_a_dead_worker_is_started_again() -> None:
    made: list[FakeProcess] = []

    def make() -> FakeProcess:
        process = FakeProcess([True, False] if not made else [])
        made.append(process)
        return process

    keeper = WorkerKeeper(make, check_seconds=5)
    keeper._launch()  # pyright: ignore[reportPrivateUsage]
    assert keeper.check() == 5 and len(made) == 1  # alive: nothing to do
    assert keeper.check() == 10 and len(made) == 2  # died: a new one, a longer wait
    assert made[1].started and keeper.restarts == 1 and keeper.alive()
    keeper.stop()
    assert made[1].exitcode == -15


def test_the_wait_grows_to_a_minute() -> None:
    keeper = WorkerKeeper(lambda: FakeProcess([False] * 10), check_seconds=5)
    keeper._launch()  # pyright: ignore[reportPrivateUsage]
    waits = [keeper.check() for _ in range(6)]
    assert waits == [10, 20, 40, 60, 60, 60]
