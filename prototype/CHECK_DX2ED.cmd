@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "DX2ED_PYTHON="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "DX2ED_PYTHON=python"
if not defined DX2ED_PYTHON (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 set "DX2ED_PYTHON=py -3"
)
if not defined DX2ED_PYTHON (
  echo DX2Ed requires Python 3.11 or newer on PATH or via the Windows py launcher.
  echo Install the standard Python distribution and enable Add Python to PATH.
  exit /b 1
)
%DX2ED_PYTHON% "%~dp0prototype_doctor.py" --root "%~dp0."
exit /b %errorlevel%
