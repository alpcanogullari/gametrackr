# Architecture

## Document status

- Status: Approved MVP architecture
- Scope: Windows-first local desktop prototype with macOS-capable platform boundaries
- Last updated: 2026-09-16

## System context

Game Accountability is a single-user Windows-first desktop application with a platform-neutral core intended to extend to macOS. It observes local processes and, through isolated adapters, read-only local game state. It decides when to issue a spoiler-free reminder and stores configuration and session history locally.

The MVP has no server, account, cloud sync, telemetry, or required storefront integration.

```text
Local processes -----> Game detector ----> Session service
                                               |
Fake/game adapter ----> Standard GameState ----+----> Accountability engine
                                                        |
                                                        +----> Notification service
                                                        +----> SQLite repository
                                                                    |
PySide6 UI/tray <---------------------------------------------------+
```

## Technology stack

- Python 3.13, 64-bit
- PySide6 for the desktop UI, native tray/menu-bar surface, and notifications
- psutil for local process observation
- watchdog for future file-change-driven adapters
- pydantic for configuration and adapter boundary validation
- platformdirs for per-user application data paths
- sqlite3 from the Python standard library
- pytest and pytest-cov for tests
- Ruff for formatting and linting

## Architectural rules

1. The domain and accountability engine must not import PySide6, psutil, watchdog, or sqlite3.
2. Game-specific code must remain inside its adapter package.
3. The engine must not interpret checkpoint IDs or other game-specific metadata.
4. Adapters may read game-generated files but must never write to them.
5. Player-facing notification text must come from a centralized spoiler-safe catalog and must not interpolate adapter data.
6. Storefront metadata is optional evidence; it is never the primary platform boundary.
7. Boundary inputs are validated before entering the domain.

## Proposed source layout

```text
src/game_accountability/
|-- __init__.py
|-- app.py
|-- domain/
|   |-- models.py
|   |-- decisions.py
|   `-- engine.py
|-- application/
|   |-- session_service.py
|   |-- monitoring_service.py
|   `-- history_service.py
|-- adapters/
|   |-- base.py
|   `-- fake_game.py
|-- infrastructure/
|   |-- process_detector.py
|   |-- sqlite_repository.py
|   |-- settings_repository.py
|   `-- notifier.py
`-- ui/
    |-- main_window.py
    |-- tray.py
    `-- view_models.py

tests/
|-- unit/
|-- integration/
`-- fixtures/
```

## Domain model

### ConfiguredGame

- `game_id: str` — stable slug, unique.
- `display_name: str` — user-facing name.
- `executable_path: Path` — normalized absolute path.
- `strategy: SessionStrategy`.
- `enabled: bool`.
- `adapter_id: str | None` — required for story-aware behavior.

### AppSettings

- `default_target_minutes: int = 90`, range 1–1,440.
- `minimum_stop_quality: int = 3`, range 0–5.
- `minimum_confidence: float = 0.80`, range 0–1.
- `state_stale_after_seconds: int = 30`.
- `process_poll_seconds: float = 2.0`.

The MVP UI exposes the target duration. Other policy values remain validated application defaults until advanced settings are intentionally designed.

### GameState

- `game_id: str`.
- `checkpoint_id: str` — opaque outside the adapter.
- `stop_quality: int`, range 0–5.
- `interruptible: bool`.
- `confidence: float`, range 0–1.
- `observed_at: aware datetime`.

### GamingSession

- `session_id: UUID`.
- `game_id: str`.
- `started_at: aware datetime`.
- `ended_at: aware datetime | None`.
- `target_seconds: int` — snapshot at session start.
- `strategy: SessionStrategy` — snapshot at session start.
- `notification_sent_at: aware datetime | None`.
- `last_decision_reason: DecisionReason | None`.
- `used_fallback: bool`.

Elapsed time is calculated from a monotonic clock while the process is running. Wall-clock timestamps are stored for history.

### AccountabilityDecision

- `action: NO_ACTION | WAIT | NOTIFY`.
- `reason: DecisionReason`.
- `message_key: str | None`.

Required reason codes:

- `BEFORE_TARGET`
- `ALREADY_NOTIFIED`
- `FIXED_TARGET_REACHED`
- `WAIT_NOT_INTERRUPTIBLE`
- `WAIT_FOR_STOPPING_POINT`
- `NOTIFY_NATURAL_STOP`
- `NOTIFY_FIXED_FALLBACK`

## Engine decision policy

The engine is a pure function of the session snapshot, elapsed seconds, optional state, policy settings, and current time.

Evaluation order:

1. If the session was already notified, return `NO_ACTION / ALREADY_NOTIFIED`.
2. If elapsed time is below the target, return `NO_ACTION / BEFORE_TARGET`.
3. If strategy is `FIXED_TIMER`, return `NOTIFY / FIXED_TARGET_REACHED`.
4. For `STORY_AWARE`, validate that state exists, matches the active game, is not stale, and meets confidence `0.80`.
5. If state is unusable, return `NOTIFY / NOTIFY_FIXED_FALLBACK`.
6. If `interruptible` is false, return `WAIT / WAIT_NOT_INTERRUPTIBLE`.
7. If quality is below `3`, return `WAIT / WAIT_FOR_STOPPING_POINT`.
8. Otherwise return `NOTIFY / NOTIFY_NATURAL_STOP`.

`MATCH_AWARE` and `HYBRID` remain modeled enum values but must be rejected by MVP configuration until their policies are specified and tested.

## Adapter contract

Each adapter implements the conceptual interface:

```python
class GameAdapter(Protocol):
    adapter_id: str
    game_id: str

    def observe(self) -> GameState | None:
        """Return the latest normalized state, or None when state is unavailable."""
