@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (py -3 dx2_actor_explorer.py --gui) else (python dx2_actor_explorer.py --gui)
if errorlevel 1 (
  echo.
  echo Python 3.9+ is required.
  pause
)
