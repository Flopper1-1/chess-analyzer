## Holly's Chess Analyzer v1.10.0-beta.7 (Pre-release)

### What's Fixed
- **Bulletproof Auto-Updater Overwrite & Reopen**:
  - Updated `updater.apply_windows_exe_update()` to wait for both the app process and PyInstaller's outer onefile bootloader (`ppid`), use locale-independent CSV `tasklist` checks, and replace the running `.exe` via atomic rename-swap (`target.old.<pid>` + `target.new.<pid>`) with direct-copy fallback—ensuring the `.exe` is cleanly overwritten even when Explorer or antivirus holds a read handle.
  - Fixed Windows batch script encoding/newlines (`UTF-8` with `chcp 65001` and exact CRLF line endings), detached working directory (`TEMP`), clean `DEVNULL` stdio handles, and relaunching inside the executable's own folder (`start "" /D`).
  - Added clean shutdown synchronization in `main.py` (waiting on `UpdateDownloadWorker`, immediately aborting Stockfish so `_MEI` temp files aren't locked, closing any open `SettingsDialog`, preventing duplicate concurrent downloads, and syncing `QSettings` before exiting).
  - Avoided redundant 134 MB `.exe` rewrites on startup when the embedded icon already matches the active icon, preventing Windows Defender scan locks right before updates.
