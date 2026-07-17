@echo off
REM Start Narrative.Rx on this machine (Podman + Hyper-V).
REM Double-click, or run from cmd.

setlocal
cd /d "%~dp0.."

REM Make sure the podman machine (Hyper-V VM) is up first
podman machine start 2>nul

podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
if errorlevel 1 (
    echo.
    echo Failed to start. Common causes:
    echo   - Podman machine isn't running:   podman machine start
    echo   - Hyper-V VM not created yet:     re-run windows\setup.ps1
    echo   - podman-compose missing:         pip install podman-compose
    pause
    exit /b 1
)
echo.
echo Narrative.Rx is running.
echo   This machine:       http://localhost:8080
echo   From other office PCs, use this machine's LAN IP -- for example:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
    for /f "tokens=* delims= " %%b in ("%%a") do echo   http://%%b:8080
    goto :done
)
:done
echo.
pause
