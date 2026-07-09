@echo off
setlocal

if "%~1"=="" (
  echo Usage: run-clean.cmd "input.xlsx-or-csv" [clean word 1] [clean word 2]
  exit /b 2
)

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=python"

if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  set "PYTHON_EXE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

if "%~2"=="" (
  "%PYTHON_EXE%" "%SCRIPT_DIR%tools\clean_excel_comments.py" "%~1"
) else if "%~3"=="" (
  "%PYTHON_EXE%" "%SCRIPT_DIR%tools\clean_excel_comments.py" "%~1" --clean-word "%~2"
) else (
  "%PYTHON_EXE%" "%SCRIPT_DIR%tools\clean_excel_comments.py" "%~1" --clean-word "%~2" --clean-word "%~3"
)

exit /b %ERRORLEVEL%
