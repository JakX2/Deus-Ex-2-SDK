@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if "%~1"=="" (
  echo DX2Ed owner-map resource diagnostic.
  echo Drag an original Deus Ex: Invisible War .gmp file onto DIAGNOSE_GMP.cmd.
  echo This only checks local GMP and IBD discovery, not actual map decoding.
  pause
  exit /b 2
)
call "%~dp0CHECK_DX2ED.cmd"
if errorlevel 1 (
  echo DX2Ed Python / worker readiness check failed.
  pause
  exit /b 1
)
echo Checking only local original GMP and IBD resource discovery...
"%DX2ED_PYTHON_EXE%" "%~dp0map_import_preflight.py" --map "%~f1"
set "DX2ED_RESULT=%ERRORLEVEL%"
if "%DX2ED_RESULT%"=="0" (
  echo Resource files located. Try dropping this GMP onto START_DX2ED.cmd.
) else (
  echo Resource discovery was refused. Confirm original mission IBD is present.
  echo You can still select IBD override from inside DX2Ed.
)
echo.
echo No original game files were modified, cached, copied or uploaded.
pause
exit /b %DX2ED_RESULT%
