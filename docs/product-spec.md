# Product specification

## Document status

- Status: Current product and MVP baseline
- Product: Game Accountability
- Platform: Windows desktop
- Last updated: 2026-08-28

## Product vision

Game Accountability helps busy PC players keep gaming within the rest of their day. Instead of demanding that a player stop the instant a timer expires, it waits for an appropriate in-game stopping opportunity when reliable game-state information is available.

The product is an accountability aid, not a game blocker, parental-control system, or spoiler-bearing progress guide.

## Product principle

> Given how much planned gaming time the player has used, is the current moment an appropriate opportunity to stop?

## Product differentiation

The intended long-term advantage is the combination of:

```text
storefront-independent game detection
+ deterministic local state observation
+ AI-assisted progression discovery
+ reusable learned game profiles
+ spoiler-aware stopping-point intelligence
```

The system should learn how to understand new games with substantially less manual authoring than a curated database of every boss, area, chapter, and checkpoint would require.

## Target users

The initial product is for a single Windows PC user who:

- wants to plan the duration of a gaming session;
- may lose track of time while playing;
- does not want interruption during a boss, match, cutscene, puzzle, or important sequence;
- plays games from varied storefronts, standalone installations, or modded setups; and
- values private, local-first runtime operation and spoiler-free guidance.

## Goals

- Detect running games independently of storefront.
- Identify games using multiple local signals rather than executable name alone.
- Track the duration and lifecycle of gaming sessions.
- Classify a game's session structure as story-driven, match-based, endless, sandbox, or hybrid, with confidence.
- Discover locally available state sources without modifying them.
- Convert raw local changes into structured, auditable observations.
- Use AI selectively to rank progression signals and propose milestones and stopping-point rules.
- Build and incrementally improve confidence-scored `GameProfile` data across sessions.
- Use reliable profiles and deterministic rules during normal runtime.
- Notify at the target time or a reliable natural stopping point after it.
- Fall back safely to fixed-timer behavior whenever understanding is insufficient.
- Keep all player-facing output free of narrative and progression spoilers.

## Non-goals for the initial development phase

- User accounts, automatic profile sharing, cloud synchronization, or social features.
- Blocking, suspending, or forcibly closing games.
- Depending on Steam or any other storefront for core operation.
- Perfectly understanding an unknown game after a few minutes of observation.
- Querying an LLM every few seconds or for every normal runtime decision.
- Sending complete binary saves or raw game files to an LLM by default.
- Manually authoring comprehensive checkpoint maps as the primary scaling method.
- Match detection for production multiplayer games.
- Screen recognition, achievement ingestion, console support, or emulator support in the initial prototype.
- Polished analytics, a massive supported-game library, or advanced installer infrastructure.
- Large AI frameworks, vector databases, Redis, or Docker without a separately approved need.

## Storefront independence

The game is the primary entity. Storefront APIs are optional metadata sources only.

Where technically possible, the architecture must accommodate Steam, Epic Games Store, GOG, Xbox App, Battle.net, Riot, itch.io, standalone executables, DRM-free games, modded installations, older PC games, and eventually emulators.

Core detection must not require a storefront account or API. Identity may combine executable path, executable fingerprint, metadata, installation markers, window metadata, local state locations, and optional storefront evidence.

For the initial automatic-discovery precision gate, an unconfigured process must be a direct or transitive child of a recognized local launcher process before it can be classified as a probable game. This is local process-tree evidence and requires no storefront API. Standalone, DRM-free, and launcherless games remain supported through explicit local path or fingerprint confirmation.

## Game-understanding model

### Deterministic observation layer

Normal Python code is responsible for:

- process detection and session timestamps;
- executable metadata and fingerprints;
- local game-identification signals;
- candidate save, state, log, and configuration discovery;
- read-only filesystem monitoring;
- bounded file snapshots and metadata capture;
- binary or structured state differences;
- recurring-change and temporal analysis; and
- structured observation persistence.

An LLM must not perform these tasks when deterministic code can do so reliably.

### AI-assisted interpretation layer

DSPy/LLM modules may operate on structured observations to:

- classify game and session structure;
- rank likely progression variables;
- correlate recurring state changes with progression;
- propose milestone boundaries;
- estimate stopping-point quality and interruptibility;
- construct candidate profiles;
- evaluate uncertainty and competing hypotheses; and
- improve an existing profile as new evidence arrives.

AI output is a hypothesis with confidence and provenance. It is not trusted as a runtime rule until validated sufficiently for the relevant behavior.

