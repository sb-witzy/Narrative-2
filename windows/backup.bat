@echo off
REM Back up MongoDB to a timestamped .gz file in windows\backups\ (Podman + Hyper-V).
setlocal
cd /d "%~dp0.."
if not exist windows\backups mkdir windows\backups
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set dt=%%I
set stamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%_%dt:~8,2%%dt:~10,2%
set outfile=windows\backups\narrative_rx_%stamp%.gz
podman exec narrative-rx-mongo mongodump --archive --gzip --db narrative_rx > "%outfile%"
if errorlevel 1 (
    echo Backup failed. Is the app running?  Try:  windows\start.bat
    pause
    exit /b 1
)
echo.
echo Backup written to %outfile%
pause
