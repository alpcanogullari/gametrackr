"""Deterministic orchestration for storefront-independent game identification."""

import hashlib
import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Set
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from game_accountability.detection.candidate_filter import LAUNCHER_NAMES, exclusion_evidence
from game_accountability.detection.executable_metadata import collect_executable_metadata
from game_accountability.detection.game_models import (
    DetectionEvidence,
    EvidenceKind,
    ExecutableMetadata,
    GameClassification,
    GameDetectionResult,
    GameIdentity,
)
from game_accountability.detection.game_registry import GameRegistry
from game_accountability.detection.models import ProcessSnapshot
from game_accountability.detection.window_observer import (
    WindowOwnerProvider,
    visible_window_process_ids,
)

MetadataProvider = Callable[[Path], ExecutableMetadata]
PROBABLE_GAME_THRESHOLD = 0.75
MAX_PROCESS_ANCESTRY_DEPTH = 32

INSTALL_MARKERS = (
    "\\games\\",
    "/games/",
    "\\steamapps\\common\\",
    "/steamapps/common/",
    "\\gog games\\",
    "/gog games/",
    "\\xboxgames\\",
    "/xboxgames/",
    "/applications/",
    "/contents/macos/",
)


class GameDetector:
    """Classify one process using bounded local evidence and known identities."""

    def __init__(
        self,
        registry: GameRegistry | None = None,
        *,
        metadata_provider: MetadataProvider = collect_executable_metadata,
        window_owner_provider: WindowOwnerProvider = visible_window_process_ids,
    ) -> None:
        self._registry = registry or GameRegistry()
        self._metadata_provider = metadata_provider
        self._window_owner_provider = window_owner_provider

    def detect(
        self,
        process: ProcessSnapshot,
        *,
        related_processes: Iterable[ProcessSnapshot] = (),
        visible_window_pids: Set[int] | None = None,
    ) -> GameDetectionResult:
        """Return a conservative identity decision with complete provenance."""

        related = tuple(related_processes)
        exclusion = exclusion_evidence(process)
        if exclusion is not None:
            classification = (
                GameClassification.LAUNCHER
                if exclusion.kind is EvidenceKind.LAUNCHER_EXECUTABLE
                else GameClassification.NOT_GAME
            )
            return GameDetectionResult(
                process=process,
                classification=classification,
                confidence=1.0,
                identity=None,
                evidence=(exclusion,),
                reason=exclusion.detail,
            )

        launcher_ancestor = _find_launcher_ancestor(process, related)
        if launcher_ancestor is not None and _is_launcher_installation_component(
            process,
            launcher_ancestor,
        ):
            evidence = (
                DetectionEvidence(
                    kind=EvidenceKind.LAUNCHER_COMPONENT,
                    source="process_tree",
                    detail="process belongs to the launcher's own installation",
                    weight=-1.0,
                ),
            )
            return GameDetectionResult(
                process=process,
                classification=GameClassification.COMPANION,
                confidence=1.0,
                identity=None,
                evidence=evidence,
                reason="launcher-owned helper process",
            )

        metadata = self._safe_metadata(process.executable_path)
        known_match = self._registry.match(metadata)
        if known_match is not None:
            game, match_kind = known_match
            evidence_kind = (
                EvidenceKind.KNOWN_FINGERPRINT
                if match_kind == "fingerprint"
                else EvidenceKind.KNOWN_PATH
            )
            evidence = (
                DetectionEvidence(
                    kind=evidence_kind,
                    source="game_registry",
                    detail=f"configured game matched by {match_kind}",
                    weight=1.0,
                ),
            )
            confidence = _clamp(game.confidence)
            identity = GameIdentity(
                canonical_game_id=game.canonical_game_id,
                display_name=game.display_name,
                executable_path=metadata.resolved_path,
                executable_fingerprint=metadata.sample_sha256,
                confidence=confidence,
                provenance=evidence,
            )
            return GameDetectionResult(
                process=process,
                classification=GameClassification.CONFIRMED_GAME,
                confidence=confidence,
                identity=identity,
                evidence=evidence,
                reason=f"matched configured game by {match_kind}",
            )

        window_pids = self._visible_window_pids(visible_window_pids)
        evidence = self._candidate_evidence(process, metadata, launcher_ancestor, window_pids)
        confidence = _clamp(sum(item.weight for item in evidence))
        has_launcher_ancestry = launcher_ancestor is not None
        classification = (
            GameClassification.PROBABLE_GAME
            if confidence >= PROBABLE_GAME_THRESHOLD and has_launcher_ancestry
            else GameClassification.UNCERTAIN
        )
        identity = self._candidate_identity(metadata, confidence, evidence)
        return GameDetectionResult(
            process=process,
            classification=classification,
            confidence=confidence,
            identity=identity,
            evidence=evidence,
            reason=(
                "launcher descendant with multiple independent game signals"
                if classification is GameClassification.PROBABLE_GAME
                else (
                    "no recognized launcher ancestor observed"
                    if not has_launcher_ancestry
                    else "insufficient independent evidence to identify a game"
                )
            ),
        )

    def detect_many(
        self,
        processes: Iterable[ProcessSnapshot],
        *,
        related_processes: Iterable[ProcessSnapshot] | None = None,
    ) -> tuple[GameDetectionResult, ...]:
        """Detect processes together and demote non-primary installation companions."""

        snapshots = tuple(processes)
        related = snapshots if related_processes is None else tuple(related_processes)
        window_pids = self._visible_window_pids(None)
        results = [
            self.detect(
                process,
                related_processes=related,
                visible_window_pids=window_pids,
            )
            for process in snapshots
        ]
        grouped_indexes: dict[str, list[int]] = defaultdict(list)
        for index, result in enumerate(results):
            group_key = _installation_group_key(result.process.executable_path)
            if group_key is not None:
                grouped_indexes[group_key].append(index)

        for indexes in grouped_indexes.values():
            primary_index = _select_primary_index(results, indexes, window_pids)
            if primary_index is None:
                continue
            for index in indexes:
                if index == primary_index:
                    continue
                result = results[index]
                if (
                    result.classification
                    in {
                        GameClassification.LAUNCHER,
                        GameClassification.NOT_GAME,
                        GameClassification.CONFIRMED_GAME,
                    }
                    or result.process.pid in window_pids
                ):
                    continue
                group_evidence = DetectionEvidence(
                    kind=EvidenceKind.PROCESS_GROUP,
                    source="process_group",
                    detail="a stronger primary process exists for this game installation",
                    weight=0.0,
                )
                evidence = (*result.evidence, group_evidence)
                results[index] = replace(
                    result,
                    classification=GameClassification.COMPANION,
                    identity=None,
                    evidence=evidence,
                    reason="grouped with a game but not selected as its primary process",
                )
        return tuple(results)

    def _safe_metadata(self, path: Path) -> ExecutableMetadata:
        try:
            return self._metadata_provider(path)
        except (OSError, TypeError, ValueError):
            return ExecutableMetadata(resolved_path=path)

    @staticmethod
    def _candidate_evidence(
        process: ProcessSnapshot,
        metadata: ExecutableMetadata,
        launcher_ancestor: ProcessSnapshot | None,
        visible_window_pids: Set[int],
    ) -> tuple[DetectionEvidence, ...]:
        evidence = [
            DetectionEvidence(
                kind=EvidenceKind.RESOLVED_PATH,
                source="process_monitor",
                detail="process supplied a resolved executable path",
                weight=0.15,
            )
        ]
        if metadata.sample_sha256:
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.CONTENT_FINGERPRINT,
                    source="executable_metadata",
                    detail="bounded executable content fingerprint available",
                    weight=0.25,
                )
            )
        if metadata.size_bytes is not None and metadata.modified_ns is not None:
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.FILE_METADATA,
                    source="executable_metadata",
                    detail="executable size and modification time available",
                    weight=0.10,
                )
            )
        path_key = str(metadata.resolved_path).replace("/", "\\").casefold()
        if any(marker.replace("/", "\\") in path_key for marker in INSTALL_MARKERS):
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.INSTALL_LOCATION,
                    source="executable_metadata",
                    detail="path contains a common game installation marker",
                    weight=0.20,
                )
            )
        if metadata.nearby_markers:
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.GAME_MARKER,
                    source="executable_metadata",
                    detail="nearby game or engine marker files found",
                    weight=0.30,
                )
            )
        if _has_minimum_lifetime(process):
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.PROCESS_LIFETIME,
                    source="process_monitor",
                    detail="process has remained active for at least 30 seconds",
                    weight=0.10,
                )
            )
        if launcher_ancestor is not None:
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.PARENT_LAUNCHER,
                    source="process_tree",
                    detail=(
                        "process is a descendant of recognized launcher "
                        f"{launcher_ancestor.executable_name.casefold()}"
                    ),
                    weight=0.10,
                )
            )
        if process.pid in visible_window_pids:
            evidence.append(
                DetectionEvidence(
                    kind=EvidenceKind.VISIBLE_WINDOW,
                    source="window_observer",
                    detail="process owns a visible top-level window",
                    weight=0.25,
                )
            )
        return tuple(evidence)

    def _visible_window_pids(self, supplied: Set[int] | None) -> frozenset[int]:
        if supplied is not None:
            return frozenset(supplied)
        try:
            return self._window_owner_provider()
        except (OSError, TypeError, ValueError):
            return frozenset()

    @staticmethod
    def _candidate_identity(
        metadata: ExecutableMetadata,
        confidence: float,
        evidence: tuple[DetectionEvidence, ...],
    ) -> GameIdentity:
        stable_material = metadata.sample_sha256 or str(metadata.resolved_path).casefold()
        local_id = hashlib.sha256(stable_material.encode("utf-8")).hexdigest()[:24]
        return GameIdentity(
            canonical_game_id=f"local-{local_id}",
            display_name=_display_name(metadata.resolved_path),
            executable_path=metadata.resolved_path,
            executable_fingerprint=metadata.sample_sha256,
            confidence=confidence,
            provenance=evidence,
        )