## Operating modes

### Discovery Mode

Discovery Mode is used for an unknown game or a known game whose profile is missing, incompatible, or below the required confidence.

```text
detect process
-> identify game
-> classify game structure
-> locate candidate local state sources
-> observe changes across gameplay
-> capture snapshots and deterministic diffs
-> persist structured observations
-> rank likely progression signals with AI assistance
-> infer candidate milestones and stopping qualities
-> build or improve a candidate GameProfile
-> validate confidence
```

Discovery Mode accumulates evidence across multiple sessions. While the profile remains unreliable, recommendations use `FIXED_TIMER`. Discovery activity must not delay or block the running game.

### Runtime Mode

Runtime Mode is used when a compatible profile has sufficient confidence for its intended rules.

```text
detect game
-> load profile
-> monitor known sources
-> deterministically extract known signals
-> derive standardized GameState
-> run deterministic accountability engine
-> send spoiler-free notification when appropriate
```

Normal Runtime Mode should be fast, reproducible, offline-capable, and free from routine LLM calls. If profile matching or state extraction loses confidence, the session falls back to `FIXED_TIMER` and may collect observations for later profile improvement.

## Session strategies

- `STORY_AWARE`: delays the reminder until a reliable, interruptible natural stopping point.
- `FIXED_TIMER`: reminds at the target without contextual state requirements.
- `MATCH_AWARE`: delays a reminder until an active match ends.
- `HYBRID`: combines compatible story, match, or timer behavior.

Classification may propose a strategy, but confidence is required. Uncertain classification defaults to `FIXED_TIMER`.

Likely mappings include:

- story-focused single-player games -> `STORY_AWARE`;
- competitive match-based games -> `MATCH_AWARE`;
- endless or sandbox games -> `FIXED_TIMER` or `HYBRID`.

## Learned GameProfile

A versioned `GameProfile` may contain:

- canonical game ID and display name;
- executable fingerprints and installation variants;
- detected storefront metadata, when available;
- game-structure classification and session strategy;
- known save, state, log, and configuration locations;
- deterministic extraction definitions or adapter references;
- important state variables and progression-signal mappings;
- milestone and stopping-point models;
- interruptibility and stop-quality rules;
- confidence at profile, source, signal, and rule levels;
- profile schema and content versions;
- observation and inference provenance; and
- compatibility constraints and validation status.

Profiles must support incremental revision rather than assuming the first inference is correct. Future designs may distribute validated, sanitized profiles so another user can avoid relearning a known game; automatic upload or sharing is not part of the initial product.

## Adapters and standardized GameState

Adapters remain the standardized runtime interface between deterministic game-specific extraction, learned profiles, and the common state consumed by the accountability engine.

Some unusual or proprietary formats may require manually written parsing code. That code extracts state; it does not imply manually authoring every milestone.

The standardized state contains at least:

- `game_id: str`;
- `checkpoint_id: str | None`, opaque outside game understanding;
- `stop_quality: int`, from 0 through 5;
- `interruptible: bool`;
- `confidence: float`, from 0.0 through 1.0; and
- `observed_at: datetime`.

The core accountability engine never contains Silent Hill, Deltarune, Silksong, storefront, save-format, or other game-specific logic.

## Accountability policy

Once a reliable `GameState` exists, runtime decisions are deterministic.

The initial story-aware rule is:

```text
target reached
+ stop_quality >= 3
+ interruptible is true
+ confidence >= 0.80
+ state is fresh
-> notify once
```

Before the target, the system does not recommend stopping. After the target, a reliable poor or non-interruptible state causes it to wait. Missing, stale, malformed, mismatched, or low-confidence state causes fixed-timer fallback. A notification is sent at most once per session.

## Spoiler policy

Internally, observations and profiles may represent exact progression, upcoming areas, bosses, future structure, or estimated duration. None of this information may cross into the player-facing interface.

Approved messages are generic, such as:

- “Good stopping point reached.”
- “This is a good place to wrap up for today.”
- “You've reached your planned gaming time.”

Notifications must never expose checkpoint IDs, state variables, areas, objectives, future-duration estimates, bosses, chapters, milestone labels, or upcoming events. Player-visible strings come from a centralized allowlist and never interpolate profile or observation data.

## Functional requirements

### Configuration, detection, and sessions

