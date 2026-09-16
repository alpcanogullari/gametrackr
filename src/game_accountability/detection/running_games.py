"""Stateful public API that exposes games rather than raw process classifications."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from game_accountability.detection.game_detector import GameDetector
from game_accountability.detection.game_models import (
    EvidenceKind,
    GameClassification,
    GameDetectionResult,
    GameIdentity,
)
from game_accountability.detection.models import ProcessIdentity, ProcessSnapshot
from game_accountability.detection.process_monitor import ProcessMonitor
from game_accountability.detection.window_observer import (
    ForegroundWindowProvider,
    foreground_window_process_id,
)

DEFAULT_STARTUP_GRACE = timedelta(seconds=3)
DEFAULT_ANCESTRY_RETENTION = timedelta(minutes=5)
GAME_CLASSIFICATIONS = frozenset(
    {GameClassification.CONFIRMED_GAME, GameClassification.PROBABLE_GAME}
)


@dataclass(frozen=True, slots=True)
class RunningGame:
    """User-facing projection of one uniquely identified running game."""

    identity: GameIdentity
    process: ProcessSnapshot
    classification: GameClassification
    confidence: float
    is_foreground: bool


@dataclass(frozen=True, slots=True)
class RunningGamesPoll:
    """Games visible to session/UI layers after filtering and primary selection."""

    observed_at: datetime
    games: tuple[RunningGame, ...]
    primary: RunningGame | None
    skipped_processes: int


@dataclass(frozen=True, slots=True)
class _HistoricalProcess:
    snapshot: ProcessSnapshot
    last_seen_at: datetime


class RunningGameService:
    """Poll processes and expose stable running-game selections."""

    def __init__(
        self,
        monitor: ProcessMonitor | None = None,
        detector: GameDetector | None = None,
        *,
        foreground_window_provider: ForegroundWindowProvider = foreground_window_process_id,
        startup_grace: timedelta = DEFAULT_STARTUP_GRACE,
        ancestry_retention: timedelta = DEFAULT_ANCESTRY_RETENTION,
    ) -> None:
        if startup_grace < timedelta(0):
            raise ValueError("startup grace must not be negative")
        if ancestry_retention < timedelta(0):
            raise ValueError("ancestry retention must not be negative")
        self._monitor = monitor or ProcessMonitor()
        self._detector = detector or GameDetector()
        self._foreground_window_provider = foreground_window_provider
        self._startup_grace = startup_grace
        self._ancestry_retention = ancestry_retention
        self._history: dict[int, _HistoricalProcess] = {}
        self._first_seen: dict[ProcessIdentity, datetime] = {}

    def poll(self) -> RunningGamesPoll:
        """Return only qualified games, with the active foreground game first."""

        process_poll = self._monitor.poll()
        now = process_poll.observed_at
        current_pids = {process.pid for process in process_poll.running}
        current_identities = {process.identity for process in process_poll.running}
        for process in process_poll.running:
            self._history[process.pid] = _HistoricalProcess(process, now)
            self._first_seen.setdefault(process.identity, now)

        self._history = {
            pid: historical
            for pid, historical in self._history.items()
            if pid in current_pids or now - historical.last_seen_at <= self._ancestry_retention
        }
        self._first_seen = {
            identity: first_seen
            for identity, first_seen in self._first_seen.items()
            if identity in current_identities
        }

        related = tuple(item.snapshot for item in self._history.values())
        results = self._detector.detect_many(
            process_poll.running,
            related_processes=related,
        )
        foreground_pid = self._foreground_pid()
        games = self._project_games(results, now, foreground_pid)
        primary = games[0] if games else None
        return RunningGamesPoll(
            observed_at=now,
            games=games,
            primary=primary,
            skipped_processes=process_poll.skipped_processes,
        )

    def reset(self) -> None:
        """Forget process, grace, and ancestry history."""

        self._monitor.reset()
        self._history = {}
        self._first_seen = {}

    def _project_games(
        self,
        results: tuple[GameDetectionResult, ...],
        now: datetime,
        foreground_pid: int | None,
    ) -> tuple[RunningGame, ...]:
        by_game_id: dict[str, RunningGame] = {}
        for result in results:
            if (
                result.classification not in GAME_CLASSIFICATIONS
                or result.identity is None
                or not self._past_startup_grace(result.process, now)
            ):
                continue
            game = RunningGame(
                identity=result.identity,
                process=result.process,
                classification=result.classification,
                confidence=result.confidence,
                is_foreground=result.process.pid == foreground_pid,
            )
            existing = by_game_id.get(game.identity.canonical_game_id)
            if existing is None or _selection_key(game) > _selection_key(existing):
                by_game_id[game.identity.canonical_game_id] = game
        return tuple(sorted(by_game_id.values(), key=_selection_key, reverse=True))

    def _past_startup_grace(self, process: ProcessSnapshot, now: datetime) -> bool:
        started_at = process.started_at
        try:
            if started_at is not None and now - started_at >= self._startup_grace:
                return True
            first_seen = self._first_seen[process.identity]
            return now - first_seen >= self._startup_grace
        except (KeyError, TypeError):
            return False

    def _foreground_pid(self) -> int | None:
        try:
            return self._foreground_window_provider()
        except (OSError, TypeError, ValueError):
            return None


def _selection_key(game: RunningGame) -> tuple[bool, bool, bool, float, int]:
    has_visible_window = any(
        evidence.kind is EvidenceKind.VISIBLE_WINDOW for evidence in game.identity.provenance
    )
    return (
        game.is_foreground,
        game.classification is GameClassification.CONFIRMED_GAME,
        has_visible_window,
        game.confidence,
        -game.process.pid,
    )
