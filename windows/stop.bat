@echo off
REM Stop Narrative.Rx on this machine (Podman + Hyper-V).
setlocal
cd /d "%~dp0.."
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml down
echo.
echo Narrative.Rx stopped. Your saved narratives are safe in the mongo-data volume.
echo (The podman machine (Hyper-V VM) is still running. Stop it too with:  podman machine stop)
pause
