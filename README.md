# WatchdawgAI

<<<<<<< HEAD
Game Accountability is a Windows-first desktop application with a platform-neutral core that is intended to extend to macOS. It helps players keep gaming sessions within their plans without interrupting them at a bad in-game moment by combining deterministic local observation, AI-assisted discovery, learned game profiles, and a deterministic spoiler-free accountability engine.

## Platform status

The current MVP target remains 64-bit Windows 10 and Windows 11. The existing process monitoring, game identity registry, executable fingerprinting, and AI discovery boundaries are ordinary Python and can run on macOS.

macOS support is feasible, but experimental until native foreground-window observation, tray/menu-bar behavior, notifications, launcher evidence, app-bundle paths, and manual game-detection validation are completed. Unknown or weakly identified games still fall back to fixed-timer behavior.
=======
WatchdawgAI is a Windows desktop application that helps players keep gaming sessions within their plans without interrupting them at a bad in-game moment. It combines deterministic local observation, AI-assisted discovery, learned game profiles, and a deterministic spoiler-free accountability engine.
>>>>>>> cdaa541b227d3af5170e35ea80cdb850a790ab0b

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

Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
```

macOS:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
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

Game identification performs read-only bounded executable fingerprinting, inspects nearby engine/storefront markers, rejects known launchers and system utilities, considers process-tree, visible-window, and installation-path evidence, and matches configured identities by exact normalized path or fingerprint. Automatic discovery requires the candidate to be a direct or transitive child of a recognized launcher. Exact configured matches remain the explicit override for standalone and DRM-free games. Launcher-owned UI helpers and non-primary installation siblings are labeled `companion`. The detector includes initial macOS launcher, app-bundle, and engine-marker signals, while foreground-window selection is still Windows-only.

`RunningGameService` is the reusable game-only boundary for session and UI code. It applies a three-second startup grace, retains ancestry observed during the last five minutes, deduplicates game identities, and selects the foreground game as primary. User-confirmed identities can round-trip through the versioned local JSON `GameRegistry`. See `docs/game-detection-manual-test.md` for a live test.

The next product step is deterministic session tracking for recognized games.
