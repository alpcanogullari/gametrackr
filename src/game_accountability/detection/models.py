"""Immutable contracts emitted by deterministic process monitoring."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True, order=True)
class ProcessIdentity:
    """Identity of one OS process instance, resilient to PID reuse."""

    pid: int
    started_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProcessSnapshot:
    """One read-only observation of a locally running executable."""

    identity: ProcessIdentity
    executable_path: Path
    executable_name: str
    observed_at: datetime
    parent_pid: int | None = None

    @property
    def pid(self) -> int:
        return self.identity.pid

    @property
    def started_at(self) -> datetime | None:
        return self.identity.started_at


@dataclass(frozen=True, slots=True)
class ProcessPoll:
    """Changes and current state produced by one monitor poll."""

    observed_at: datetime
    started: tuple[ProcessSnapshot, ...]
    running: tuple[ProcessSnapshot, ...]
    stopped: tuple[ProcessSnapshot, ...]
    skipped_processes: int = 0
