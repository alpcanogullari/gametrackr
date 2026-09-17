# Conversation context and current architecture

## Purpose and precedence

This file is the authoritative implementation handoff and current architectural context. Durable product behavior is defined in `product-spec.md`.

The architecture changed on 2026-08-28 from a primarily manual adapter/checkpoint model to deterministic observation plus AI-assisted discovery and learned profiles. Any older repository text that presents manually authored adapters or checkpoint maps as the primary scaling strategy is superseded by this file and `product-spec.md`.

## Current product direction

Game Accountability is a Windows-first desktop tool with a platform-neutral core intended to extend to macOS. A user chooses a target duration. Once the target is reached, the application either gives a fixed reminder or, when reliable game understanding exists, waits for a natural stopping point.

The application does not block games. It must not reveal spoilers. Its identity principle remains:

> Games are the platform. Storefronts are optional integrations.

Its scaling principle is now:

> Observe deterministically, interpret selectively with AI, validate with confidence, learn reusable profiles, and run deterministically whenever possible.

## Confirmed decisions

- Initial supported platform: 64-bit Windows 10 and Windows 11.
- macOS applicability: feasible and intended, but experimental until native window observation, menu-bar/tray behavior, notifications, app-bundle and launcher validation, packaging, and real game tests are complete.
- Runtime stack: Python 3.13, PySide6, psutil, watchdog, pydantic, platformdirs, and sqlite3.
- Development stack: pytest, pytest-cov, Ruff, Git, VS Code, and Codex.
- AI experiment stack: DSPy and python-dotenv.
- Explicitly excluded without a concrete approved need: LangChain, LlamaIndex, PyTorch, TensorFlow, vector databases, Redis, and Docker.
- The core accountability engine remains pure, deterministic, and game-independent.
- `Discovery Mode` learns about unknown or low-confidence games across multiple sessions.
- `Runtime Mode` uses validated profiles and deterministic extraction without routine LLM calls.
- Learned `GameProfile` data, not comprehensive manual milestone entry, is the primary scaling mechanism.
- Adapters remain, but act as standardized extraction/profile-to-`GameState` interfaces.
- Manually written parsing is an allowed exception for proprietary or unusual formats.
- All game-state observation is read-only.
- Low-confidence identity, classification, profile matching, extraction, or state causes fixed-timer fallback.
- Player-facing output is always selected from a spoiler-safe message catalog.
- Steam and other storefronts are optional evidence only.

## Architectural overview

### Layer 1: deterministic observation

Ordinary Python code performs reliable mechanical work:

- process monitoring and session timing;
- executable fingerprinting and multi-signal identity collection;
- filesystem monitoring and candidate source discovery;
- file metadata and bounded snapshot capture;
- binary or structured differences;
- timestamps and recurring-change analysis; and
- structured observation storage.

This layer produces validated, structured records. It does not ask an LLM to inspect processes, watch files, compute byte differences, or perform other deterministic tasks.

### Layer 2: AI-assisted interpretation

DSPy modules may interpret structured observations to:

- classify the game as story-driven, match-based, endless, sandbox, or hybrid;
- propose the appropriate session strategy;
- rank likely progression signals;
- correlate changes with progression;
- infer candidate milestones and stopping quality;
- build or revise candidate profiles; and
- estimate confidence and identify insufficient evidence.

AI results must pass schema validation and retain model/prompt/module version, source observation references, confidence, and creation time. They remain candidate knowledge until profile validation accepts them.

### Runtime accountability

The LLM does not decide from scratch whether the player should stop on every evaluation. Once reliable profile mappings exist, deterministic extraction derives `GameState`, and the deterministic engine applies session target, freshness, confidence, interruptibility, and stop-quality thresholds.

## Platform applicability

The current codebase can be extended to macOS without changing the core product model. Process polling, executable fingerprinting, registry persistence, AI schemas, profile concepts, and deterministic accountability should remain ordinary portable Python. Platform behavior belongs behind small adapters for process evidence, foreground-window ownership, installation/source discovery, notifications, tray or menu-bar UI, and packaging.