```

Adapter requirements:

- It returns promptly and does not block the UI thread.
- It catches and translates format-specific errors at its boundary.
- It never produces player-facing prose.
- It never mutates game files or process memory.
- It supplies an aware `observed_at` time and calibrated confidence.
- It is tested from synthetic or legally obtained user-provided fixtures; real save files are not committed by default.

The fake adapter is controlled by deterministic fixture states and is the only required MVP adapter.

## Process detection and lifecycle

- Poll processes every 2 seconds on a worker thread.
- Match the normalized resolved executable path using the host platform's path rules.
- Treat access-denied and disappeared-process errors as ordinary observations, not fatal errors.
- Start a session on the first positive observation for an enabled configured game.
- Keep one active session until its matching process is absent for two consecutive polls, avoiding a transient read failure ending the session.
- When multiple matching processes represent the same game, treat them as one session.
- When another configured game launches during an active session, retain the existing session and log the ignored candidate.
- On clean shutdown, observe the process once more and close the session if it is gone.
- On startup, close any unfinished database session at its last recorded heartbeat and mark its recovery reason; never count application downtime as play time.

## Persistence

SQLite is stored under the user data directory returned by `platformdirs.user_data_dir("Game Accountability", "Game Accountability")`.

Minimum tables:

### `configured_games`

- `game_id` text primary key
- `display_name` text not null
- `executable_path` text not null unique
- `strategy` text not null
- `adapter_id` text nullable
- `enabled` integer not null
- `created_at` text not null
- `updated_at` text not null

### `settings`

- `key` text primary key
- `value_json` text not null

### `sessions`

- `session_id` text primary key
- `game_id` text not null
- `started_at` text not null
- `last_heartbeat_at` text not null
- `ended_at` text nullable
- `target_seconds` integer not null
- `strategy` text not null
- `notification_sent_at` text nullable
- `last_decision_reason` text nullable
- `used_fallback` integer not null default 0
- `end_reason` text nullable

Schema changes use explicit, ordered migrations recorded in a `schema_migrations` table. Foreign keys are enabled. Repository methods own transactions and expose domain types rather than rows.

## Notifications and spoiler boundary

The notifier accepts only a `message_key`, never `GameState`. Initial keys are:

- `natural_stop`: “Good stopping point reached. You've reached your planned gaming time; consider wrapping up here for today.”
- `fixed_target`: “You've reached your planned gaming time. Consider wrapping up for today.”

On a notify decision, the application records the notification transactionally before dispatching it. This favors avoiding duplicate notifications if the process crashes. Notification delivery failure is logged and shown in application status but does not reveal adapter data.

## Concurrency

- PySide6 owns the main thread.
- Process polling, adapter observation, and database work must not block the UI thread.
- Worker results cross into the UI through Qt signals or an application-service boundary.
- The session service serializes lifecycle and decision events so only one decision can mark a session notified.

## Error and fallback policy

- Detector failure: log, retain current session temporarily, retry on the next poll.
- Adapter exception or invalid result: log without checkpoint data in user-facing output and apply fixed fallback once the target is reached.
- Database write failure: show a non-spoiler operational error and do not claim that history was stored.
- Notification failure: preserve the notified record to prevent repeated interruption; expose retry only as a future feature.
- Unknown strategy: reject configuration rather than guessing.

## Security and privacy

- No network access is required by runtime features.
- No telemetry is collected.
- Paths and session history stay in the per-user data directory.
- Logs must not contain raw save contents and should avoid checkpoint IDs at normal log levels.
- SQL uses parameter binding.
- File parsers treat all game data as untrusted and enforce size and format bounds.
- History deletion is an explicit local database transaction and does not delete settings or game files.

## Test strategy

### Unit tests

- Every engine branch and threshold boundary.
- Pydantic validation for states and configuration.
- Spoiler-safe message lookup and absence of adapter interpolation.
- Fake adapter state transitions.
- Session lifecycle and single-notification invariant.

### Integration tests

- SQLite migrations and repository round trips in a temporary directory.
- Real child-process start/stop detection using a harmless test executable.
- Monitoring service through fake detector and fake adapter.
- Reconciliation of unfinished sessions.

### UI smoke tests

- Application startup.
- Configure-game form validation.
- Active-session status update.
- Main-window hide and tray restore.
- Recent-history display and deletion.

Coverage is a signal, not the sole completion criterion. Domain and application-service code should target at least 90% branch coverage for the MVP.

## Architectural decisions

### ADR-001: Local-first Windows-first desktop application

- Status: Accepted
- Decision: Build a single-user Windows-first desktop application with no required server and keep platform-specific behavior isolated for later macOS support.
- Consequence: Privacy and offline operation are simple; cross-device features are deferred. macOS support requires native window observation, menu-bar behavior, notifications, packaging, and validation.

### ADR-002: Python and PySide6 for the MVP

- Status: Accepted
- Decision: Use Python 3.13 and PySide6 to support rapid adapter and save-format experimentation.
- Consequence: Native helpers may be introduced later only when profiling or platform access justifies them.

### ADR-003: Storefront-independent game identity

- Status: Accepted
- Decision: Identify local games primarily by process path and local fingerprints; storefronts are optional integrations.
- Consequence: Configured executable paths are the MVP identity signal, with richer fingerprints deferred.

### ADR-004: Adapter-normalized game state

- Status: Accepted
- Decision: Isolate game-specific progress interpretation behind adapters that emit `GameState`.
- Consequence: The engine remains generic and real adapters can evolve independently.

### ADR-005: Confidence-based safe fallback

- Status: Accepted
- Decision: Missing, stale, malformed, or low-confidence context falls back to a fixed timer.
- Consequence: The product may notify at a suboptimal moment, but it will not invent a contextual claim.

### ADR-006: Fake adapter before real game research

- Status: Accepted
- Decision: Validate the end-to-end architecture with deterministic simulated states first.
- Consequence: Silent Hill 2 and other real adapters begin only after the pipeline acceptance criteria pass.
