@echo off
REM Narrative.Rx - self-update runner.
REM This script is meant to be spawned DETACHED by the running backend
REM (see POST /api/system/update). It:
REM   1. Waits a moment so the HTTP response can complete
REM   2. Stops the NarrativeRxApp Windows Service (or NarrativeRx, whichever exists)
REM   3. git pulls the latest code
REM   4. Rebuilds Python deps + frontend
REM   5. Starts the service back up
REM Logs everything to windows\logs\update-YYYYMMDD-HHMMSS.log

setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0.."
set REPO=%CD%

REM Ensure npm-global path is on PATH even when spawned by the LocalSystem service.
REM Yarn/global npm binaries normally live under the installing user's AppData.
if exist "C:\Users\Administrator\AppData\Roaming\npm" set "PATH=%PATH%;C:\Users\Administrator\AppData\Roaming\npm"
if exist "%APPDATA%\npm" set "PATH=%PATH%;%APPDATA%\npm"
if exist "C:\Program Files\nodejs" set "PATH=%PATH%;C:\Program Files\nodejs"

if not exist windows\logs mkdir windows\logs
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set _dt=%%I
set STAMP=%_dt:~0,4%%_dt:~4,2%%_dt:~6,2%-%_dt:~8,2%%_dt:~10,2%%_dt:~12,2%
set LOG=%REPO%\windows\logs\update-%STAMP%.log

echo === Narrative.Rx update started %DATE% %TIME% ===  > "%LOG%"
echo Repo: %REPO% >> "%LOG%"

REM Give the HTTP 202 response time to reach the browser
timeout /t 3 /nobreak >nul

REM Figure out the service name (older installs used NarrativeRx, newer use NarrativeRxApp)
set SVC=
sc query NarrativeRxApp >nul 2>&1 && set SVC=NarrativeRxApp
if not defined SVC (
  sc query NarrativeRx >nul 2>&1 && set SVC=NarrativeRx
)
if not defined SVC (
  echo No NarrativeRx service found. Aborting. >> "%LOG%"
  exit /b 1
)
echo Detected service: %SVC% >> "%LOG%"

echo Stopping %SVC%... >> "%LOG%"
net stop %SVC% >> "%LOG%" 2>&1
timeout /t 2 /nobreak >nul

echo git pull... >> "%LOG%"
git pull >> "%LOG%" 2>&1
if errorlevel 1 (
  echo git pull FAILED - starting old version back up >> "%LOG%"
  net start %SVC% >> "%LOG%" 2>&1
  exit /b 1
)

echo Installing Python deps... >> "%LOG%"
call "%REPO%\backend\.venv\Scripts\python.exe" -m pip install --quiet -r "%REPO%\backend\requirements.txt" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo pip install FAILED >> "%LOG%"
  net start %SVC% >> "%LOG%" 2>&1
  exit /b 1
)

echo Rebuilding frontend... >> "%LOG%"
where yarn >> "%LOG%" 2>&1
where node >> "%LOG%" 2>&1
where git >> "%LOG%" 2>&1
pushd "%REPO%\frontend"
call yarn install --frozen-lockfile >> "%LOG%" 2>&1
if errorlevel 1 (
  popd
  echo yarn install FAILED >> "%LOG%"
  net start %SVC% >> "%LOG%" 2>&1
  exit /b 1
)
call yarn build >> "%LOG%" 2>&1
if errorlevel 1 (
  popd
  echo yarn build FAILED >> "%LOG%"
  net start %SVC% >> "%LOG%" 2>&1
  exit /b 1
)
popd

echo Starting %SVC%... >> "%LOG%"
net start %SVC% >> "%LOG%" 2>&1

echo === Update finished %DATE% %TIME% === >> "%LOG%"
endlocal
exit /b 0
