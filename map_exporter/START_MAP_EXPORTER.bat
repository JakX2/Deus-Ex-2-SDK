@echo off
cd /d "%~dp0map_exporter"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 dx2_map_exporter.py gui
) else (
    python dx2_map_exporter.py gui
)
if errorlevel 1 (
    echo.
    echo The exporter could not start. Install Python 3.9 or later, including tkinter.
    pause
)
