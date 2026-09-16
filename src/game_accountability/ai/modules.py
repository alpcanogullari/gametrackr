"""DSPy modules with strict Pydantic validation and provenance checks."""

from collections.abc import Callable
from typing import Any

import dspy
from pydantic import ValidationError

from game_accountability.ai.errors import AIOutputValidationError
from game_accountability.ai.schemas import (
    ClassificationRequest,
    GameClassification,
    SignalRankingRequest,
    SignalRankingResult,
    observation_ids,
)
from game_accountability.ai.signatures import (
    GameClassificationSignature,
    ProgressionSignalRankingSignature,
)

Predictor = Callable[..., Any]


def _prediction_value(prediction: Any, field: str) -> Any:
    try:
        return getattr(prediction, field)
    except AttributeError as exc:
        raise AIOutputValidationError(f"AI prediction omitted required field {field!r}") from exc


def _validate_references(references: list[str], available: set[str]) -> None:
    unknown = set(references) - available
    if unknown:
        rendered = ", ".join(sorted(unknown))
        raise AIOutputValidationError(f"AI output referenced unknown observations: {rendered}")


class GameClassifier(dspy.Module):
    """Classify a game from bounded identity evidence and structured observations."""

    def __init__(self, predictor: Predictor | None = None) -> None:
        super().__init__()
        self.predictor = predictor or dspy.ChainOfThought(GameClassificationSignature)

    def forward(self, request: ClassificationRequest) -> dspy.Prediction:
        prediction = self.predictor(
            game_name_hint=request.game_name_hint or "unknown",
            identity_evidence_json=(
                "[" + ",".join(item.model_dump_json() for item in request.identity_evidence) + "]"
            ),
            observations_json=(
                "[" + ",".join(item.model_dump_json() for item in request.observations) + "]"
            ),
        )
        try:
            result = GameClassification.model_validate(
                {
                    "structure": _prediction_value(prediction, "structure"),
                    "strategy": _prediction_value(prediction, "strategy"),
                    "confidence": _prediction_value(prediction, "confidence"),
                    "rationale": _prediction_value(prediction, "rationale"),
                    "supporting_observation_ids": _prediction_value(
                        prediction, "supporting_observation_ids"
                    ),
                }
            )
        except ValidationError as exc:
            raise AIOutputValidationError("invalid game-classification output") from exc

        _validate_references(
            result.supporting_observation_ids,
            observation_ids(request.observations),
        )
        return dspy.Prediction(result=result)


class ProgressionSignalRanker(dspy.Module):
    """Rank likely progression signals from structured deterministic changes."""

    def __init__(self, predictor: Predictor | None = None) -> None:
        super().__init__()
        self.predictor = predictor or dspy.ChainOfThought(ProgressionSignalRankingSignature)

    def forward(self, request: SignalRankingRequest) -> dspy.Prediction:
        prediction = self.predictor(
            game_id=request.game_id,
            observations_json=(
                "[" + ",".join(item.model_dump_json() for item in request.observations) + "]"
            ),
        )
        try:
            result = SignalRankingResult.model_validate(
                {
                    "signals": _prediction_value(prediction, "signals"),
                    "confidence": _prediction_value(prediction, "confidence"),
                    "summary": _prediction_value(prediction, "summary"),
                }
            )
        except ValidationError as exc:
            raise AIOutputValidationError("invalid progression-signal output") from exc

        available = observation_ids(request.observations)
        for signal in result.signals:
            _validate_references(signal.supporting_observation_ids, available)
        return dspy.Prediction(result=result)
