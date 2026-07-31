@echo off
REM Narrative.Rx - installer-based self-update runner.
REM Spawned DETACHED by POST /api/system/update when the app was installed
REM via NarrativeRx-Setup-<version>.exe (i.e. no git checkout available).
REM
REM Flow:
REM   1. Waits a moment so the HTTP response can reach the browser
REM   2. Reads latest release URL from arg %1 (backend queries GitHub)
REM   3. Downloads the new .exe to %TEMP%
REM   4. Runs it with /SILENT /SUPPRESSMSGBOXES /NORESTART
REM   5. The Inno Setup upgrade handles service stop/start automatically
REM Logs everything to %ProgramData%\NarrativeRx\logs\update-YYYYMMDD-HHMMSS.log

setlocal enableextensions enabledelayedexpansion

set DOWNLOAD_URL=%~1
if "%DOWNLOAD_URL%"=="" (
  echo No download URL supplied. 1>&2
  exit /b 2
)

set LOGDIR=%ProgramData%\NarrativeRx\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set _dt=%%I
set STAMP=%_dt:~0,4%%_dt:~4,2%%_dt:~6,2%-%_dt:~8,2%%_dt:~10,2%%_dt:~12,2%
set LOG=%LOGDIR%\update-%STAMP%.log
set SETUP=%TEMP%\NarrativeRx-Setup-latest.exe

echo === Narrative.Rx installer update started %DATE% %TIME% === > "%LOG%"
echo URL: %DOWNLOAD_URL% >> "%LOG%"
echo Target: %SETUP% >> "%LOG%"

REM Give the HTTP response time to reach the browser
timeout /t 3 /nobreak >nul

echo Downloading new installer... >> "%LOG%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%SETUP%' -UseBasicParsing -TimeoutSec 600 } catch { Write-Error $_; exit 1 }" ^
  >> "%LOG%" 2>&1

if not exist "%SETUP%" (
  echo Download FAILED - installer not found at %SETUP% >> "%LOG%"
  exit /b 1
)

for %%A in ("%SETUP%") do set SIZE=%%~zA
echo Downloaded %SIZE% bytes >> "%LOG%"
if %SIZE% LSS 10000000 (
  echo Download too small - probably an error page. Aborting. >> "%LOG%"
  del /q "%SETUP%" >nul 2>&1
  exit /b 1
)

echo Running silent upgrade... >> "%LOG%"
REM Inno Setup with matching AppId detects existing install and upgrades in place.
REM The [Run] section of the .iss stops+restarts the NarrativeRxApp service for us.
"%SETUP%" /SILENT /SUPPRESSMSGBOXES /NORESTART /LOG="%LOGDIR%\innosetup-%STAMP%.log"
set RC=%ERRORLEVEL%
echo Installer exit code: %RC% >> "%LOG%"

del /q "%SETUP%" >nul 2>&1

echo === Update finished %DATE% %TIME% === >> "%LOG%"
exit /b %RC%
