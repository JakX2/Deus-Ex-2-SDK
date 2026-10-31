@echo off
setlocal
set "APP=%~dp0map_exporter"
if not exist "%APP%\dx2_map_exporter.py" set "APP=%~dp0"
cd /d "%APP%"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 dx2_map_exporter.py gui
) else (
    python dx2_map_exporter.py gui
)
if errorlevel 1 (
    echo.
    echo Could not start DX2 Map Exporter. Install Python 3.9 or later with tkinter.
    pause
)
