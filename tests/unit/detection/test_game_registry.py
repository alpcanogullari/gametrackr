import json
from pathlib import Path

import pytest

from game_accountability.detection import (
    ExecutableMetadata,
    GameIdentity,
    GameRegistry,
)


def candidate_identity(
    path: str = "D:/Standalone/example.exe",
    fingerprint: str = "a" * 64,
) -> GameIdentity:
    return GameIdentity(
        canonical_game_id="local-candidate",
        display_name="Example",
        executable_path=Path(path),
        executable_fingerprint=fingerprint,
        confidence=0.75,
        provenance=(),
    )


def test_confirmed_identity_round_trips_through_versioned_registry(tmp_path: Path) -> None:
    registry_path = tmp_path / "game-registry.json"
    registry = GameRegistry()

    confirmed = registry.confirm_identity(
        candidate_identity(),
        canonical_game_id="example-game",
        display_name="Example Game",
    )
    registry.save(registry_path)
    restored = GameRegistry.load(registry_path)

    assert confirmed.confidence == 1.0
    assert restored.games == registry.games
    match = restored.match(
        ExecutableMetadata(
            resolved_path=Path("E:/Moved/example.exe"),
            sample_sha256="a" * 64,
        )
    )
    assert match is not None
    assert match[0].canonical_game_id == "example-game"
    assert match[1] == "fingerprint"


def test_reconfirming_game_merges_installation_aliases() -> None:
    registry = GameRegistry()

    registry.confirm_identity(candidate_identity("D:/First/game.exe"))
    confirmed = registry.confirm_identity(candidate_identity("E:/Second/game.exe", "b" * 64))

    assert len(registry.games) == 1
    assert confirmed.executable_paths == (
        Path("D:/First/game.exe"),
        Path("E:/Second/game.exe"),
    )
    assert confirmed.executable_fingerprints == ("a" * 64, "b" * 64)


def test_missing_registry_loads_as_empty(tmp_path: Path) -> None:
    assert GameRegistry.load(tmp_path / "missing.json").games == ()


def test_invalid_registry_is_rejected(tmp_path: Path) -> None:
    registry_path = tmp_path / "invalid.json"
    registry_path.write_text(json.dumps({"schema_version": 999, "games": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid game registry"):
        GameRegistry.load(registry_path)


def test_confirmation_rejects_blank_identity_fields() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        GameRegistry().confirm_identity(
            candidate_identity(),
            canonical_game_id=" ",
        )
