@echo off
title RMKCET Parent Connect
color 0A
echo.
echo  ============================================
echo   RMKCET Parent Connect
echo   Starting server...
echo  ============================================
echo.

:: Move to the folder where this .bat lives
cd /d "%~dp0"

:: Resolve virtual environment path (supports venv and .venv)
set "PY_EXE="
set "PIP_EXE="
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    set "PIP_EXE=venv\Scripts\pip.exe"
)
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
    set "PIP_EXE=.venv\Scripts\pip.exe"
)

:: Kill any old process on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Check venv exists
if "%PY_EXE%"=="" (
    echo  [ERROR] Virtual environment not found!
    echo  Run one of the following:
    echo        python -m venv venv
    echo        venv\Scripts\pip install -r backend\requirements.txt
    echo  OR
    echo        python -m venv .venv
    echo        .venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)

:: Quick dependency check
"%PY_EXE%" -c "import flask" 2>nul
if errorlevel 1 (
    echo  Installing dependencies...
    "%PIP_EXE%" install -r backend\requirements.txt
)

:: Start server
echo.
echo  Opening http://localhost:5000 in your browser...
echo  Press Ctrl+C to stop the server.
echo.
start "" http://localhost:5000
"%PY_EXE%" backend\app.py
pause
