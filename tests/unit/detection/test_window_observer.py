from game_accountability.detection.window_observer import (
    foreground_window_process_id,
    visible_window_process_ids,
)


def test_visible_window_observation_is_read_only_and_returns_process_ids() -> None:
    process_ids = visible_window_process_ids()

    assert isinstance(process_ids, frozenset)
    assert all(isinstance(process_id, int) and process_id > 0 for process_id in process_ids)


def test_foreground_window_observation_returns_optional_process_id() -> None:
    process_id = foreground_window_process_id()

    assert process_id is None or process_id > 0
