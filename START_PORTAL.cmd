@echo off
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=2
".venv\Scripts\python.exe" "scripts\portal_preflight.py"
if errorlevel 1 (
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8765 in your browser after the server starts.
echo Sign-in details are in runtime\portal\LOCAL_ACCESS.txt
echo Keep this window open. Press Ctrl+C to stop the portal.
".venv\Scripts\python.exe" "scripts\serve_portal.py"
pause
