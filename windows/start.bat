@echo off
REM Start Narrative.Rx on this Windows Server (native install).
setlocal
sc query MongoDB | findstr "RUNNING" >nul || net start MongoDB
net start NarrativeRx
if errorlevel 2 (
    echo.
    echo Failed to start. Check the log at windows\logs\service-stderr.log
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
