"""Deterministic matching and local persistence for confirmed game identities."""

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from game_accountability.detection.game_models import ExecutableMetadata, GameIdentity, KnownGame
from game_accountability.detection.process_monitor import normalize_executable_path

REGISTRY_SCHEMA_VERSION = 1


class GameRegistry:
    """Match executable evidence to known games without a storefront dependency."""

    def __init__(self, games: Iterable[KnownGame] = ()) -> None:
        self._games = tuple(games)

    @property
    def games(self) -> tuple[KnownGame, ...]:
        """Return immutable configured identities."""

        return self._games

    def match(self, metadata: ExecutableMetadata) -> tuple[KnownGame, str] | None:
        """Return the strongest configured match and its provenance kind."""

        fingerprint = metadata.sample_sha256
        if fingerprint:
            for game in self._games:
                if fingerprint.casefold() in {
                    candidate.casefold() for candidate in game.executable_fingerprints
                }:
                    return game, "fingerprint"

        path_key = normalize_executable_path(metadata.resolved_path)
        for game in self._games:
            if path_key in {
                normalize_executable_path(candidate) for candidate in game.executable_paths
            }:
                return game, "path"
        return None

    def confirm_identity(
        self,
        identity: GameIdentity,
        *,
        canonical_game_id: str | None = None,
        display_name: str | None = None,
    ) -> KnownGame:
        """Trust a user-confirmed local identity and retain its reusable aliases."""

        game_id = (canonical_game_id or identity.canonical_game_id).strip()
        name = (display_name or identity.display_name).strip()
        if not game_id or not name:
            raise ValueError("confirmed game ID and display name must not be empty")

        existing = next(
            (game for game in self._games if game.canonical_game_id == game_id),
            None,
        )
        paths = (*(() if existing is None else existing.executable_paths), identity.executable_path)
        fingerprints = tuple(
            fingerprint
            for fingerprint in (
                *(() if existing is None else existing.executable_fingerprints),
                identity.executable_fingerprint,
            )
            if fingerprint
        )
        confirmed = KnownGame(
            canonical_game_id=game_id,
            display_name=name,
            executable_paths=_unique_paths(paths),
            executable_fingerprints=tuple(dict.fromkeys(fingerprints)),
            confidence=1.0,
        )
        self._games = tuple(game for game in self._games if game.canonical_game_id != game_id) + (
            confirmed,
        )
        return confirmed

    def save(self, path: str | os.PathLike[str]) -> None:
        """Atomically persist the sanitized registry as versioned local JSON."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "games": [
                {
                    "canonical_game_id": game.canonical_game_id,
                    "display_name": game.display_name,
                    "executable_paths": [str(path) for path in game.executable_paths],
                    "executable_fingerprints": list(game.executable_fingerprints),
                    "confidence": game.confidence,
                }
                for game in self._games
            ],
        }
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, destination)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "GameRegistry":
        """Load a versioned registry; a missing file represents an empty registry."""

        source = Path(path)
        if not source.exists():
            return cls()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            games = _parse_registry(payload)
        except (OSError, TypeError, ValueError) as error:
            raise ValueError(f"invalid game registry: {source}") from error
        return cls(games)


def _parse_registry(payload: Any) -> tuple[KnownGame, ...]:
    if not isinstance(payload, dict) or payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ValueError("unsupported game registry schema")
    raw_games = payload.get("games")
    if not isinstance(raw_games, list):
        raise ValueError("game registry games must be a list")

    games: list[KnownGame] = []
    for item in raw_games:
        if not isinstance(item, dict):
            raise ValueError("game registry entry must be an object")
        game_id = item.get("canonical_game_id")
        display_name = item.get("display_name")
        paths = item.get("executable_paths")
        fingerprints = item.get("executable_fingerprints")
        confidence = item.get("confidence")
        if (
            not isinstance(game_id, str)
            or not game_id.strip()
            or not isinstance(display_name, str)
            or not display_name.strip()
            or not isinstance(paths, list)
            or not all(isinstance(path, str) and path for path in paths)
            or not isinstance(fingerprints, list)
            or not all(isinstance(value, str) and value for value in fingerprints)
            or not isinstance(confidence, int | float)
            or isinstance(confidence, bool)
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise ValueError("invalid game registry entry")
        games.append(
            KnownGame(
                canonical_game_id=game_id.strip(),
                display_name=display_name.strip(),
                executable_paths=tuple(Path(path) for path in paths),
                executable_fingerprints=tuple(fingerprints),
                confidence=float(confidence),
            )
        )
    return tuple(games)


def _unique_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    unique: dict[str, Path] = {}
    for path in paths:
        unique.setdefault(normalize_executable_path(path), path)
    return tuple(unique.values())