- `FR-001`: The user can configure a whole-minute session target from 1 through 1,440 minutes; the default is 90.
- `FR-002`: The application detects local processes and creates one active session for the recognized game.
- `FR-003`: Game identification combines available local evidence and produces identity confidence and provenance.
- `FR-003a`: An unconfigured automatic-discovery candidate requires direct or transitive ancestry from a recognized launcher; a configured path or fingerprint may explicitly identify a launcherless game.
- `FR-003b`: The running-game boundary filters launchers and companions, deduplicates canonical identities, and selects the foreground qualified game as primary.
- `FR-003c`: Automatic candidates pass a short startup grace period, and launcher ancestry observed by the application may be retained briefly after launcher exit.
- `FR-003d`: A user can confirm an executable identity and persist its normalized path and bounded fingerprint locally for deterministic later matching.
- `FR-004`: Executable names alone are insufficient when ambiguous; resolved path or stronger fingerprints are required.
- `FR-005`: Optional storefront data may enrich identification but cannot be required.
- `FR-006`: The application stores session start, heartbeat, end, target, strategy, notification state, and relevant decision reason locally.
- `FR-007`: The UI can show the current game, mode, elapsed time, target, profile confidence status, and recent session history without spoilers.
- `FR-008`: The application continues monitoring from the Windows system tray when its main window is hidden.
- `FR-009`: Restart reconciles an unfinished session without counting application downtime as play time.

### Deterministic observation

- `FR-010`: Discovery Mode can register candidate save, state, log, and configuration sources associated with a game identity.
- `FR-011`: Filesystem observation and snapshot readers are read-only.
- `FR-012`: Snapshot capture records bounded content-derived features, metadata, time, source identity, and provenance.
- `FR-013`: Diff processing converts snapshots into structured changes before AI interpretation.
- `FR-014`: Repeated observations can be correlated across events and sessions.
- `FR-015`: Raw binary content is not sent to an LLM by default.
- `FR-016`: Observation failures are isolated from the running game and do not terminate session tracking.

### AI-assisted discovery

- `FR-020`: Game classification returns a proposed structure and session strategy with confidence and rationale/provenance suitable for auditing.
- `FR-021`: Progression-signal ranking consumes structured observations rather than requiring raw game files.
- `FR-022`: Milestone and stopping-point inference produces candidate rules with confidence and supporting observation references.
- `FR-023`: The profile builder versions all generated profiles and preserves their provenance.
- `FR-024`: New evidence can strengthen, weaken, replace, or invalidate existing candidate rules.
- `FR-025`: Remote AI use, if configured, is explicit and data-minimized; credentials are loaded from environment variables and never persisted in profiles or observations.
- `FR-026`: Discovery Mode remains useful over multiple sessions and does not claim complete understanding from insufficient evidence.

### Profiles, adapters, and runtime

- `FR-030`: A profile must pass schema, compatibility, and confidence checks before enabling contextual Runtime Mode.
- `FR-031`: Runtime Mode deterministically monitors the sources and applies the extraction rules identified by the active profile.
- `FR-032`: Adapters expose a common interface that produces validated `GameState` values.
- `FR-033`: Manually written extractors may support unusual formats without placing game-specific logic in the core engine.
- `FR-034`: Runtime Mode does not require routine LLM queries when a reliable profile and extraction mapping exist.
- `FR-035`: Profile mismatch, insufficient confidence, extraction failure, or invalid state triggers `FIXED_TIMER` fallback.
- `FR-036`: Profiles can be improved from later structured observations without silently overwriting the last known valid version.

### Decisions and notifications

- `FR-040`: The accountability engine is deterministic and consumes only session facts, policy, and standardized state.
- `FR-041`: Before the target, the engine never recommends stopping.
- `FR-042`: `STORY_AWARE` waits after the target while a reliable state is non-interruptible or below stop quality `3`.
- `FR-043`: `STORY_AWARE` notifies after the target when state is fresh, confidence is at least `0.80`, interruptibility is true, and quality is at least `3`.
- `FR-044`: `FIXED_TIMER` notifies at the target without contextual claims.
- `FR-045`: Uncertain game classification defaults to `FIXED_TIMER`.
- `FR-046`: The application emits at most one stopping recommendation per session.
- `FR-047`: Player-facing notifications use spoiler-safe catalog messages only.
- `FR-048`: Completed session history can be viewed and deleted without deleting configured games or game files.

## Quality requirements

