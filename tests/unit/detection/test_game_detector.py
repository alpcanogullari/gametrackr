from datetime import UTC, datetime, timedelta
from pathlib import Path

from game_accountability.detection import (
    EvidenceKind,
    ExecutableMetadata,
    GameClassification,
    GameDetector,
    GameRegistry,
    KnownGame,
    ProcessIdentity,
    ProcessSnapshot,
)

NOW = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def process(
    path: str = "C:/Games/Example/example.exe",
    *,
    pid: int = 123,
    started_at: datetime | None = None,
    parent_pid: int | None = None,
) -> ProcessSnapshot:
    executable_path = Path(path)
    return ProcessSnapshot(
        identity=ProcessIdentity(pid=pid, started_at=started_at),
        executable_path=executable_path,
        executable_name=executable_path.name,
        observed_at=NOW,
        parent_pid=parent_pid,
    )


def metadata(
    path: str = "C:/Games/Example/example.exe",
    *,
    fingerprint: str | None = "a" * 64,
    markers: tuple[str, ...] = ("unityplayer.dll",),
) -> ExecutableMetadata:
    return ExecutableMetadata(
        resolved_path=Path(path),
        size_bytes=10_000 if fingerprint else None,
        modified_ns=100 if fingerprint else None,
        sample_sha256=fingerprint,
        nearby_markers=markers,
    )


def test_known_path_match_returns_confirmed_stable_identity() -> None:
    known = KnownGame(
        canonical_game_id="example-game",
        display_name="Example Game",
        executable_paths=(Path("C:/Games/Example/example.exe"),),
        confidence=0.95,
    )
    detector = GameDetector(
        GameRegistry([known]),
        metadata_provider=lambda _: metadata(),
        window_owner_provider=lambda: frozenset(),
    )

    first = detector.detect(process())
    second = detector.detect(process())

    assert first.classification is GameClassification.CONFIRMED_GAME
    assert first.confidence == 0.95
    assert first.identity == second.identity
    assert first.identity is not None
    assert first.identity.canonical_game_id == "example-game"
    assert first.evidence[0].kind is EvidenceKind.KNOWN_PATH


def test_known_fingerprint_matches_changed_installation_path() -> None:
    known = KnownGame(
        canonical_game_id="portable-game",
        display_name="Portable Game",
        executable_fingerprints=("b" * 64,),
    )
    observed = metadata(
        "D:/Portable/Elsewhere/game.exe",
        fingerprint="b" * 64,
        markers=(),
    )
    detector = GameDetector(
        GameRegistry([known]),
        metadata_provider=lambda _: observed,
        window_owner_provider=lambda: frozenset(),
    )

    result = detector.detect(process("D:/Portable/Elsewhere/game.exe"))

    assert result.classification is GameClassification.CONFIRMED_GAME
    assert result.identity is not None
    assert result.identity.canonical_game_id == "portable-game"
    assert result.evidence[0].kind is EvidenceKind.KNOWN_FINGERPRINT


def test_known_launcher_is_rejected_without_collecting_metadata() -> None:
    calls = 0

    def provider(_: Path) -> ExecutableMetadata:
        nonlocal calls
        calls += 1
        raise AssertionError("launcher filtering should happen first")

    result = GameDetector(
        metadata_provider=provider,
        window_owner_provider=lambda: frozenset(),
    ).detect(process("C:/Program Files/Steam/steam.exe"))

    assert result.classification is GameClassification.LAUNCHER
    assert result.identity is None
    assert result.confidence == 1.0
    assert calls == 0


def test_macos_launcher_name_is_rejected_without_collecting_metadata() -> None:
    calls = 0

    def provider(_: Path) -> ExecutableMetadata:
        nonlocal calls
        calls += 1
        raise AssertionError("launcher filtering should happen first")

    result = GameDetector(
        metadata_provider=provider,
        window_owner_provider=lambda: frozenset(),
    ).detect(process("/Applications/Steam.app/Contents/MacOS/steam_osx"))

    assert result.classification is GameClassification.LAUNCHER
    assert result.identity is None
    assert calls == 0


def test_system_process_is_not_a_game() -> None:
    result = GameDetector(window_owner_provider=lambda: frozenset()).detect(
        process("C:/Windows/System32/custom-service.exe")
    )

    assert result.classification is GameClassification.NOT_GAME
    assert result.identity is None
    assert result.evidence[0].kind is EvidenceKind.SYSTEM_LOCATION


def test_macos_system_process_is_not_a_game() -> None:
    result = GameDetector(window_owner_provider=lambda: frozenset()).detect(
        process("/System/Library/CoreServices/loginwindow")
    )

    assert result.classification is GameClassification.NOT_GAME
    assert result.identity is None
    assert result.evidence[0].kind is EvidenceKind.SYSTEM_LOCATION


