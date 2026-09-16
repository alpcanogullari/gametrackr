"""Deterministic local process and game detection."""

from game_accountability.detection.game_detector import GameDetector
from game_accountability.detection.game_models import (
    DetectionEvidence,
    EvidenceKind,
    ExecutableMetadata,
    GameClassification,
    GameDetectionResult,
    GameIdentity,
    KnownGame,
)
from game_accountability.detection.game_registry import GameRegistry
from game_accountability.detection.models import ProcessIdentity, ProcessPoll, ProcessSnapshot
from game_accountability.detection.process_monitor import ProcessMonitor
from game_accountability.detection.running_games import (
    RunningGame,
    RunningGameService,
    RunningGamesPoll,
)
from game_accountability.detection.window_observer import (
    foreground_window_process_id,
    visible_window_process_ids,
)

__all__ = [
    "DetectionEvidence",
    "EvidenceKind",
    "ExecutableMetadata",
    "GameClassification",
    "GameDetectionResult",
    "GameDetector",
    "GameIdentity",
    "GameRegistry",
    "KnownGame",
    "ProcessIdentity",
    "ProcessMonitor",
    "ProcessPoll",
    "ProcessSnapshot",
    "RunningGame",
    "RunningGameService",
    "RunningGamesPoll",
    "foreground_window_process_id",
    "visible_window_process_ids",
]
