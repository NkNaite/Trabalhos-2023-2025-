
@echo off
echo Starting Pax Dei Advisor Dashboard...
echo Open your browser at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.
echo Syncing data from Hugging Face...
D:\py\python.exe scripts/sync_data.py
echo.
D:\py\python.exe src/server.py
pause
".\start_dashboard.bat"