- `NFR-001 Privacy`: Runtime Mode requires no network service and sends no telemetry.
- `NFR-002 AI data minimization`: Optional remote discovery receives structured observations only by default, never complete binary save files.
- `NFR-003 Safety`: The application never modifies game saves, logs, configuration, or process memory as part of observation.
- `NFR-004 Reliability`: Invalid AI output or adapter state is rejected and causes deterministic fallback.
- `NFR-005 Reproducibility`: A versioned profile plus the same standardized inputs produces the same runtime decision.
- `NFR-006 Performance`: Routine monitoring and extraction do not block the UI or require continuous AI calls.
- `NFR-007 Auditability`: Identity, classifications, signals, milestones, and profile rules retain confidence and provenance.
- `NFR-008 Accessibility`: Core controls are keyboard accessible, labeled, and do not convey state through color alone.
- `NFR-009 Compatibility`: Initial development targets 64-bit Windows 10 and Windows 11 with Python 3.13.
- `NFR-010 Testability`: Detection, snapshots, diffs, profile validation, adapters, fallback, and the accountability engine can be tested without a commercial game or GUI.
- `NFR-011 Spoiler safety`: No player-facing string interpolates observations, learned rules, checkpoints, or profile metadata.

## Initial acceptance criteria

- `AC-001`: A configured or identifiable test executable creates one session within 5 seconds of launch and ends it within 5 seconds of exit.
- `AC-002`: Two matching observations of the same executable resolve to the same canonical test-game identity with recorded evidence.
- `AC-003`: A synthetic state file change produces a snapshot and structured diff without modifying the source file.
- `AC-004`: Repeated synthetic changes are stored with timestamps, source identity, session association, and provenance.
- `AC-005`: The fake-game simulation can produce poor, strong, non-interruptible, and low-confidence states without a manually authored commercial-game checkpoint map.
- `AC-006`: At 50 of 90 target minutes, a quality-5 state produces `BEFORE_TARGET` and no notification.
- `AC-007`: At 97 of 90 minutes, a fresh, high-confidence, interruptible quality-1 state produces `WAIT_FOR_STOPPING_POINT` and no notification.
- `AC-008`: At 103 of 90 minutes, a fresh, high-confidence, interruptible quality-5 state produces `NOTIFY_NATURAL_STOP` and exactly one notification.
- `AC-009`: Missing, stale, mismatched, malformed, or confidence-below-0.80 state produces fixed-timer fallback after the target.
- `AC-010`: A structured-observation classification experiment returns a validated class, proposed strategy, confidence, and provenance; invalid AI output is rejected.
- `AC-011`: A progression-signal experiment ranks synthetic candidate changes and references supporting structured observations without receiving the raw binary fixture.
- `AC-012`: A candidate `GameProfile` round-trips through validation and versioned persistence without losing confidence or provenance.
- `AC-013`: A below-threshold or incompatible profile cannot enable contextual Runtime Mode.
- `AC-014`: A sufficiently confident synthetic profile deterministically derives the expected `GameState` without an LLM call.
- `AC-015`: No player-facing output contains checkpoint IDs, learned variables, milestone labels, or other profile/observation content.
- `AC-016`: Automated tests cover deterministic engine branches, observation/diff boundaries, AI-output validation, profile gates, and confidence fallback.

## Revised development order

1. Process detection.
2. Game identification.
3. Session tracking.
4. Filesystem observation.
5. File snapshot capture.
6. Binary/state difference analysis.
7. Structured observation storage.
8. Fake-game simulation.
9. Deterministic accountability engine.
10. AI game-classification experiment.
11. AI progression-signal ranking experiment.
12. Learned `GameProfile` format.
13. Discovery Mode prototype.
14. Runtime Mode prototype.
15. Silent Hill 2 Enhanced Edition real-world experiment.
16. Deltarune Chapter 4 evaluation.
17. Hollow Knight: Silksong evaluation.

Do not start by manually creating comprehensive checkpoint maps for the validation games.

## Initial validation games

### Silent Hill 2

“Silent Hill 2” means the original PC release with the Enhanced Edition project/mod, not the 2024 remake. It is the first major real-world test of standalone and modded detection, storefront independence, save/state observation, automatic progression-signal discovery, AI-assisted inference, and learned profiles.

### Deltarune Chapter 4

This is the mostly linear narrative test for scenes, chapter transitions, scripted sequences, and automatic narrative milestone discovery.

### Hollow Knight: Silksong

This is the nonlinear test for exploration, branching progression, bosses, benches, areas, abilities, and less predictable milestone structure.

Together, the three games test whether the discovery approach generalizes across materially different progression structures. They are research targets, not claims of current support.
