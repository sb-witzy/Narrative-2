@echo off
REM Launcher for Narrative.Rx desktop / Start Menu shortcut.
REM Ensures the service is running, then opens the app in the default browser.
sc query NarrativeRxApp | findstr "RUNNING" >nul
if errorlevel 1 (
    net start NarrativeRxApp >nul 2>&1
    REM Give uvicorn a couple of seconds to bind port 8080
    timeout /t 3 /nobreak >nul
)
start "" "http://localhost:8080"
