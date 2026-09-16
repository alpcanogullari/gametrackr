# Game Accountability: project brief

## What this project is

Game Accountability is a Windows desktop application that helps players stay within a planned gaming duration without interrupting them at a poor moment in the game.

When the target time is reached, the application either gives a normal timer reminder or waits for a reliable natural stopping point. All player-facing guidance remains spoiler-free.

## How the project documents work

- `AGENTS.md` contains the rules contributors and coding agents must follow.
- `docs/product-spec.md` defines the product behavior, requirements, acceptance criteria, and development order.
- `docs/conversation-context.md` records the current architecture, confirmed decisions, project state, and next action.
- This document is a short orientation guide. It summarizes the authoritative documents but does not replace them.

If documents conflict, follow `product-spec.md` and `conversation-context.md`, then the user's latest explicit instruction.

## Architecture at a glance

The system separates reliable mechanical observation from AI-assisted interpretation:

```text
Running game
    |
    v
Deterministic detection and observation
(processes, fingerprints, files, snapshots, diffs)
    |
    v
Structured observations
    |
    v
AI-assisted interpretation during discovery
(classification, signal ranking, milestone inference)
    |
    v
Versioned, confidence-scored GameProfile
    |
    v
Deterministic Runtime Mode -> GameState -> accountability engine
    |
    v
Spoiler-free notification
```

AI is used to help learn what game-state changes mean. It is not used for routine process monitoring, file comparison, or deciding from scratch whether the player should stop during every runtime check.

## Discovery Mode and Runtime Mode

`Discovery Mode` is used for unknown games or profiles with insufficient confidence. It observes local state read-only, creates structured differences, and may use DSPy/LLM modules to propose progression signals, milestones, and profile rules across multiple sessions. Until confidence is sufficient, accountability falls back to a fixed timer.

`Runtime Mode` loads a validated game profile, deterministically extracts known signals, produces a standardized `GameState`, and runs the deterministic accountability engine. It is designed to be fast, reproducible, and offline-capable.

## Core runtime state

Adapters convert profile-guided or game-specific extraction into a common state:

```python
GameState(
    game_id="...",
    checkpoint_id=None,
    stop_quality=0,
    interruptible=True,
    confidence=0.0,
)
```

The accountability engine contains no game-specific logic. A story-aware notification requires the target time to be reached, stop quality of at least `3`, `interruptible=True`, confidence of at least `0.80`, and fresh state. Unreliable input falls back to `FIXED_TIMER`.

## Key architectural guarantees

- Games are primary; Steam and other storefronts are optional metadata sources.
- Game saves, logs, configuration, and local state are observed read-only.
- Raw binary saves are not sent to an LLM by default.
- AI interpretations and learned rules retain confidence, versioning, and provenance.
- Learned profiles are the main scaling mechanism; comprehensive manual checkpoint maps are not.
- Adapters remain available for deterministic extraction and unusual proprietary formats.
- Runtime accountability remains deterministic and sends at most one reminder per session.
- Notifications never expose checkpoints, future areas, bosses, story events, or learned variables.

## Technology direction

The Windows-first stack uses Python 3.13, PySide6, psutil, watchdog, pydantic, platformdirs, sqlite3, pytest, pytest-cov, and Ruff. DSPy and python-dotenv support controlled AI discovery experiments.

Large AI frameworks and infrastructure such as LangChain, LlamaIndex, PyTorch, TensorFlow, vector databases, Redis, and Docker are excluded unless a concrete requirement later justifies them.

## Current status

The DSPy discovery boundary and deterministic process monitor are implemented with offline tests. The monitor reports executable paths and process lifecycle changes without using AI. Game identification, session tracking, the observation pipeline, profiles, runtime engine, persistence, and UI are not yet implemented. The next development step is storefront-independent game identification from process evidence.

The initial research games are the original Silent Hill 2 PC release with Enhanced Edition, Deltarune Chapter 4, and Hollow Knight: Silksong. They are validation targets, not currently supported games.