The current implementation includes initial macOS-shaped detection signals for Steam launcher processes, app-bundle paths, engine-marker dylibs, and common operating-system path exclusions. macOS foreground-window detection is not implemented yet; the current observer returns no foreground PID outside Windows. Therefore macOS can be used for development and deterministic test coverage, but it is not yet a supported product platform.

## Discovery Mode

Discovery Mode activates when:

- a game cannot be identified confidently;
- no compatible profile exists;
- a profile is below the contextual-runtime confidence threshold;
- the installation or state-source fingerprint no longer matches; or
- Runtime Mode reports repeated extraction failures or novel structured changes.

Flow:

```text
process detected
-> identity evidence and canonical game candidate
-> game-structure classification
-> candidate local state-source discovery
-> read-only observation
-> snapshots
-> deterministic diffs
-> structured observations
-> AI-assisted signal ranking and milestone inference
-> candidate profile build/revision
-> confidence and compatibility validation
```

Discovery is incremental and may require multiple sessions. The user still receives fixed-timer accountability while reliable contextual understanding is unavailable. Discovery work must be rate-limited and must not interfere with the game.

## Runtime Mode

Runtime Mode requires a compatible, sufficiently confident profile.

Flow:

```text
game detected
-> profile selected and compatibility checked
-> known sources monitored
-> known signals deterministically extracted
-> validated GameState derived
-> deterministic accountability policy evaluated
-> spoiler-safe notification emitted at most once
```

Runtime Mode is designed to remain fast, reproducible, and offline-capable. New observations can be retained for later profile evaluation, but an unvalidated candidate rule must not silently alter an active session's decisions.

## Confidence gates and fallback

Confidence exists at several boundaries:

- game identity;
- structure/strategy classification;
- source relevance;
- progression signal;
- milestone or stopping rule;
- profile as a whole;
- profile-to-installation compatibility; and
- derived runtime `GameState`.

Each boundary records provenance. Contextual behavior is enabled only when every required boundary passes its configured threshold. The initial standardized state threshold remains `0.80`; the initial stop-quality threshold remains `3`; state older than 30 seconds is stale.

Any missing, stale, incompatible, malformed, or below-threshold input causes deterministic `FIXED_TIMER` behavior. A previously valid profile remains versioned and recoverable if a proposed revision is rejected.

## Core data concepts

### `GameIdentity`

- canonical game ID and display name;
- executable path, metadata, hashes/fingerprints, and installation markers;
- optional storefront evidence;
- installation/mod variant evidence;
- confidence and provenance.

### `ObservationSource`

- stable source ID and associated game/install identity;
- normalized local path and source type;
- discovery evidence and access policy;
- last-seen metadata and confidence.

### `Snapshot`

- source and session IDs;
- observation time;
- file metadata and safe bounded features;
- content hash and optional locally retained content reference;
- capture method and provenance.

### `StateDiff`

- before/after snapshot references;
- deterministic structured changes such as byte ranges, keys, values, counters, and metadata;
- recurrence and temporal features;
- no AI-authored claims.

### `Interpretation`

- classification, ranked signal, milestone, or stopping-rule hypothesis;
- supporting structured observation references;
- confidence, rationale, and alternatives;
- DSPy signature/module, model, and prompt/version provenance;
- validation status.

### `GameProfile`

- canonical identity and compatible variants;
- session strategy and classification confidence;
- known state sources;
- deterministic extraction definitions or adapter references;
- signal mappings, milestone model, and stopping model;
- confidence at profile and rule levels;
- schema/content version, provenance, and validation status.

### `GameState`

- `game_id`;
- optional opaque `checkpoint_id`;
- `stop_quality` from 0 through 5;
- `interruptible`;
- confidence from 0.0 through 1.0; and
- observation time.

Only `GameState` crosses from game understanding into the core accountability engine.

## Adapter definition

