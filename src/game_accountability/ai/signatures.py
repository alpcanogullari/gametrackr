"""DSPy signatures for bounded interpretation of structured observations."""

import dspy

from game_accountability.ai.schemas import (
    ProgressionSignal,
    SessionStrategy,
    SessionStructure,
)


class GameClassificationSignature(dspy.Signature):
    """Classify game structure conservatively using only supplied structured evidence.

    Choose UNKNOWN and FIXED_TIMER when the evidence does not justify a more
    specific classification. Never infer or reveal upcoming narrative content.
    """

    game_name_hint: str = dspy.InputField(desc="Optional non-authoritative display-name hint")
    identity_evidence_json: str = dspy.InputField(
        desc="Validated deterministic identity evidence encoded as JSON"
    )
    observations_json: str = dspy.InputField(
        desc="Validated structured observations encoded as JSON; never raw game files"
    )

    structure: SessionStructure = dspy.OutputField()
    strategy: SessionStrategy = dspy.OutputField()
    confidence: float = dspy.OutputField(desc="Calibrated value from 0.0 through 1.0")
    rationale: str = dspy.OutputField(desc="Brief evidence-grounded rationale")
    supporting_observation_ids: list[str] = dspy.OutputField(
        desc="Only IDs present in observations_json"
    )


class ProgressionSignalRankingSignature(dspy.Signature):
    """Rank structured state changes by likely progression relevance.

    Do not claim knowledge unsupported by the observations. Do not produce
    player-facing text or expose prospective story events.
    """

    game_id: str = dspy.InputField()
    observations_json: str = dspy.InputField(
        desc="Validated structured changes encoded as JSON; never raw binary content"
    )

    signals: list[ProgressionSignal] = dspy.OutputField(
        desc="Most relevant candidate progression features, ordered strongest first"
    )
    confidence: float = dspy.OutputField(desc="Overall calibrated confidence from 0.0 to 1.0")
    summary: str = dspy.OutputField(desc="Brief evidence-grounded summary")