def test_common_utility_is_not_a_game() -> None:
    result = GameDetector(window_owner_provider=lambda: frozenset()).detect(
        process("C:/Tools/python.exe")
    )

    assert result.classification is GameClassification.NOT_GAME
    assert result.evidence[0].kind is EvidenceKind.EXCLUDED_EXECUTABLE


def test_multiple_independent_signals_and_launcher_ancestry_make_a_probable_game() -> None:
    detector = GameDetector(
        metadata_provider=lambda _: metadata(),
        window_owner_provider=lambda: frozenset(),
    )
    launcher = process("C:/Program Files/Steam/steam.exe", pid=88)
    game = process(
        pid=501,
        parent_pid=88,
        started_at=NOW - timedelta(minutes=5),
    )

    result = detector.detect(game, related_processes=(launcher, game))

    assert result.classification is GameClassification.PROBABLE_GAME
    assert result.confidence == 1.0
    assert result.identity is not None
    assert result.identity.display_name == "Example"
    assert {item.kind for item in result.evidence} >= {
        EvidenceKind.RESOLVED_PATH,
        EvidenceKind.CONTENT_FINGERPRINT,
        EvidenceKind.FILE_METADATA,
        EvidenceKind.INSTALL_LOCATION,
        EvidenceKind.GAME_MARKER,
        EvidenceKind.PROCESS_LIFETIME,
        EvidenceKind.PARENT_LAUNCHER,
    }


def test_macos_steam_app_bundle_descendant_can_be_a_probable_game() -> None:
    game_path = (
        "/Users/player/Library/Application Support/Steam/steamapps/common/"
        "Example/Example.app/Contents/MacOS/Example"
    )
    launcher = process("/Applications/Steam.app/Contents/MacOS/steam_osx", pid=88)
    game = process(
        game_path,
        pid=501,
        parent_pid=88,
        started_at=NOW - timedelta(minutes=5),
    )
    detector = GameDetector(
        metadata_provider=lambda _: metadata(game_path, markers=("unityplayer.dylib",)),
        window_owner_provider=lambda: frozenset(),
    )

    result = detector.detect(game, related_processes=(launcher, game))

    assert result.classification is GameClassification.PROBABLE_GAME
    assert result.identity is not None
    assert {item.kind for item in result.evidence} >= {
        EvidenceKind.INSTALL_LOCATION,
        EvidenceKind.GAME_MARKER,
        EvidenceKind.PARENT_LAUNCHER,
    }


def test_weak_evidence_remains_uncertain_but_has_a_repeatable_candidate_identity() -> None:
    observed = metadata("D:/Uncategorized/mystery.exe", fingerprint=None, markers=())
    detector = GameDetector(
        metadata_provider=lambda _: observed,
        window_owner_provider=lambda: frozenset(),
    )

    first = detector.detect(process("D:/Uncategorized/mystery.exe"))
    second = detector.detect(process("D:/Uncategorized/mystery.exe"))

    assert first.classification is GameClassification.UNCERTAIN
    assert first.confidence == 0.15
    assert first.identity is not None
    assert first.identity.canonical_game_id == second.identity.canonical_game_id  # type: ignore[union-attr]


def test_metadata_failure_is_non_fatal_and_keeps_result_uncertain() -> None:
    def inaccessible(_: Path) -> ExecutableMetadata:
        raise PermissionError("denied")

    result = GameDetector(
        metadata_provider=inaccessible,
        window_owner_provider=lambda: frozenset(),
    ).detect(process("D:/Unknown/mystery.exe"))

    assert result.classification is GameClassification.UNCERTAIN
    assert result.identity is not None
    assert result.confidence == 0.15


def test_parent_launcher_is_recorded_as_process_tree_evidence() -> None:
    child_metadata = metadata(
        "D:/Uncategorized/child.exe",
        fingerprint="c" * 64,
        markers=(),
    )
    child = process("D:/Uncategorized/child.exe", parent_pid=88)
    launcher = ProcessSnapshot(
        identity=ProcessIdentity(pid=88, started_at=NOW - timedelta(minutes=1)),
        executable_path=Path("C:/Program Files/Steam/steam.exe"),
        executable_name="steam.exe",
        observed_at=NOW,
    )

    result = GameDetector(
        metadata_provider=lambda _: child_metadata,
        window_owner_provider=lambda: frozenset(),
    ).detect(
        child,
        related_processes=(launcher, child),
    )

    assert EvidenceKind.PARENT_LAUNCHER in {item.kind for item in result.evidence}


