# Chess Game Analyzer (Stockfish)

A desktop chess game analysis application built with **PySide6 (Qt)** and **Stockfish 17.1**, packaged as a standalone Windows executable.

Analyze games with full move annotations, interactive best move sequences, opening book classification, live accuracy/ratings breakdown, customizable symbols, and background execution.

---

## Features

- **In-Depth Game & Move Annotations:**
  - `!!` **Brilliant:** Discovered sacrifices and tactical turnarounds
  - `!` **Great:** High-impact best find
  - `★` **Best:** Engine's primary recommended move
  - `👍` **Excellent:** Strong continuation maintaining advantage
  - `✓` **Good:** Solid move
  - `/` **Book:** Recognizes openings from the Lichess chess-openings dataset (A–E)
  - `?!` **Inaccuracy:** Suboptimal move (5–10% win loss)
  - `?` **Mistake:** Serious positional concession (10–20% win loss)
  - `??` **Blunder:** Decisive game-altering mistake (>20% win loss)
  - `✗` **Miss:** Missed winning tactic/continuation
  - `→` **Forced:** Only legal response available
- **Visual Board Markers & Alternatives:**
  - Highlights inaccuracies, mistakes, blunders, and misses with an on-board arrow showing the best alternative move (`alt`).
  - Terminal badges on kings for checkmate, draw, or resignation.
- **Evaluation & Accuracies:**
  - Real-time streaming evaluation graph with interactive hover tooltips showing position and score.
  - Phase-based accuracy breakdown (Opening, Middlegame, Endgame) and estimated rating.
  - White/Black POV evaluation bar with numerical display.
- **Engine Control & Presets:**
  - Multi-threaded Stockfish analysis with customizable hash memory and depth.
  - Presets: Low (fast), Medium, High (accurate), and Custom with an interactive slider that dynamically optimizes threads and hash table allocation based on CPU capabilities.
  - Selective analysis scope: All moves, My side only, or My side + any brilliants.
  - Lenient brilliants toggle.
- **Customizable UI & MS Paint Integration:**
  - Toggle between modern icon assets and legacy text/color annotations.
  - One-click "Edit in Paint" button for each annotation badge, with live preview and instant reset.
- **Performance & Background Execution:**
  - Automatic thread execution state management prevents Windows from throttling the engine when minimized or tabbed out.
  - Taskbar progress and desktop notification when analysis finishes.
  - Auto-flips board to your perspective when matching player name.
- **Exporting & Sharing:**
  - Export games to annotated PGN format with NAGs, `%eval` comments, and opening identifiers.

---

## Architecture & Project Structure

- `main.py` — PySide6 application window, board renderer, interactive graph, and settings dialog.
- `analysis.py` — Engine pipeline, asynchronous analysis queue, MultiPV evaluation, and resource auto-scaling.
- `classify.py` — Win-probability curve conversion, tactical sacrifice detection, and move classification heuristics.
- `accuracy.py` — Harmonics-weighted accuracy calculation by game phase and Elo estimation.
- `openings.py` — Opening book lookup indexing Lichess TSV datasets by board EPD.
- `styles.py` — Symbol and palette styling persistence.
- `icons.py` — Badge asset management, user directory overrides, and MS Paint spawning.
- `winutil.py` — Windows API process throttle mitigation and power state management.
- `build.ps1` — PyInstaller standalone binary build script.

---

## Building from Source

### Prerequisites
- Python 3.12+
- Windows x64 (AVX2 support recommended)

```powershell
pip install -r requirements.txt
python -m pytest tests
.\build.ps1
```

---

## License

GPL-3.0 License (Stockfish bundled under GPLv3, Lichess opening database under CC0).

