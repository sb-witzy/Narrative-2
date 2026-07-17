@echo off
REM Stop Narrative.Rx on this Windows Server (native install).
REM MongoDB is NOT stopped - other apps may use it.
setlocal
net stop NarrativeRx
echo.
echo Narrative.Rx stopped. Your data is safe in the local MongoDB.
pause
