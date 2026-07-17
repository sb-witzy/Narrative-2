@echo off
REM Pull the latest images from GHCR and restart (Podman + Hyper-V).
setlocal
cd /d "%~dp0.."
podman machine start 2>nul
echo Pulling latest images...
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
if errorlevel 1 (
    echo.
    echo Pull failed. Are the images public on GHCR? Or did you run `podman login ghcr.io` first?
    pause
    exit /b 1
)
echo Restarting containers with the new images...
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
echo.
echo Narrative.Rx updated.
pause