Adapters are not removed. An adapter is the standardized runtime boundary that combines a compatible profile with deterministic extraction to produce a validated `GameState`.

Generic adapters may execute declarative extraction rules stored in a profile. Game-specific adapters may contain read-only parsing code for proprietary or unusual formats. Neither approach places checkpoint meanings or game names in the accountability engine.

Manual code is acceptable where required; comprehensive manual entry of every milestone is not the default discovery or scaling plan.

## Conceptual module layout

```text
src/game_accountability/
|-- core/
|   |-- accountability
|   |-- sessions
|   |-- models
|   `-- strategies
|-- detection/
|   |-- process_monitor
|   |-- game_identifier
|   |-- game_registry
|   `-- file_observer
|-- discovery/
|   |-- discovery_engine
|   |-- snapshots
|   |-- state_diff
|   |-- signal_ranker
|   `-- observation_store
|-- ai/
|   |-- signatures
|   |-- game_classifier
|   |-- progression_inference
|   |-- milestone_inference
|   |-- profile_builder
|   `-- confidence
|-- adapters/
|   |-- base
|   `-- registry
|-- profiles/
|-- observations/
|-- games/
|-- notifications/
|-- persistence/
`-- ui/

tests/
research/
```

Exact filenames may change, but these responsibilities must remain separated.

## Storage boundaries

SQLite or structured local files store:

- configured games and user settings;
- sessions and notification state;
- game identity evidence;
- observation-source metadata;
- snapshot metadata and structured diffs;
- interpretations and their provenance;
- versioned profiles and validation status.

Large or binary local artifacts, if retained, live in bounded per-user application storage and are referenced rather than embedded indiscriminately in SQLite. Retention and deletion must distinguish session history, observations, profiles, and user game files. Deleting application data must never delete source game files.

Profiles intended for future sharing must be sanitized and must not contain user paths, credentials, raw saves, or personal identifiers.

## AI, privacy, secrets, and offline behavior

Normal Runtime Mode requires no network connection. Discovery Mode may use either a local model or an explicitly configured remote provider.

For remote AI:

- use structured, minimized observations rather than complete raw files;
- require explicit configuration/consent before transmission;
- record what representation and provider were used;
- keep credentials in environment variables;
- use python-dotenv only for local development loading from an ignored `.env` file;
- never store credentials in SQLite, observations, profiles, fixtures, or logs; and
- treat provider failure as non-fatal and continue fixed-timer behavior and deterministic observation.

There is no telemetry or automatic profile upload in the initial architecture.

## Spoiler boundary

The interpretation layer and profiles may contain sensitive progression knowledge. The notifier accepts only an approved message key, never observations, interpretations, profiles, or `GameState` metadata.

Initial messages remain generic:

- `natural_stop`: “Good stopping point reached. This is a good place to wrap up for today.”
- `fixed_target`: “You've reached your planned gaming time.”

Logs shown to users must also avoid inferred milestones, checkpoint IDs, future structure, bosses, areas, or duration estimates.

## Strategy behavior

- `STORY_AWARE`: use a reliable profile and state; otherwise fall back to `FIXED_TIMER`.
- `MATCH_AWARE`: use a reliable match-boundary model; otherwise fall back to `FIXED_TIMER`.
- `HYBRID`: apply only a validated combination policy; otherwise fall back to `FIXED_TIMER`.
- `FIXED_TIMER`: requires no inferred game understanding.

Uncertain AI classification never enables a more specific strategy automatically.

## Testing expectations

- Detection tests use harmless local processes and multiple identity signals.
- Snapshot and diff tests use synthetic bounded fixtures and confirm read-only behavior.
- Observation-store tests verify session association, provenance, and retention boundaries.
- DSPy module tests use structured synthetic observations, schema validation, and stubbed model outputs.
- Profile tests verify versioning, provenance, compatibility gates, rejected revisions, and deterministic round trips.
- Runtime tests assert no AI call occurs when a valid profile is sufficient.
- Fallback tests cover unknown identity, uncertain classification, weak profile, mismatched installation, extraction failure, stale state, and malformed AI output.
- Accountability tests cover every deterministic threshold and the single-notification invariant.
- Spoiler tests ensure no internal value reaches player-facing output.

