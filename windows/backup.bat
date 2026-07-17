@echo off
REM Back up MongoDB (narrative_rx DB) to a timestamped .gz file (native install).
REM Uses mongodump.exe from the local MongoDB install.
setlocal
cd /d "%~dp0.."
if not exist windows\backups mkdir windows\backups
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set dt=%%I
set stamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%_%dt:~8,2%%dt:~10,2%
set outdir=windows\backups\narrative_rx_%stamp%

REM Locate mongodump.exe (default MongoDB install path)
set MONGODUMP=
for %%V in (8.0 7.0 6.0) do (
    if exist "C:\Program Files\MongoDB\Server\%%V\bin\mongodump.exe" (
        set "MONGODUMP=C:\Program Files\MongoDB\Server\%%V\bin\mongodump.exe"
        goto :found
    )
)
where mongodump >nul 2>&1 && set "MONGODUMP=mongodump"

:found
if "%MONGODUMP%"=="" (
    echo mongodump.exe not found. Install "MongoDB Database Tools" from https://www.mongodb.com/try/download/database-tools
    pause
    exit /b 1
)

"%MONGODUMP%" --uri="mongodb://localhost:27017" --db=narrative_rx --gzip --out="%outdir%"
if errorlevel 1 (
    echo Backup failed. Is MongoDB running?  Try: net start MongoDB
    pause
    exit /b 1
)
echo.
echo Backup written to %outdir%
echo Copy the whole folder to OneDrive / USB / network share for safekeeping.
pause
