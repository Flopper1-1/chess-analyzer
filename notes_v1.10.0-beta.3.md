## Holly's Chess Analyzer v1.10.0-beta.3 (Pre-release)

### Fixes
- **Auto-Updater Fixed**:
  - Replaced `timeout /t 1` (which exited immediately with redirected stdin in detached/no-window batch scripts) with `ping` + a 25-attempt `copy /Y` retry loop so PyInstaller's onefile bootloader finishes releasing the `.exe` lock before replacement.
  - Closed all top-level windows and ensured clean process exit (`os._exit(0)`) after launching the updater script.
  - Fixed **Check for Updates Now** on pre-release builds to check for newer pre-releases instead of only stable releases.