Do not commit commercial save files or personal user data as fixtures by default.

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

Do not reorder the project around manual checkpoint-map creation.

## Validation games

- Original Silent Hill 2 PC with Enhanced Edition, explicitly not the 2024 remake: standalone/modded identification, state observation, automatic signal discovery, inference, and learned profiles.
- Deltarune Chapter 4: mostly linear scenes, scripted sequences, and narrative transitions.
- Hollow Knight: Silksong: nonlinear exploration, branching progression, areas, benches, bosses, and abilities.

These are research and generalization targets, not current support claims.

## Current repository state

- Authoritative context now reflects the two-layer discovery/profile architecture.
- Python package metadata now declares DSPy, pydantic, python-dotenv, and development tooling.
- The AI discovery boundary implements validated structured observations, DSPy game classification, progression-signal ranking, explicit provider configuration, and provenance-reference checks.
- DSPy disk caching and call history are disabled by the application configuration; remote providers require explicit opt-in.
- Offline tests cover schemas, configuration safety, output validation, provenance, and a real DSPy JSON-adapter path using `DummyLM`.
- The deterministic psutil process monitor emits immutable started, running, and stopped snapshots, resolves executable paths, filters configured paths, handles inaccessible or vanished processes, and distinguishes PID reuse through creation time.
- Unit tests and a real harmless child-process integration test verify detection and exit reporting within five seconds without AI calls.
- The deterministic game identifier emits `confirmed_game`, `probable_game`, `uncertain`, `not_game`, or `launcher` results with confidence and provenance.
- Identification can match configured games by normalized executable path or bounded content fingerprint, collect read-only file/installation/engine evidence, use parent-launcher evidence, and reject known launchers, utilities, and operating-system locations.
- Identification now includes initial macOS launcher names, app-bundle installation markers, Unity/engine dylib markers, and common macOS system-path exclusions.
- Automatic game discovery requires a direct or transitive process-tree ancestor whose executable is a recognized launcher. Visible-window ownership, metadata, duration, or installation location cannot qualify an unrelated process by themselves.
- Exact configured path or fingerprint matches remain a storefront-independent override for standalone, DRM-free, and launcherless games.
- Processes inside the launcher's own installation, outside a recognized game-library root, are classified as launcher companions even when they own visible windows.
- Multi-process detection groups recognized installation processes, selects the strongest primary candidate, and classifies non-window-owning siblings as companions rather than independent games.
- `RunningGameService` is the reusable game-only API for future session/UI consumers. It filters diagnostics, deduplicates canonical game identities, and selects a foreground game as primary.
- The service applies a three-second startup grace and retains process ancestry it observed for five minutes, allowing a running game to remain identifiable after its launcher exits. It cannot reconstruct ancestry that was never observed.
- `GameRegistry` supports explicit identity confirmation plus atomic, versioned local JSON persistence of executable path and bounded fingerprint aliases.
- Weak or inaccessible evidence remains non-fatal and uncertain; the identifier performs no AI or network calls.
- No session service, observation pipeline, profile persistence, accountability engine, database, desktop UI, or production model integration has been implemented.

## Next action

Continue with step 3: implement deterministic session tracking that consumes process lifecycle and sufficiently confident game-identification results. Uncertain identity must retain fixed-timer-safe behavior, and no production model call is needed.

## Removed assumptions

- Every supported story game requires a fully manual milestone/checkpoint map before use.
- Adapters are the primary container for manually curated progression meaning.
- A fake adapter and accountability engine should be implemented before the deterministic discovery foundations.
- Real-game work begins mainly as manual save parsing and checkpoint labeling.
- A strictly no-network application model can describe optional remote AI discovery; instead, Runtime Mode is offline and remote discovery is explicit and data-minimized.

