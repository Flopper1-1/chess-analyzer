$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m pip install PySide6 chess pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "Holly's Chess Analyzer" --icon icon.ico --add-data "icon.ico;." `
  --add-binary "assets\stockfish.exe;assets" `
  --add-data "assets\openings;assets\openings" `
  --add-data "LICENSES;LICENSES" --add-data "assets\icons;assets\icons" `
  --add-data "assets\sounds;assets\sounds" `
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtPdf `
  main.py
try {
    Copy-Item "dist\Holly's Chess Analyzer.exe" "$env:USERPROFILE\Downloads\Holly's Chess Analyzer.exe" -Force
} catch {
    Write-Warning "Could not overwrite $env:USERPROFILE\Downloads\Holly's Chess Analyzer.exe (file is currently running)."
}
