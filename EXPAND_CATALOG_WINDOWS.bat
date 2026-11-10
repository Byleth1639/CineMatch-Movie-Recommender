@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\prepare_catalog.py --download
) else (
    py -3 scripts\prepare_catalog.py --download
)
if errorlevel 1 (
    echo.
    echo Download did not succeed. Try downloading movies_metadata.csv from Kaggle
    echo and run: py -3 scripts\prepare_catalog.py --input movies_metadata.csv
)
echo.
pause
