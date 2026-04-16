@echo off
setlocal EnableExtensions EnableDelayedExpansion
title RMKCET Parent Connect
color 0A

cd /d "%~dp0"

set "AUTORUN=false"
if /I "%~1"=="--autorun" set "AUTORUN=true"

set "CONFIG_FILE=%CD%\config.ini"
if not exist "%CONFIG_FILE%" (
    >"%CONFIG_FILE%" echo [launcher]
    >>"%CONFIG_FILE%" echo shell_startup_enabled = false
)

call :read_config
if /I "%SHELL_STARTUP_ENABLED%"=="true" call :ensure_windows_startup_task

set "RUNTIME_ROOT=%CD%\.runtime"
set "EMBED_VERSION=3.11.9"
set "PY_HOME=%RUNTIME_ROOT%\python-embed"
set "PY_EXE=%PY_HOME%\python.exe"

echo.
echo  ============================================
echo   RMKCET Parent Connect
echo   Starting server...
echo  ============================================
echo.

call :ensure_embedded_python
if errorlevel 1 goto :startup_failed

call :ensure_dependencies
if errorlevel 1 goto :startup_failed

echo  [INFO] Checking for existing processes on port 5000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo  [INFO] Killing process with PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo  ============================================
echo   Server starting...
echo   URL: http://localhost:5000
echo   Press Ctrl+C to stop the server.
echo  ============================================
echo.

if /I not "%AUTORUN%"=="true" start "" http://localhost:5000
"%PY_EXE%" -c "import runpy,sys; sys.path.insert(0, r'%CD%\\backend'); runpy.run_path(r'%CD%\\backend\\app.py', run_name='__main__')"

echo.
echo  Server has stopped.
if /I not "%AUTORUN%"=="true" pause
exit /b 0

:startup_failed
echo.
echo  [ERROR] Launcher failed.
if /I not "%AUTORUN%"=="true" pause
exit /b 1

:read_config
set "SHELL_STARTUP_ENABLED=false"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /I /R "^shell_startup_enabled[ ]*=" "%CONFIG_FILE%"`) do (
    set "_val=%%B"
    set "_val=!_val: =!"
    if /I "!_val!"=="true" set "SHELL_STARTUP_ENABLED=true"
)
exit /b 0

:ensure_windows_startup_task
set "TASK_NAME=RMKCET_ParentConnect_Autostart"
set "TASK_CMD=\"%CD%\start.bat\" --autorun"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] shell_startup_enabled=true, creating startup task...
    schtasks /Create /F /TN "%TASK_NAME%" /SC ONSTART /RU SYSTEM /TR "%TASK_CMD%" >nul 2>&1
    if errorlevel 1 (
        schtasks /Create /F /TN "%TASK_NAME%" /SC ONLOGON /TR "%TASK_CMD%" >nul 2>&1
        if errorlevel 1 (
            echo  [WARNING] Could not create startup task automatically.
            echo  [WARNING] Run this script as Administrator once if needed.
        ) else (
            echo  [SUCCESS] Startup task created (ONLOGON fallback): %TASK_NAME%
        )
    ) else (
        echo  [SUCCESS] Startup task created (ONSTART): %TASK_NAME%
    )
)
exit /b 0

:ensure_embedded_python
if exist "%PY_EXE%" (
    echo  [INFO] Using embedded Python runtime: %PY_EXE%
    exit /b 0
)

echo  [INFO] Embedded Python not found. Downloading Python %EMBED_VERSION% embeddable package...
if not exist "%RUNTIME_ROOT%" mkdir "%RUNTIME_ROOT%"

set "EMBED_ZIP=%RUNTIME_ROOT%\python-embed.zip"
set "GET_PIP_FILE=%RUNTIME_ROOT%\get-pip.py"
set "EMBED_URL=https://www.python.org/ftp/python/%EMBED_VERSION%/python-%EMBED_VERSION%-embed-amd64.zip"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri '%EMBED_URL%' -OutFile '%EMBED_ZIP%'" >nul
if errorlevel 1 (
    echo  [ERROR] Failed to download embedded Python package.
    exit /b 1
)

if exist "%PY_HOME%" rmdir /s /q "%PY_HOME%"
mkdir "%PY_HOME%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%PY_HOME%' -Force" >nul
if errorlevel 1 (
    echo  [ERROR] Failed to extract embedded Python package.
    exit /b 1
)
del /q "%EMBED_ZIP%" >nul 2>&1

if not exist "%PY_HOME%\Lib\site-packages" mkdir "%PY_HOME%\Lib\site-packages"
if exist "%PY_HOME%\python311._pth" (
    >"%PY_HOME%\python311._pth" echo python311.zip
    >>"%PY_HOME%\python311._pth" echo .
    >>"%PY_HOME%\python311._pth" echo Lib
    >>"%PY_HOME%\python311._pth" echo Lib\site-packages
    >>"%PY_HOME%\python311._pth" echo import site
)

echo  [INFO] Installing pip into embedded Python runtime...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GET_PIP_FILE%'" >nul
if errorlevel 1 (
    echo  [ERROR] Failed to download get-pip.py.
    exit /b 1
)

"%PY_EXE%" "%GET_PIP_FILE%" --disable-pip-version-check --no-warn-script-location >nul
if errorlevel 1 (
    echo  [ERROR] Failed to install pip in embedded runtime.
    exit /b 1
)
del /q "%GET_PIP_FILE%" >nul 2>&1

echo  [SUCCESS] Embedded Python runtime is ready.
exit /b 0

:ensure_dependencies
if not exist "backend\requirements.txt" (
    echo  [WARNING] backend\requirements.txt not found. Skipping dependency installation.
    exit /b 0
)

"%PY_EXE%" -c "import flask, pandas, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing dependencies from backend\requirements.txt...
    "%PY_EXE%" -m pip install --disable-pip-version-check --no-warn-script-location --upgrade pip >nul
    "%PY_EXE%" -m pip install --disable-pip-version-check --no-warn-script-location -r backend\requirements.txt
    if errorlevel 1 (
        echo  [ERROR] Failed to install dependencies.
        exit /b 1
    )
    echo  [SUCCESS] Dependencies installed.
) else (
    echo  [INFO] Dependencies already installed.
)
exit /b 0