## Handoff log

### 2026-08-28 — deterministic game identification

- Added immutable identity, executable metadata, evidence, known-game, classification, and result contracts.
- Added read-only bounded executable fingerprinting and nearby marker discovery without executing or modifying game files.
- Added explainable launcher, utility, self-process, and platform system-path exclusions.
- Added confidence scoring from independent path, file, marker, lifetime, and parent-launcher evidence.
- Added read-only visible top-level window ownership as primary-process evidence.
- Added conservative primary-process gating and installation grouping so background helpers cannot qualify from game-directory membership alone.
- Added a regression fixture based on the observed Overwatch and `crashmailer_64.exe` process combination; Overwatch remains the primary candidate and the crash reporter is demoted to a companion.
- Required direct or transitive recognized-launcher ancestry for automatic probable-game classification, preventing visible applications such as browsers, editors, terminals, and media players from qualifying independently.
- Added launcher-installation companion handling for helpers such as `steamwebhelper.exe`, plus Xbox App launcher recognition.
- Added an in-memory registry for exact normalized path and fingerprint matching; unknown weak candidates remain uncertain.
- Added offline tests for stable identity, registry aliases, conservative fallback, process-tree evidence, read-only collection, and metadata access failure.

### 2026-08-29 — running-game selection milestone

- Added the reusable `RunningGameService` and immutable `RunningGame`/`RunningGamesPoll` contracts so presentation and session layers receive games rather than raw processes.
- Added foreground-window PID observation and deterministic primary selection when multiple games qualify.
- Added a three-second startup grace, canonical identity deduplication, and five-minute retention of process ancestry actually observed by the service.
- Added user confirmation, alias merging, strict versioned JSON loading, and atomic local persistence to `GameRegistry`.
- Added tests for game-only projection, foreground selection, startup grace, launcher exit/retention expiry, registry round trips, malformed registries, Windows foreground observation, and initial macOS detection markers.

### 2026-09-16 — macOS applicability statement

- Documented the product as Windows-first with a platform-neutral core intended for macOS.
- Added initial macOS detection vocabulary for Steam launcher ancestry, app-bundle install paths, engine dylib markers, and operating-system path exclusions.
- Clarified that macOS is experimental until native foreground-window observation, menu-bar/tray behavior, notifications, packaging, and real game validation are implemented.

### 2026-08-28 — deterministic process detection

- Added immutable `ProcessIdentity`, `ProcessSnapshot`, and `ProcessPoll` contracts.
- Added stateful psutil polling with started/running/stopped changes, executable-path filtering, timezone-aware timestamps, and PID-reuse handling.
- Treated access denial, vanished processes, zombie processes, and malformed metadata as non-fatal skipped observations.
- Added unit coverage plus a real child-process launch/exit integration test; process detection makes no AI calls.

### 2026-08-28 — DSPy discovery boundary

- Added DSPy 3.3-compatible signatures and modules for game classification and progression-signal ranking.
- Added bounded Pydantic input/output schemas that reject raw-content fields and unknown observation references.
- Added `.env`-based configuration with explicit remote-provider opt-in, disabled DSPy caching/history, and no committed secrets.
- Added support for OpenAI's standard `OPENAI_API_KEY` environment variable while retaining the project-specific key as a compatibility override.
- Added package metadata, usage documentation, and offline tests with 94% coverage of the AI package.

### 2026-08-28 — discovery architecture revision

- Replaced the manual-adapter-first scaling model with deterministic observation, AI-assisted interpretation, and learned profiles.
- Added Discovery Mode and Runtime Mode.
- Redefined adapters as deterministic extraction/profile-to-`GameState` boundaries.
- Added confidence and provenance across identity, interpretations, profiles, and runtime state.
- Added DSPy and python-dotenv to the intended stack.
- Reordered development around detection, observation, diffs, and structured evidence before AI experiments.
- Retained storefront independence, read-only game access, deterministic accountability, fixed fallback, spoiler safety, and the three validation games.
