@echo off
REM Start Narrative.Rx on this machine.
REM Double-click, or run from cmd.

setlocal
cd /d "%~dp0.."
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
if errorlevel 1 (
    echo.
    echo Failed to start. Is Docker Desktop running?
    echo Open Docker Desktop and wait for the whale icon to stop animating, then try again.
    pause
    exit /b 1
)
echo.
echo Narrative.Rx is running.
echo   This machine:       http://localhost:8080
echo   From other office PCs, use this machine's IP -- for example:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
    for /f "tokens=* delims= " %%b in ("%%a") do echo   http://%%b:8080
    goto :done
)
:done
echo.
pause
