from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from game_accountability.detection import (
    ExecutableMetadata,
    GameDetector,
    ProcessIdentity,
    ProcessPoll,
    ProcessSnapshot,
    RunningGameService,
)

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


class PollSequence:
    def __init__(self, polls: list[ProcessPoll]) -> None:
        self._polls = iter(polls)
        self.reset_calls = 0

    def poll(self) -> ProcessPoll:
        return next(self._polls)

    def reset(self) -> None:
        self.reset_calls += 1


def snapshot(
    pid: int,
    path: str,
    observed_at: datetime,
    *,
    parent_pid: int | None = None,
    started_at: datetime | None = None,
) -> ProcessSnapshot:
    executable_path = Path(path)
    return ProcessSnapshot(
        identity=ProcessIdentity(pid=pid, started_at=started_at),
        executable_path=executable_path,
        executable_name=executable_path.name,
        observed_at=observed_at,
        parent_pid=parent_pid,
    )


def process_poll(now: datetime, processes: tuple[ProcessSnapshot, ...]) -> ProcessPoll:
    return ProcessPoll(
        observed_at=now,
        started=processes,
        running=processes,
        stopped=(),
        skipped_processes=2,
    )


def metadata(path: Path) -> ExecutableMetadata:
    return ExecutableMetadata(
        resolved_path=path,
        size_bytes=50_000,
        modified_ns=100,
        sample_sha256=(path.stem[0].casefold() * 64),
        nearby_markers=(),
    )


def detector(visible_pids: frozenset[int]) -> GameDetector:
    return GameDetector(
        metadata_provider=metadata,
        window_owner_provider=lambda: visible_pids,
    )


def test_service_exposes_only_games_and_prioritizes_foreground_game() -> None:
    steam = snapshot(10, "C:/Steam/steam.exe", NOW, started_at=NOW - timedelta(minutes=2))
    epic = snapshot(
        20,
        "C:/Epic/EpicGamesLauncher.exe",
        NOW,
        started_at=NOW - timedelta(minutes=2),
    )
    first_game = snapshot(
        101,
        "D:/Games/First/first.exe",
        NOW,
        parent_pid=10,
        started_at=NOW - timedelta(minutes=1),
    )
    second_game = snapshot(
        202,
        "E:/Games/Second/second.exe",
        NOW,
        parent_pid=20,
        started_at=NOW - timedelta(minutes=1),
    )
    monitor = PollSequence([process_poll(NOW, (steam, epic, first_game, second_game))])
    service = RunningGameService(
        monitor=monitor,  # type: ignore[arg-type]
        detector=detector(frozenset({101, 202})),
        foreground_window_provider=lambda: 202,
    )

    result = service.poll()

    assert [game.process.pid for game in result.games] == [202, 101]
    assert result.primary is not None
    assert result.primary.process.pid == 202
    assert result.primary.is_foreground
    assert result.skipped_processes == 2


def test_startup_grace_hides_new_candidate_until_stable() -> None:
    moments = [NOW, NOW + timedelta(seconds=2), NOW + timedelta(seconds=3)]
    polls = []
    for moment in moments:
        launcher = snapshot(10, "C:/Steam/steam.exe", moment)
        game = snapshot(101, "D:/Games/First/first.exe", moment, parent_pid=10)
        polls.append(process_poll(moment, (launcher, game)))
    service = RunningGameService(
        monitor=PollSequence(polls),  # type: ignore[arg-type]
        detector=detector(frozenset({101})),
        foreground_window_provider=lambda: 101,
        startup_grace=timedelta(seconds=3),
    )

    assert service.poll().games == ()
    assert service.poll().games == ()
    assert [game.process.pid for game in service.poll().games] == [101]


def test_observed_launcher_ancestry_survives_launcher_exit_until_retention_expires() -> None:
    first_game = snapshot(
        101,
        "D:/Games/First/first.exe",
        NOW,
        parent_pid=10,
        started_at=NOW - timedelta(minutes=1),
    )
    first_launcher = snapshot(10, "C:/Steam/steam.exe", NOW)
    retained_at = NOW + timedelta(minutes=1)
    expired_at = NOW + timedelta(minutes=6)
    retained_game = snapshot(
        101,
        "D:/Games/First/first.exe",
        retained_at,
        parent_pid=10,
        started_at=first_game.started_at,
    )
    expired_game = snapshot(
        101,
        "D:/Games/First/first.exe",
        expired_at,
        parent_pid=10,
        started_at=first_game.started_at,
    )
    monitor = PollSequence(
        [
            process_poll(NOW, (first_launcher, first_game)),
            process_poll(retained_at, (retained_game,)),
            process_poll(expired_at, (expired_game,)),
        ]
    )
    service = RunningGameService(
        monitor=monitor,  # type: ignore[arg-type]
        detector=detector(frozenset({101})),
        foreground_window_provider=lambda: 101,
        startup_grace=timedelta(0),
        ancestry_retention=timedelta(minutes=5),
    )

    assert service.poll().primary is not None
    assert service.poll().primary is not None
    assert service.poll().primary is None


def test_reset_clears_service_and_monitor_history() -> None:
    monitor = PollSequence([])
    service = RunningGameService(monitor=monitor)  # type: ignore[arg-type]

    service.reset()

    assert monitor.reset_calls == 1


@pytest.mark.parametrize("field", ["startup_grace", "ancestry_retention"])
def test_negative_durations_are_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        RunningGameService(**{field: timedelta(seconds=-1)})
