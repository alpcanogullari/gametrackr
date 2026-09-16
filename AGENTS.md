# Codex Project Instructions

Before making architectural, product-behaviour, or implementation changes, read completely:

1. `docs/product-spec.md`
2. `docs/conversation-context.md`

Treat those files as the authoritative description of the current product and architecture. If another repository document or existing implementation conflicts with them, prefer these documents unless the user explicitly provides a newer instruction.

## Core architectural rules

- Keep the runtime accountability engine deterministic and free of game-specific logic.
- Separate deterministic observation from AI-assisted interpretation.
- Use ordinary Python code for process detection, fingerprinting, file discovery, snapshots, diffs, timestamps, recurring-change analysis, and structured observation storage.
- Do not use an LLM for work that deterministic code can perform reliably.
- AI may classify game structure, rank progression signals, infer milestones, estimate stopping quality, and construct or improve candidate game profiles.
- AI should reason over structured observations. Do not send complete binary saves or raw game files to an LLM by default.
- Treat all AI-generated interpretations as hypotheses with provenance and confidence, never as automatically correct rules.
- Use `Discovery Mode` for unknown or insufficiently understood games and `Runtime Mode` for games with sufficiently reliable learned profiles.
- Prefer deterministic profile-based extraction during Runtime Mode. Do not query an LLM on every polling cycle or routine session when a reliable mapping exists.
- Fall back to `FIXED_TIMER` whenever game identity, classification, profile, extracted state, or interpretation confidence is insufficient.

## Games, profiles, and adapters

- The game is the primary entity. Storefront APIs are optional metadata sources; Steam must never be required for core operation.
- Identify games using multiple local signals where possible, including executable path, executable metadata or fingerprint, installation files, window metadata, and known local state locations.
- Learned `GameProfile` data is the primary scaling mechanism for game understanding.
- Profiles must be versioned, confidence-scored, provenance-aware, and capable of incremental improvement across sessions.
- Adapters remain a standardized runtime interface between deterministic extraction, learned profiles, and the common `GameState`.
- Manually written parsing code is allowed for proprietary or unusual formats, but manually authoring every boss, area, chapter, checkpoint, and stopping point is not the default strategy.
- Keep game-specific extraction or parsing code out of the core engine.
- Save-file, log, configuration, and local-state readers must be read-only.

## Safety and product rules

- Never expose upcoming story information, internal progression variables, milestone labels, or checkpoint identifiers to the player.
- Player-facing notification text must come from a spoiler-safe catalog and must not interpolate learned-profile or observation details.
- Store confidence with classifications, inferred signals, milestones, profile rules, and runtime `GameState` values.
- Preserve structured observation provenance so learned rules can be audited and revised.
- Keep normal Runtime Mode offline-capable. Any remote AI use in Discovery Mode must be explicit, data-minimized, and limited to structured observations.
- Never commit secrets. Load optional AI credentials from environment variables, with local development support through an ignored `.env` file.

## Development rules

- Use the Windows-first Python 3.13 stack documented in `docs/conversation-context.md`.
- Do not introduce LangChain, LlamaIndex, PyTorch, TensorFlow, vector databases, Redis, or Docker without a concrete approved requirement.
- Prefer testable, modular Python with explicit boundaries between core, detection, discovery, AI, adapters, profiles, observations, games, notifications, persistence, and UI.
- Add tests for deterministic observations, profile validation, confidence fallback, and every core accountability decision.
- Use synthetic fixtures for discovery tests; do not commit copyrighted or personal save data by default.
- Do not begin comprehensive manual checkpoint mapping for validation games.
- Keep `docs/conversation-context.md` current when an architectural decision, milestone status, or next action changes.

## Initial validation games

- “Silent Hill 2” means the original PC release with Enhanced Edition, not the 2024 remake.
- Deltarune Chapter 4 is the mostly linear narrative validation case.
- Hollow Knight: Silksong is the nonlinear exploration validation case.

