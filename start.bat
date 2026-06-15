@echo off
setlocal

chcp 65001 >nul

set "APP_DIR=%~dp0"
set "APP_URL=http://127.0.0.1:8005/"

cd /d "%APP_DIR%"

start "" "%APP_URL%"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run.py
  goto :done
)

where uv >nul 2>nul
if not errorlevel 1 (
  uv run python run.py
  goto :done
)

python run.py

:done
if errorlevel 1 (
  echo.
  echo Failed to start Proton Local Toolkit.
  echo Install uv or Python dependencies, then run this file again.
  pause
)

endlocal
