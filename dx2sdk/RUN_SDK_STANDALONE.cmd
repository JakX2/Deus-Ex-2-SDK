@echo off
rem DX2SDK v0.4 source-only portable Python CLI. No Godot runtime required.
rem Python 3.11+ is required, using python or the official py launcher.
setlocal EnableExtensions
cd /d "%~dp0"
set "SDK_PYTHON="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "SDK_PYTHON=%%P"
)
if not defined SDK_PYTHON (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "SDK_PYTHON=%%P"
  )
)
if not defined SDK_PYTHON (
  echo DX2SDK requires Python 3.11 or newer.
  exit /b 1
)
if "%~1"=="" (
  "%SDK_PYTHON%" -B -m dx2sdk --help
) else (
  "%SDK_PYTHON%" -B -m dx2sdk %*
)
exit /b %errorlevel%
