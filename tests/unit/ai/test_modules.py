from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from game_accountability.ai.errors import AIOutputValidationError
from game_accountability.ai.modules import GameClassifier, ProgressionSignalRanker
from game_accountability.ai.schemas import (
    ClassificationRequest,
    SessionStrategy,
    SessionStructure,
    SignalRankingRequest,
    SourceKind,
    StructuredObservation,
)


class StubPredictor:
    def __init__(self, **output: object) -> None:
        self.output = output
        self.inputs: dict[str, Any] | None = None

    def __call__(self, **inputs: Any) -> SimpleNamespace:
        self.inputs = inputs
        return SimpleNamespace(**self.output)


def observation(observation_id: str = "obs:1") -> StructuredObservation:
    return StructuredObservation(
        observation_id=observation_id,
        source_id="save:1",
        source_kind=SourceKind.SAVE,
        feature_name="story_counter",
        change_kind="integer_increased",
        before_value=4,
        after_value=5,
        recurrence_count=2,
        session_elapsed_seconds=600,
        observed_at=datetime(2026, 8, 28, tzinfo=UTC),
    )


def test_classifier_returns_validated_result_from_structured_input() -> None:
    predictor = StubPredictor(
        structure="story_driven",
        strategy="STORY_AWARE",
        confidence=0.86,
        rationale="Recurring state changes support structured progression.",
        supporting_observation_ids=["obs:1"],
    )
    request = ClassificationRequest(observations=[observation()])

    prediction = GameClassifier(predictor=predictor).forward(request)

    assert prediction.result.structure is SessionStructure.STORY_DRIVEN
    assert prediction.result.strategy is SessionStrategy.STORY_AWARE
    assert prediction.result.confidence == 0.86
    assert predictor.inputs is not None
    assert "raw_file_content" not in predictor.inputs["observations_json"]


def test_classifier_rejects_hallucinated_observation_reference() -> None:
    predictor = StubPredictor(
        structure="story_driven",
        strategy="STORY_AWARE",
        confidence=0.95,
        rationale="Unsupported reference.",
        supporting_observation_ids=["obs:missing"],
    )

    with pytest.raises(AIOutputValidationError, match="unknown observations"):
        GameClassifier(predictor=predictor).forward(
            ClassificationRequest(observations=[observation()])
        )


def test_classifier_rejects_invalid_confidence() -> None:
    predictor = StubPredictor(
        structure="story_driven",
        strategy="STORY_AWARE",
        confidence=1.2,
        rationale="Invalid confidence.",
        supporting_observation_ids=["obs:1"],
    )

    with pytest.raises(AIOutputValidationError, match="invalid game-classification"):
        GameClassifier(predictor=predictor).forward(
            ClassificationRequest(observations=[observation()])
        )


def test_signal_ranker_validates_nested_signals_and_provenance() -> None:
    predictor = StubPredictor(
        signals=[
            {
                "feature_name": "story_counter",
                "progression_relevance": 0.92,
                "confidence": 0.83,
                "rationale": "It changes monotonically across repeated observations.",
                "supporting_observation_ids": ["obs:1"],
            }
        ],
        confidence=0.83,
        summary="One likely progression signal was found.",
    )

    prediction = ProgressionSignalRanker(predictor=predictor).forward(
        SignalRankingRequest(game_id="fake_game", observations=[observation()])
    )

    assert prediction.result.signals[0].feature_name == "story_counter"
    assert prediction.result.signals[0].progression_relevance == 0.92
