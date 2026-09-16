from datetime import UTC, datetime

import dspy
from dspy.utils.dummies import DummyLM

from game_accountability.ai.modules import GameClassifier
from game_accountability.ai.schemas import (
    ClassificationRequest,
    SessionStrategy,
    SessionStructure,
    SourceKind,
    StructuredObservation,
)


def test_classifier_runs_through_real_dspy_signature_and_json_adapter() -> None:
    adapter = dspy.JSONAdapter()
    lm = DummyLM(
        [
            {
                "reasoning": "The structured counter changes support progression.",
                "structure": "story_driven",
                "strategy": "STORY_AWARE",
                "confidence": 0.88,
                "rationale": "A recurring counter changes during the session.",
                "supporting_observation_ids": ["obs:1"],
            }
        ],
        adapter=adapter,
    )
    request = ClassificationRequest(
        observations=[
            StructuredObservation(
                observation_id="obs:1",
                source_id="save:1",
                source_kind=SourceKind.SAVE,
                feature_name="progress_counter",
                change_kind="integer_increased",
                before_value=7,
                after_value=8,
                recurrence_count=2,
                session_elapsed_seconds=900,
                observed_at=datetime(2026, 8, 28, tzinfo=UTC),
            )
        ]
    )

    with dspy.context(lm=lm, adapter=adapter):
        result = GameClassifier()(request=request).result

    assert result.structure is SessionStructure.STORY_DRIVEN
    assert result.strategy is SessionStrategy.STORY_AWARE
    assert result.confidence == 0.88
