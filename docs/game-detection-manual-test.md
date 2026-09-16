# Game detection manual test

## Purpose

This verifies the public running-game API, foreground selection, startup grace, and local identity confirmation. It observes processes and executable metadata read-only. It does not stop, modify, or control applications and makes no network or AI calls.

Run every command from:

```powershell
Set-Location -LiteralPath "C:\Users\offline (şimdilik)\Desktop\gametrackr\gametrackr"
```

## Test 1: no game running

Close games but leave ordinary applications and launchers open. Run:

```powershell
& ".\.venv\Scripts\python.exe" -c "from game_accountability.detection import RunningGameService; result=RunningGameService().poll(); print('Running game:', result.primary.identity.display_name if result.primary else 'None')"
```

Expected:

```text
Running game: None
```

Browsers, editors, media players, launchers, and launcher helpers must not be presented as games.

## Test 2: launch and foreground selection

Open two PowerShell windows. In the first, run this continuous observer:

```powershell
@'
import time

from game_accountability.detection import RunningGameService

service = RunningGameService()
previous = object()

print("Watching for games. Press Ctrl+C to stop.")
while True:
    result = service.poll()
    current = result.primary.identity.display_name if result.primary else None
    if current != previous:
        if result.primary is None:
            print("Running game: None")
        else:
            game = result.primary
            print(f"Running game: {game.identity.display_name}")
            print(f"Executable: {game.process.executable_name}")
            print(f"Classification: {game.classification.value}")
            print(f"Confidence: {game.confidence:.2f}")
            print(f"Foreground: {game.is_foreground}")
        previous = current
    time.sleep(1)
'@ | & ".\.venv\Scripts\python.exe" -
```

In the second window, launch a game through a recognized launcher. The game should appear after no more than a few seconds. For Overwatch through Steam, expect:

```text
Running game: Overwatch
Executable: overwatch.exe
Classification: probable_game
Confidence: 1.00
Foreground: True
```

Closing the game should return the observer to `Running game: None`. If two games are running, switch focus between their windows; the foreground game should become primary on the next poll.

## Test 3: confirm and persist an identity

With the game running, execute:

```powershell
@'
import os
from datetime import timedelta
from pathlib import Path

from game_accountability.detection import GameDetector, GameRegistry, RunningGameService

registry_path = Path(os.environ["LOCALAPPDATA"]) / "Game Accountability" / "games.json"
registry = GameRegistry.load(registry_path)
detector = GameDetector(registry)
result = RunningGameService(detector=detector, startup_grace=timedelta(0)).poll()

if result.primary is None:
    print("No game is currently available to confirm.")
else:
    game = result.primary
    registry.confirm_identity(game.identity)
    registry.save(registry_path)
    print(f"Confirmed: {game.identity.display_name}")
    print(f"Registry: {registry_path}")
'@ | & ".\.venv\Scripts\python.exe" -
```

Run Test 2 again. The same executable should now report `confirmed_game`. The registry contains only local identity aliases and confidence; it must never contain an API key.

## Automated milestone test

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests\unit\detection -v -p no:cacheprovider --basetemp=".test-temp-manual"
```

All tests should pass. The exact count may increase as the project grows.
