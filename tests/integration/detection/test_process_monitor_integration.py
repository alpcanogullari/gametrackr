import subprocess
import sys
import time
from collections.abc import Callable

from game_accountability.detection.models import ProcessPoll
from game_accountability.detection.process_monitor import ProcessMonitor


def poll_until(
    monitor: ProcessMonitor,
    predicate: Callable[[ProcessPoll], bool],
    *,
    timeout_seconds: float = 5.0,
) -> ProcessPoll:
    deadline = time.monotonic() + timeout_seconds
    last_poll = monitor.poll()
    while time.monotonic() < deadline:
        if predicate(last_poll):
            return last_poll
        time.sleep(0.05)
        last_poll = monitor.poll()
    raise AssertionError("process state was not observed within five seconds")


def test_real_child_process_is_detected_and_reported_stopped() -> None:
    monitor = ProcessMonitor()
    monitor.poll()
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        started = poll_until(
            monitor,
            lambda poll: any(snapshot.pid == child.pid for snapshot in poll.started),
        )
        detected = next(snapshot for snapshot in started.running if snapshot.pid == child.pid)
        assert detected.executable_path.resolve() == detected.executable_path
        assert detected.executable_name.lower().startswith("python")
    finally:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)

    stopped = poll_until(
        monitor,
        lambda poll: any(snapshot.pid == child.pid for snapshot in poll.stopped),
    )
    assert any(snapshot.pid == child.pid for snapshot in stopped.stopped)
