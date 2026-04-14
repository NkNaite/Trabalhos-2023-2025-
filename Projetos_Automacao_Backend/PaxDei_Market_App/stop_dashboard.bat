@echo off
echo Stopping Pax Dei Advisor Dashboard...
powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Dashboard stopped successfully.
) else (
    echo.
    echo Dashboard was not running or could not be found on port 8000.
)
timeout /t 3
