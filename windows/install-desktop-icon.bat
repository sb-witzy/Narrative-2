@echo off
REM Narrative.Rx - Desktop icon installer (double-click me!)
REM This is a friendly wrapper around create-desktop-shortcut.ps1
REM for staff who don't want to open PowerShell manually.
REM
REM Both this .bat and narrative-rx.ico must sit next to create-desktop-shortcut.ps1
REM (or in the folder where a server admin dropped them).

echo.
echo   Installing Narrative.Rx desktop shortcut...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-desktop-shortcut.ps1"
echo.
pause
