"""Resilient, deterministic process monitoring implemented with psutil."""

import os
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import psutil

from game_accountability.detection.models import (
    ProcessIdentity,
    ProcessPoll,
    ProcessSnapshot,
)

PROCESS_ATTRIBUTES = ("pid", "name", "exe", "create_time", "ppid")
EXPECTED_PROCESS_ERRORS = (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess)
PROCESS_ITERATION_ERRORS = EXPECTED_PROCESS_ERRORS + (OSError,)


class ProcessLike(Protocol):
    """Small psutil-compatible boundary used by the monitor and unit tests."""

    @property
    def info(self) -> dict[str, Any]: ...


ProcessIterator = Callable[[], Iterable[ProcessLike]]
Clock = Callable[[], datetime]


def normalize_executable_path(path: str | os.PathLike[str]) -> str:
    """Return a stable path key with Windows case normalization."""

    resolved = os.path.realpath(os.path.abspath(os.fspath(path)))
    return os.path.normcase(resolved)


def _default_process_iterator() -> Iterable[ProcessLike]:
    return psutil.process_iter(attrs=PROCESS_ATTRIBUTES, ad_value=None)


def _default_clock() -> datetime:
    return datetime.now(UTC)


class ProcessMonitor:
    """Poll local processes and report starts, current state, and stops.

    When ``executable_paths`` is ``None``, all accessible processes with a
    resolved executable path are observed. An explicit iterable, including an
    empty iterable, filters observations to those exact normalized paths.
    """

    def __init__(
        self,
        executable_paths: Iterable[str | os.PathLike[str]] | None = None,
        *,
        process_iterator: ProcessIterator | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._target_paths = (
            None
            if executable_paths is None
            else frozenset(normalize_executable_path(path) for path in executable_paths)
        )
        self._process_iterator = process_iterator or _default_process_iterator
        self._clock = clock or _default_clock
        self._previous: dict[ProcessIdentity, ProcessSnapshot] = {}

    def poll(self) -> ProcessPoll:
        """Observe processes once and compare them with the previous poll."""

        observed_at = self._aware_now()
        current, skipped = self._scan(observed_at)
        previous = self._previous

        started = self._sorted_snapshots(
            snapshot for identity, snapshot in current.items() if identity not in previous
        )
        stopped = self._sorted_snapshots(
            snapshot for identity, snapshot in previous.items() if identity not in current
        )
        running = self._sorted_snapshots(current.values())

        self._previous = current
        return ProcessPoll(
            observed_at=observed_at,
            started=started,
            running=running,
            stopped=stopped,
            skipped_processes=skipped,
        )

    def reset(self) -> None:
        """Forget previous state so the next poll reports all matches as started."""

        self._previous = {}

    def _scan(self, observed_at: datetime) -> tuple[dict[ProcessIdentity, ProcessSnapshot], int]:
        snapshots: dict[ProcessIdentity, ProcessSnapshot] = {}
        skipped = 0

        try:
            processes = self._process_iterator()
            for process in processes:
                try:
                    snapshot = self._snapshot_process(process, observed_at)
                except EXPECTED_PROCESS_ERRORS:
                    skipped += 1
                    continue
                except (OSError, TypeError, ValueError):
                    skipped += 1
                    continue

                if snapshot is None:
                    skipped += 1
                    continue
                if (
                    self._target_paths is not None
                    and normalize_executable_path(snapshot.executable_path)
                    not in self._target_paths
                ):
                    continue
                snapshots[snapshot.identity] = snapshot
        except PROCESS_ITERATION_ERRORS:
            skipped += 1

        return snapshots, skipped

    def _snapshot_process(
        self,
        process: ProcessLike,
        observed_at: datetime,
    ) -> ProcessSnapshot | None:
        info = process.info
        executable = info.get("exe")
        pid = info.get("pid")
        if not executable or pid is None:
            return None

        started_at = self._started_at(info.get("create_time"))
        identity = ProcessIdentity(pid=int(pid), started_at=started_at)
        path = Path(normalize_executable_path(executable))
        return ProcessSnapshot(
            identity=identity,
            executable_path=path,
            executable_name=path.name,
            observed_at=observed_at,
            parent_pid=self._optional_int(info.get("ppid")),
        )

    def _aware_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("process monitor clock must return a timezone-aware datetime")
        return value

    @staticmethod
    def _started_at(value: Any) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(float(value), tz=UTC)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _sorted_snapshots(
        snapshots: Iterable[ProcessSnapshot],
    ) -> tuple[ProcessSnapshot, ...]:
        return tuple(
            sorted(
                snapshots,
                key=lambda snapshot: (
                    snapshot.pid,
                    snapshot.started_at or datetime.min.replace(tzinfo=UTC),
                ),
            )
        )
