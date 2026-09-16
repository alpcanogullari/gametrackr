# Game Accountability

Game Accountability is a Windows desktop application that helps players keep gaming sessions within their plans without interrupting them at a bad in-game moment. It combines deterministic local observation, AI-assisted discovery, learned game profiles, and a deterministic spoiler-free accountability engine.

## Context and specifications

Read `AGENTS.md` first. The authoritative project documents are:

- `docs/product-spec.md`: product scope, requirements, and acceptance criteria.
- `docs/conversation-context.md`: current architecture, state, milestones, and next action.
- `docs/project-brief.md`: short orientation to the product and architecture.

## Planned stack

- Python 3.13, 64-bit
- PySide6
- psutil, watchdog, pydantic, and platformdirs
- SQLite through Python's built-in `sqlite3`
- DSPy and python-dotenv for controlled AI discovery experiments
- pytest, pytest-cov, and Ruff

## Development setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
```

Copy `.env.example` to `.env` only when configuring a real model. OpenAI credentials use `OPENAI_API_KEY`, and remote providers require `GAME_ACCOUNTABILITY_AI_ALLOW_REMOTE=true`; tests make no network or model calls. See `docs/dspy-integration.md`.

## Repository layout

```text
.
|-- AGENTS.md
|-- README.md
|-- docs/
|   |-- product-spec.md
|   |-- conversation-context.md
|   |-- project-brief.md
|   |-- dspy-integration.md
|   `-- game-detection-manual-test.md
|-- src/game_accountability/
|   |-- ai/
|   `-- detection/
`-- tests/
```

## Development status

The safe DSPy discovery boundary, deterministic process monitor, and first storefront-independent game-identification component are implemented. Process polling reports immutable started, running, and stopped snapshots, supports executable-path filtering, tolerates inaccessible processes, records parent PIDs, and distinguishes PID reuse with process creation time.

Game identification performs read-only bounded executable fingerprinting, inspects nearby engine/storefront markers, rejects known launchers and system utilities, considers process-tree, visible-window, and installation-path evidence, and matches configured identities by exact normalized path or fingerprint. Automatic discovery requires the candidate to be a direct or transitive child of a recognized launcher. Exact configured matches remain the explicit override for standalone and DRM-free games. Launcher-owned UI helpers and non-primary installation siblings are labeled `companion`.

`RunningGameService` is the reusable game-only boundary for session and UI code. It applies a three-second startup grace, retains ancestry observed during the last five minutes, deduplicates game identities, and selects the foreground game as primary. User-confirmed identities can round-trip through the versioned local JSON `GameRegistry`. See `docs/game-detection-manual-test.md` for a live test.

The next product step is deterministic session tracking for recognized games.
