"""Immutable contracts for deterministic, storefront-independent game detection."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from game_accountability.detection.models import ProcessSnapshot


class GameClassification(StrEnum):
    """Conservative classifications emitted by the game detector."""

    CONFIRMED_GAME = "confirmed_game"
    PROBABLE_GAME = "probable_game"
    UNCERTAIN = "uncertain"
    NOT_GAME = "not_game"
    LAUNCHER = "launcher"
    COMPANION = "companion"


class EvidenceKind(StrEnum):
    """Auditable sources used to reach an identity decision."""

    RESOLVED_PATH = "resolved_path"
    CONTENT_FINGERPRINT = "content_fingerprint"
    FILE_METADATA = "file_metadata"
    INSTALL_LOCATION = "install_location"
    GAME_MARKER = "game_marker"
    PROCESS_LIFETIME = "process_lifetime"
    PARENT_LAUNCHER = "parent_launcher"
    VISIBLE_WINDOW = "visible_window"
    PROCESS_GROUP = "process_group"
    KNOWN_PATH = "known_path"
    KNOWN_FINGERPRINT = "known_fingerprint"
    EXCLUDED_EXECUTABLE = "excluded_executable"
    SYSTEM_LOCATION = "system_location"
    LAUNCHER_EXECUTABLE = "launcher_executable"
    LAUNCHER_COMPONENT = "launcher_component"


@dataclass(frozen=True, slots=True)
class DetectionEvidence:
    """One deterministic fact and its contribution to a decision."""

    kind: EvidenceKind
    source: str
    detail: str
    weight: float


@dataclass(frozen=True, slots=True)
class ExecutableMetadata:
    """Bounded, read-only metadata derived from an executable and its folder."""

    resolved_path: Path
    size_bytes: int | None = None
    modified_ns: int | None = None
    sample_sha256: str | None = None
    nearby_markers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GameIdentity:
    """Stable local identity for one known or candidate game installation."""

    canonical_game_id: str
    display_name: str
    executable_path: Path
    executable_fingerprint: str | None
    confidence: float
    provenance: tuple[DetectionEvidence, ...]


@dataclass(frozen=True, slots=True)
class KnownGame:
    """Locally configured identity aliases used for deterministic matching."""

    canonical_game_id: str
    display_name: str
    executable_paths: tuple[Path, ...] = ()
    executable_fingerprints: tuple[str, ...] = ()
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class GameDetectionResult:
    """Complete, auditable classification for one process observation."""

    process: ProcessSnapshot
    classification: GameClassification
    confidence: float
    identity: GameIdentity | None
    evidence: tuple[DetectionEvidence, ...]
    reason: str
