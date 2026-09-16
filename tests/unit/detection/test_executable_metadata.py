from pathlib import Path

from game_accountability.detection.executable_metadata import collect_executable_metadata


def test_collects_repeatable_bounded_fingerprint_and_nearby_markers(tmp_path: Path) -> None:
    executable = tmp_path / "sample-game.exe"
    executable.write_bytes(b"synthetic executable" * 10_000)
    marker = tmp_path / "UnityPlayer.dll"
    marker.write_bytes(b"synthetic marker")
    before = executable.read_bytes()

    first = collect_executable_metadata(executable)
    second = collect_executable_metadata(executable)

    assert first.sample_sha256 == second.sample_sha256
    assert first.size_bytes == len(before)
    assert first.modified_ns is not None
    assert first.nearby_markers == ("unityplayer.dll",)
    assert executable.read_bytes() == before


def test_missing_executable_returns_partial_metadata_without_crashing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.exe"

    result = collect_executable_metadata(missing)

    assert result.resolved_path == missing.resolve()
    assert result.size_bytes is None
    assert result.sample_sha256 is None
    assert result.nearby_markers == ()