def test_installation_membership_without_primary_evidence_stays_uncertain() -> None:
    crash_reporter_metadata = metadata(
        "C:/Program Files/Steam/steamapps/common/Overwatch/errorreporting/crashmailer_64.exe",
        markers=(),
    )
    detector = GameDetector(
        metadata_provider=lambda _: crash_reporter_metadata,
        window_owner_provider=lambda: frozenset(),
    )

    result = detector.detect(
        process(
            str(crash_reporter_metadata.resolved_path),
            started_at=NOW - timedelta(minutes=5),
        )
    )

    assert result.confidence == 0.8
    assert result.classification is GameClassification.UNCERTAIN
    assert EvidenceKind.VISIBLE_WINDOW not in {item.kind for item in result.evidence}


def test_visible_window_without_launcher_ancestry_remains_uncertain() -> None:
    observed = metadata("D:/Portable/play.exe", markers=())
    detector = GameDetector(
        metadata_provider=lambda _: observed,
        window_owner_provider=lambda: frozenset({501}),
    )

    result = detector.detect(
        process(
            "D:/Portable/play.exe",
            pid=501,
            started_at=NOW - timedelta(minutes=5),
        )
    )

    assert result.classification is GameClassification.UNCERTAIN
    assert result.reason == "no recognized launcher ancestor observed"
    assert EvidenceKind.VISIBLE_WINDOW in {item.kind for item in result.evidence}


def test_transitive_launcher_descendant_can_be_a_probable_game() -> None:
    launcher = process("C:/Program Files/Steam/steam.exe", pid=10)
    bootstrapper = process("D:/Bootstrap/bootstrap.exe", pid=20, parent_pid=10)
    game = process(
        "D:/Games/Example/example.exe",
        pid=30,
        parent_pid=20,
        started_at=NOW - timedelta(minutes=5),
    )
    detector = GameDetector(
        metadata_provider=lambda _: metadata("D:/Games/Example/example.exe", markers=()),
        window_owner_provider=lambda: frozenset({30}),
    )

    result = detector.detect(
        game,
        related_processes=(launcher, bootstrapper, game),
    )

    assert result.classification is GameClassification.PROBABLE_GAME
    assert any(
        item.kind is EvidenceKind.PARENT_LAUNCHER and "steam.exe" in item.detail
        for item in result.evidence
    )


def test_launcher_installation_helper_is_a_companion() -> None:
    launcher = process("C:/Program Files (x86)/Steam/steam.exe", pid=10)
    web_helper = process(
        "C:/Program Files (x86)/Steam/bin/cef/steamwebhelper.exe",
        pid=40,
        parent_pid=10,
    )
    detector = GameDetector(
        metadata_provider=lambda path: metadata(str(path), markers=()),
        window_owner_provider=lambda: frozenset({40}),
    )

    result = detector.detect(web_helper, related_processes=(launcher, web_helper))

    assert result.classification is GameClassification.COMPANION
    assert result.identity is None
    assert result.evidence[0].kind is EvidenceKind.LAUNCHER_COMPONENT


def test_xbox_app_is_a_launcher() -> None:
    result = GameDetector(window_owner_provider=lambda: frozenset()).detect(
        process("C:/Program Files/WindowsApps/Microsoft.GamingApp/xboxpcapp.exe")
    )

    assert result.classification is GameClassification.LAUNCHER


def test_detect_many_selects_game_and_demotes_same_installation_helper() -> None:
    launcher = process("C:/Program Files (x86)/Steam/steam.exe", pid=10)
    game = process(
        "C:/Program Files (x86)/Steam/steamapps/common/Overwatch/overwatch.exe",
        pid=501,
        parent_pid=10,
        started_at=NOW - timedelta(minutes=5),
    )
    crash_reporter = process(
        "C:/Program Files (x86)/Steam/steamapps/common/Overwatch/errorreporting/crashmailer_64.exe",
        pid=502,
        started_at=NOW - timedelta(minutes=5),
    )

    def provider(path: Path) -> ExecutableMetadata:
        return metadata(str(path), markers=())

    detector = GameDetector(
        metadata_provider=provider,
        window_owner_provider=lambda: frozenset({501}),
    )

    results = {
        result.process.pid: result
        for result in detector.detect_many((launcher, game, crash_reporter))
    }

    assert results[10].classification is GameClassification.LAUNCHER
    assert results[501].classification is GameClassification.PROBABLE_GAME
    assert results[502].classification is GameClassification.COMPANION
    assert results[502].identity is None
    assert EvidenceKind.PROCESS_GROUP in {item.kind for item in results[502].evidence}
