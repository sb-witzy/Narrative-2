@echo off
REM Launcher for Narrative.Rx desktop / Start Menu shortcut.
REM 1. If no LLM key is configured yet, launch the first-run wizard.
REM 2. Ensure the service is running.
REM 3. Open the app in the default browser.

setlocal enableextensions
set CFG=%ProgramData%\NarrativeRx\.env
set NEEDS_SETUP=1
if exist "%CFG%" (
    findstr /R /C:"^EMERGENT_LLM_KEY=..*" "%CFG%" >nul 2>&1 && set NEEDS_SETUP=0
)

if "%NEEDS_SETUP%"=="1" (
    if exist "%~dp0firstrun.exe" (
        REM Blocks until the user closes the wizard.
        "%~dp0firstrun.exe"
    )
)

sc query NarrativeRxApp | findstr "RUNNING" >nul
if errorlevel 1 (
    net start NarrativeRxApp >nul 2>&1
    REM Give uvicorn a couple of seconds to bind port 8080
    timeout /t 3 /nobreak >nul
)
start "" "http://localhost:8080"
