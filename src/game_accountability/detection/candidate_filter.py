"""Explainable exclusions for processes that should not be treated as games."""

from pathlib import PurePath

from game_accountability.detection.game_models import DetectionEvidence, EvidenceKind
from game_accountability.detection.models import ProcessSnapshot

LAUNCHER_NAMES = frozenset(
    {
        "battle.net",
        "steam.exe",
        "steam",
        "steam_osx",
        "epicgameslauncher.exe",
        "epicgameslauncher",
        "epicgameslauncher-mac-shipping",
        "epic games launcher",
        "goggalaxy.exe",
        "galaxyclient.exe",
        "galaxyclient",
        "gog galaxy",
        "battle.net.exe",
        "riotclientservices.exe",
        "riotclientservices",
        "riot client",
        "upc.exe",
        "eadesktop.exe",
        "xboxpcapp.exe",
    }
)
EXCLUDED_NAMES = frozenset(
    {
        "explorer.exe",
        "svchost.exe",
        "services.exe",
        "taskhostw.exe",
        "conhost.exe",
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "bash",
        "fish",
        "sh",
        "zsh",
        "terminal",
        "iterm2",
        "python",
        "python3",
        "python.exe",
        "pythonw.exe",
        "game-accountability.exe",
        "game_accountability.exe",
        "game-accountability",
        "game_accountability",
    }
)


def exclusion_evidence(process: ProcessSnapshot) -> DetectionEvidence | None:
    """Return a deterministic exclusion, preferring specific launcher evidence."""

    executable_name = process.executable_name.casefold()
    if executable_name in LAUNCHER_NAMES:
        return DetectionEvidence(
            kind=EvidenceKind.LAUNCHER_EXECUTABLE,
            source="candidate_filter",
            detail=f"known launcher executable: {executable_name}",
            weight=-1.0,
        )
    if executable_name in EXCLUDED_NAMES:
        return DetectionEvidence(
            kind=EvidenceKind.EXCLUDED_EXECUTABLE,
            source="candidate_filter",
            detail=f"excluded utility executable: {executable_name}",
            weight=-1.0,
        )
    if _is_operating_system_path(process.executable_path):
        return DetectionEvidence(
            kind=EvidenceKind.SYSTEM_LOCATION,
            source="candidate_filter",
            detail="executable is in an operating-system location",
            weight=-1.0,
        )
    return None


def _is_operating_system_path(path: PurePath) -> bool:
    parts = tuple(part.casefold() for part in path.parts)
    for index, part in enumerate(parts[:-1]):
        if part == "windows" and parts[index + 1] in {"system32", "syswow64", "winsxs"}:
            return True
    if parts[:3] == ("/", "system", "library"):
        return True
    if parts[:2] in {
        ("/", "bin"),
        ("/", "sbin"),
    }:
        return True
    if parts[:3] in {
        ("/", "usr", "bin"),
        ("/", "usr", "sbin"),
    }:
        return True
    return False
