@echo off
REM Pull the latest code from GitHub, rebuild, and restart the service.
setlocal
cd /d "%~dp0.."

echo Stopping NarrativeRx service...
net stop NarrativeRx 2>nul

echo Pulling latest code from GitHub...
git pull
if errorlevel 1 (
    echo git pull failed. Resolve conflicts manually then re-run this script.
    net start NarrativeRx
    pause
    exit /b 1
)

echo Updating Python dependencies...
call backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
if errorlevel 1 (
    echo pip install failed. Check messages above.
    pause
    exit /b 1
)

echo Rebuilding frontend (3-5 min)...
pushd frontend
call yarn install --frozen-lockfile
if errorlevel 1 ( popd & echo yarn install failed & pause & exit /b 1 )
call yarn build
if errorlevel 1 ( popd & echo yarn build failed & pause & exit /b 1 )
popd

echo Starting NarrativeRx service...
net start NarrativeRx

echo.
echo Update complete. App is live again on http://localhost:8080
pause
