@echo off
REM Stop Narrative.Rx on this machine.
setlocal
cd /d "%~dp0.."
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml down
echo.
echo Narrative.Rx stopped. Your saved narratives are safe in the Docker volume.
pause
