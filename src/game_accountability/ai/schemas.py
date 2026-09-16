"""Validated structured inputs and outputs for AI-assisted discovery.

These models intentionally contain observations and derived features, not raw
files or unbounded binary content.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160, pattern=r"^[\w.:-]+$"),
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=512)]
ScalarValue = str | int | float | bool | None


class StrictModel(BaseModel):
    """Base model that rejects unrecognized data at every AI boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class SessionStructure(StrEnum):
    STORY_DRIVEN = "story_driven"
    MATCH_BASED = "match_based"
    ENDLESS = "endless"
    SANDBOX = "sandbox"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class SessionStrategy(StrEnum):
    STORY_AWARE = "STORY_AWARE"
    FIXED_TIMER = "FIXED_TIMER"
    MATCH_AWARE = "MATCH_AWARE"
    HYBRID = "HYBRID"


class SourceKind(StrEnum):
    EXECUTABLE = "executable"
    SAVE = "save"
    LOG = "log"
    CONFIG = "config"
    FILESYSTEM = "filesystem"
    SESSION = "session"


class IdentityEvidence(StrictModel):
    """One deterministic signal supporting a canonical game identity."""

    evidence_id: Identifier
    signal_type: Identifier
    value: ShortText
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: ShortText


class StructuredObservation(StrictModel):
    """A bounded, deterministic observation safe for AI interpretation."""

    observation_id: Identifier
    source_id: Identifier
    source_kind: SourceKind
    feature_name: Identifier
    change_kind: Identifier
    before_value: ScalarValue = None
    after_value: ScalarValue = None
    recurrence_count: int = Field(default=1, ge=1, le=1_000_000)
    session_elapsed_seconds: float = Field(ge=0.0)
    observed_at: AwareDatetime

    @field_validator("before_value", "after_value")
    @classmethod
    def bound_string_values(cls, value: ScalarValue) -> ScalarValue:
        if isinstance(value, str) and len(value) > 512:
            raise ValueError("structured scalar strings cannot exceed 512 characters")
        return value


class ClassificationRequest(StrictModel):
    game_name_hint: str | None = Field(default=None, max_length=200)
    identity_evidence: list[IdentityEvidence] = Field(default_factory=list, max_length=100)
    observations: list[StructuredObservation] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def require_structured_evidence(self) -> "ClassificationRequest":
        if not self.identity_evidence and not self.observations:
            raise ValueError("classification requires identity evidence or structured observations")
        return self


class GameClassification(StrictModel):
    structure: SessionStructure
    strategy: SessionStrategy
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: ShortText
    supporting_observation_ids: list[Identifier] = Field(default_factory=list, max_length=100)


class SignalRankingRequest(StrictModel):
    game_id: Identifier
    observations: list[StructuredObservation] = Field(min_length=1, max_length=500)


class ProgressionSignal(StrictModel):
    feature_name: Identifier
    progression_relevance: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: ShortText
    supporting_observation_ids: list[Identifier] = Field(min_length=1, max_length=100)


class SignalRankingResult(StrictModel):
    signals: list[ProgressionSignal] = Field(min_length=1, max_length=50)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: ShortText


def observation_ids(observations: list[StructuredObservation]) -> set[str]:
    """Return the observation IDs available for provenance checks."""

    return {observation.observation_id for observation in observations}
