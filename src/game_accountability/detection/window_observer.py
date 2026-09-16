"""Read-only Windows top-level window ownership observation."""

import ctypes
import os
from collections.abc import Callable
from ctypes import wintypes

WindowOwnerProvider = Callable[[], frozenset[int]]
ForegroundWindowProvider = Callable[[], int | None]


def visible_window_process_ids() -> frozenset[int]:
    """Return PIDs owning visible top-level windows, or an empty set if unavailable."""

    if os.name != "nt":
        return frozenset()

    process_ids: set[int] = set()
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def collect(hwnd: int, _parameter: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            process_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value:
                process_ids.add(process_id.value)
            return True

        user32.EnumWindows(collect, 0)
    except (AttributeError, OSError):
        return frozenset()
    return frozenset(process_ids)


def foreground_window_process_id() -> int | None:
    """Return the PID owning the foreground window, or ``None`` if unavailable."""

    if os.name != "nt":
        return None
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        window = user32.GetForegroundWindow()
        if not window:
            return None
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
        return process_id.value or None
    except (AttributeError, OSError):
        return None
