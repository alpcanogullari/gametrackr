"""Read-only, bounded executable evidence collection."""

import hashlib
from collections.abc import Iterable
from pathlib import Path

from game_accountability.detection.game_models import ExecutableMetadata
from game_accountability.detection.process_monitor import normalize_executable_path

SAMPLE_SIZE = 64 * 1024
MAX_DIRECTORY_ENTRIES = 512

MARKER_FILENAMES = frozenset(
    {
        "steam_appid.txt",
        "unityplayer.dll",
        "gameassembly.dll",
        "ue4commandline.txt",
        "goggame.info",
    }
)
MARKER_SUFFIXES = ("-shipping.exe", "-win64-shipping.exe")


def collect_executable_metadata(path: Path) -> ExecutableMetadata:
    """Collect bounded evidence without writing to or executing the target."""

    resolved_path = Path(normalize_executable_path(path))
    size_bytes: int | None = None
    modified_ns: int | None = None
    fingerprint: str | None = None
    markers: tuple[str, ...] = ()

    try:
        stat = resolved_path.stat()
        if resolved_path.is_file():
            size_bytes = stat.st_size
            modified_ns = stat.st_mtime_ns
            fingerprint = _sample_fingerprint(resolved_path, stat.st_size)
    except (OSError, ValueError):
        pass

    try:
        markers = _nearby_markers(resolved_path.parent.iterdir())
    except (OSError, ValueError):
        pass

    return ExecutableMetadata(
        resolved_path=resolved_path,
        size_bytes=size_bytes,
        modified_ns=modified_ns,
        sample_sha256=fingerprint,
        nearby_markers=markers,
    )


def _sample_fingerprint(path: Path, size_bytes: int) -> str:
    digest = hashlib.sha256()
    digest.update(str(size_bytes).encode("ascii"))
    with path.open("rb") as executable:
        digest.update(executable.read(SAMPLE_SIZE))
        if size_bytes > SAMPLE_SIZE:
            executable.seek(max(SAMPLE_SIZE, size_bytes - SAMPLE_SIZE))
            digest.update(executable.read(SAMPLE_SIZE))
    return digest.hexdigest()


def _nearby_markers(entries: Iterable[Path]) -> tuple[str, ...]:
    markers: set[str] = set()
    for index, entry in enumerate(entries):
        if index >= MAX_DIRECTORY_ENTRIES:
            break
        name = entry.name.casefold()
        if name in MARKER_FILENAMES or name.endswith(MARKER_SUFFIXES):
            markers.add(name)
    return tuple(sorted(markers))
