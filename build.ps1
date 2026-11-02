$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m pip install PySide6 chess pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name ChessAnalyzer --icon icon.ico --add-data "icon.ico;." `
  --add-binary "assets\stockfish.exe;assets" `
  --add-data "assets\openings;assets\openings" `
  --add-data "LICENSES;LICENSES" --add-data "assets\icons;assets\icons" `
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtPdf `
  main.py
Copy-Item dist\ChessAnalyzer.exe "$env:USERPROFILE\Downloads\ChessAnalyzer.exe" -Force
