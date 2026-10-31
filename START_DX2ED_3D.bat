@echo off
cd /d "%~dp0dx2ed_3d"
py -3 dx2ed_3d.py gui
if errorlevel 1 (
  echo.
  echo Python launcher failed. Try: python dx2ed_3d.py gui
  pause
)