def _display_name(path: Path) -> str:
    words = re.sub(r"[_-]+", " ", path.stem).strip()
    return words.title() or path.name


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _has_minimum_lifetime(process: ProcessSnapshot) -> bool:
    if process.started_at is None:
        return False
    try:
        return process.observed_at - process.started_at >= timedelta(seconds=30)
    except TypeError:
        return False


def _find_launcher_ancestor(
    process: ProcessSnapshot,
    related_processes: Iterable[ProcessSnapshot],
) -> ProcessSnapshot | None:
    """Find a direct or transitive launcher ancestor without trusting process names alone."""

    by_pid = {candidate.pid: candidate for candidate in related_processes}
    parent_pid = process.parent_pid
    visited = {process.pid}
    for _depth in range(MAX_PROCESS_ANCESTRY_DEPTH):
        if parent_pid is None or parent_pid in visited:
            return None
        visited.add(parent_pid)
        parent = by_pid.get(parent_pid)
        if parent is None:
            return None
        if parent.executable_name.casefold() in LAUNCHER_NAMES:
            return parent
        parent_pid = parent.parent_pid
    return None


def _is_launcher_installation_component(
    process: ProcessSnapshot,
    launcher: ProcessSnapshot,
) -> bool:
    """Separate launcher UI/helpers from game content beneath recognized library roots."""

    process_key = str(process.executable_path).replace("/", "\\").casefold()
    launcher_root = str(launcher.executable_path.parent).replace("/", "\\").casefold()
    if not launcher_root.endswith("\\"):
        launcher_root += "\\"
    return (
        process_key.startswith(launcher_root)
        and _installation_group_key(process.executable_path) is None
    )


def _installation_group_key(path: Path) -> str | None:
    parts = [part.casefold() for part in path.parts]
    single_markers = {"games", "gog games", "xboxgames"}
    for index, part in enumerate(parts[:-1]):
        if part in single_markers and index + 1 < len(parts):
            return "\\".join(parts[: index + 2])
        if part == "steamapps" and index + 2 < len(parts) and parts[index + 1] == "common":
            return "\\".join(parts[: index + 3])
    return None


def _select_primary_index(
    results: list[GameDetectionResult],
    indexes: list[int],
    visible_window_pids: Set[int],
) -> int | None:
    candidates = [
        index
        for index in indexes
        if results[index].classification
        in {GameClassification.CONFIRMED_GAME, GameClassification.PROBABLE_GAME}
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda index: (
            results[index].classification is GameClassification.CONFIRMED_GAME,
            results[index].process.pid in visible_window_pids,
            results[index].confidence,
            -results[index].process.pid,
        ),
    )
