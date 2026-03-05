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

:: Kill any old process on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Check venv exists
if not exist "venv\Scripts\python.exe" (
    echo  [ERROR] Virtual environment not found!
    echo  Run:  python -m venv venv
    echo        venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)

:: Quick dependency check
"venv\Scripts\python.exe" -c "import flask" 2>nul
if errorlevel 1 (
    echo  Installing dependencies...
    "venv\Scripts\pip.exe" install -r backend\requirements.txt
)

:: Start server
echo.
echo  Opening http://localhost:5000 in your browser...
echo  Press Ctrl+C to stop the server.
echo.
start "" http://localhost:5000
"venv\Scripts\python.exe" backend\app.py
pause
