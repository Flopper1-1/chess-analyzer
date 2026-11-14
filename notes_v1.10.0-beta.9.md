## Holly's Chess Analyzer v1.10.0-beta.9 (Pre-release)

### What's New & Changed
- **Single-Instance Guard**: Opening a second instance while the app is already running now shows an error message (`Holly's Chess Analyzer is already running`) and exits instead of launching a duplicate window.
- **Merged Open / Paste PGN Tab**: Combined `Open PGN…` and `Paste PGN/FEN…` into a single **Open / Paste PGN…** toolbar tab with both **Open PGN File…** browsing and PGN/FEN text pasting in one dialog.
- **Editable Keybinds in Settings**: Moved **Keys** from the top bar into a dedicated **Keys** tab inside **Settings**, with live shortcut capture (`QKeySequenceEdit`), per-action reset, **Reset All to Defaults**, and duplicate-keybind conflict checking.
- **Cleaner Top Bar**: Removed the **Win% Guide** and **Keys** tabs from the top bar.
