"""DSPy-powered discovery modules with validated structured boundaries."""

from game_accountability.ai.config import DSPySettings, configure_dspy, load_dspy_settings
from game_accountability.ai.modules import GameClassifier, ProgressionSignalRanker
from game_accountability.ai.schemas import (
    ClassificationRequest,
    GameClassification,
    IdentityEvidence,
    ProgressionSignal,
    SignalRankingRequest,
    SignalRankingResult,
    StructuredObservation,
)

__all__ = [
    "ClassificationRequest",
    "DSPySettings",
    "GameClassification",
    "GameClassifier",
    "IdentityEvidence",
    "ProgressionSignal",
    "ProgressionSignalRanker",
    "SignalRankingRequest",
    "SignalRankingResult",
    "StructuredObservation",
    "configure_dspy",
    "load_dspy_settings",
]
