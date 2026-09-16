from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil
import pytest

from game_accountability.detection.process_monitor import (
    ProcessLike,
    ProcessMonitor,
    normalize_executable_path,
)


class FakeProcess:
    def __init__(self, info: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self._info = info or {}
        self._error = error

    @property
    def info(self) -> dict[str, Any]:
        if self._error:
            raise self._error
        return self._info


class ProcessSequence:
    def __init__(self, polls: list[list[ProcessLike]]) -> None:
        self._polls = iter(polls)

    def __call__(self) -> Iterable[ProcessLike]:
        return next(self._polls)


def fake_process(
    pid: int,
    executable: str,
    *,
    create_time: float | None = 1_700_000_000.0,
) -> FakeProcess:
    return FakeProcess(
        {
            "pid": pid,
            "name": Path(executable).name,
            "exe": executable,
            "create_time": create_time,
        }
    )


NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def test_poll_reports_started_running_and_stopped_processes() -> None:
    first = fake_process(101, "C:/Games/One/game-one.exe")
    second = fake_process(202, "C:/Games/Two/game-two.exe")
    sequence = ProcessSequence([[first], [first, second], [second]])
    monitor = ProcessMonitor(process_iterator=sequence, clock=lambda: NOW)

    initial = monitor.poll()
    expanded = monitor.poll()
    contracted = monitor.poll()

    assert [snapshot.pid for snapshot in initial.started] == [101]
    assert [snapshot.pid for snapshot in initial.running] == [101]
    assert not initial.stopped
    assert [snapshot.pid for snapshot in expanded.started] == [202]
    assert [snapshot.pid for snapshot in expanded.running] == [101, 202]
    assert [snapshot.pid for snapshot in contracted.stopped] == [101]
    assert [snapshot.pid for snapshot in contracted.running] == [202]


def test_monitor_filters_by_normalized_executable_path() -> None:
    target = "C:/Games/Example/GAME.EXE"
    other = "C:/Games/Other/game.exe"
    monitor = ProcessMonitor(
        executable_paths=["c:\\games\\example\\game.exe"],
        process_iterator=lambda: [fake_process(10, target), fake_process(20, other)],
        clock=lambda: NOW,
    )

    poll = monitor.poll()

    assert [snapshot.pid for snapshot in poll.running] == [10]
    assert poll.running[0].executable_path == Path(normalize_executable_path(target))
    assert poll.skipped_processes == 0


def test_monitor_skips_inaccessible_and_incomplete_processes() -> None:
    monitor = ProcessMonitor(
        process_iterator=lambda: [
            FakeProcess(error=psutil.AccessDenied(pid=10)),
            FakeProcess({"pid": 20, "exe": None, "create_time": None}),
            fake_process(30, "C:/Games/Visible/game.exe"),
        ],
        clock=lambda: NOW,
    )

    poll = monitor.poll()

    assert [snapshot.pid for snapshot in poll.running] == [30]
    assert poll.skipped_processes == 2


def test_monitor_skips_processes_with_invalid_metadata() -> None:
    monitor = ProcessMonitor(
        process_iterator=lambda: [
            fake_process(10, "C:/Games/Invalid/game.exe", create_time=float("nan")),
        ],
        clock=lambda: NOW,
    )

    poll = monitor.poll()

    assert not poll.running
    assert poll.skipped_processes == 1


def test_monitor_handles_process_iterator_access_failure() -> None:
    def inaccessible_iterator() -> Iterable[ProcessLike]:
        raise psutil.AccessDenied(pid=10)

    poll = ProcessMonitor(process_iterator=inaccessible_iterator, clock=lambda: NOW).poll()

    assert not poll.running
    assert poll.skipped_processes == 1


def test_process_without_creation_time_uses_pid_identity() -> None:
    process = fake_process(55, "C:/Games/Legacy/game.exe", create_time=None)
    poll = ProcessMonitor(process_iterator=lambda: [process], clock=lambda: NOW).poll()

    assert poll.running[0].identity.started_at is None


def test_monitor_captures_parent_pid_when_available() -> None:
    observed = fake_process(55, "C:/Games/Example/game.exe")
    observed._info["ppid"] = 12

    poll = ProcessMonitor(process_iterator=lambda: [observed], clock=lambda: NOW).poll()

    assert poll.running[0].parent_pid == 12


def test_process_creation_time_distinguishes_pid_reuse() -> None:
    old = fake_process(99, "C:/Games/Example/game.exe", create_time=1_700_000_000.0)
    replacement = fake_process(99, "C:/Games/Example/game.exe", create_time=1_700_000_100.0)
    monitor = ProcessMonitor(
        process_iterator=ProcessSequence([[old], [replacement]]),
        clock=lambda: NOW,
    )

    monitor.poll()
    poll = monitor.poll()

    assert [snapshot.pid for snapshot in poll.started] == [99]
    assert [snapshot.pid for snapshot in poll.stopped] == [99]
    assert poll.started[0].started_at != poll.stopped[0].started_at


def test_reset_reports_existing_process_as_started_again() -> None:
    process = fake_process(44, "C:/Games/Example/game.exe")
    monitor = ProcessMonitor(
        process_iterator=ProcessSequence([[process], [process]]),
        clock=lambda: NOW,
    )

    monitor.poll()
    monitor.reset()

    assert [snapshot.pid for snapshot in monitor.poll().started] == [44]


def test_monitor_rejects_a_naive_clock() -> None:
    monitor = ProcessMonitor(process_iterator=lambda: [], clock=lambda: datetime(2026, 8, 28))

    with pytest.raises(ValueError, match="timezone-aware"):
        monitor.poll()
