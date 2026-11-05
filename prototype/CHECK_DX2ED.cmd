@echo off
rem This helper is CALLed by START_DX2ED.cmd. Deliberately no SETLOCAL:
rem pass the absolute Python executable verified below into the Godot process.
cd /d "%~dp0"
set "DX2ED_PYTHON_EXE="
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "DX2ED_PYTHON_EXE=%%P"
)
if not defined DX2ED_PYTHON_EXE (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "DX2ED_PYTHON_EXE=%%P"
  )
)
if not defined DX2ED_PYTHON_EXE (
  echo DX2Ed requires Python 3.11 or newer on PATH or via the Windows py launcher.
  echo Install Python, then rerun CHECK_DX2ED.cmd.
  exit /b 1
)
if not exist "%DX2ED_PYTHON_EXE%" (
  echo Python preflight returned a missing interpreter.
  set "DX2ED_PYTHON_EXE="
  exit /b 1
)
"%DX2ED_PYTHON_EXE%" "%~dp0prototype_doctor.py" --root "%~dp0."
exit /b %errorlevel%
