@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment...
  py -3 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
  if errorlevel 1 (
    echo Please install Python 3.10 or newer and try again.
    pause
    exit /b 1
  )
)
echo Installing required Python libraries...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Setup failed. Check the error above.
  pause
  exit /b 1
)
echo.
echo Open http://127.0.0.1:8000 in your browser.
echo Press Ctrl+C here to stop the server.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
