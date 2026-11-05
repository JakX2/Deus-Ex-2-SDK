@echo off
rem DX2SDK v0.1 public Python API/CLI. Uses the same interpreter checked
rem by START_DX2ED, and ships with all source-only dependencies.
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0CHECK_DX2ED.cmd"
if errorlevel 1 (
  echo DX2SDK cannot run until the source-only checks pass.
  exit /b 1
)
if "%~1"=="" (
  "%DX2ED_PYTHON_EXE%" -B -m dx2sdk --help
) else (
  "%DX2ED_PYTHON_EXE%" -B -m dx2sdk %*
)
exit /b %errorlevel%
