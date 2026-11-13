## Holly's Chess Analyzer v1.10.0-beta.5 (Pre-release)

### What's Fixed
- **Auto-Updater Relaunch (Error -3) & Update Loop Fixed**:
  - Cleared inherited PyInstaller bootloader environment variables (`_MEIPASS2`, `_PYI_*`) and set `PYINSTALLER_RESET_ENVIRONMENT=1` when relaunching after an update so the new executable extracts cleanly instead of failing with `Error -3`.
  - Added atomic `.part` download staging, `Content-Length` verification, and Windows executable (`MZ`) header validation in `download_update()`.
  - Increased file-replacement retry window to 40 attempts so the outer PyInstaller bootloader has plenty of time to release the `.exe` lock.
