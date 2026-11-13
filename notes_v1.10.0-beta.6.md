## Holly's Chess Analyzer v1.10.0-beta.6 (Pre-release)

### What's Fixed
- **Revert to Stable Channel & Update UI**:
  - Closing the Settings dialog automatically once a channel switch download starts so the main window's download progress bar and status are visible.
  - Showing a warning dialog if an interactive update download or apply step fails instead of failing silently behind Settings.
  - Using a daemon `threading.Timer` fallback for process exit after `QApplication.quit()` and `CREATE_NO_WINDOW` (without conflicting `DETACHED_PROCESS`) for the updater helper script.
