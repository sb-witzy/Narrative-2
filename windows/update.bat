@echo off
REM Pull the latest images from GHCR and restart.
setlocal
cd /d "%~dp0.."
echo Pulling latest images...
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
if errorlevel 1 (
    echo.
    echo Pull failed. Are the images public? Or did you run `docker login ghcr.io` first?
    pause
    exit /b 1
)
echo Restarting containers with the new images...
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
echo.
echo Narrative.Rx updated.
pause
