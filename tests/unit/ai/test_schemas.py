from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from game_accountability.ai.schemas import (
    ClassificationRequest,
    SourceKind,
    StructuredObservation,
)


def make_observation(**overrides: object) -> StructuredObservation:
    values: dict[str, object] = {
        "observation_id": "obs:1",
        "source_id": "save:1",
        "source_kind": SourceKind.SAVE,
        "feature_name": "offset_42",
        "change_kind": "integer_changed",
        "before_value": 3,
        "after_value": 4,
        "session_elapsed_seconds": 120.0,
        "observed_at": datetime(2026, 8, 28, tzinfo=UTC),
    }
    values.update(overrides)
    return StructuredObservation.model_validate(values)


def test_classification_requires_structured_evidence() -> None:
    with pytest.raises(ValidationError, match="requires identity evidence"):
        ClassificationRequest()


def test_observation_rejects_unbounded_string_content() -> None:
    with pytest.raises(ValidationError, match="cannot exceed 512"):
        make_observation(after_value="x" * 513)


def test_observation_rejects_unknown_raw_content_field() -> None:
    values = make_observation().model_dump()
    values["raw_file_content"] = "not allowed"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StructuredObservation.model_validate(values)
