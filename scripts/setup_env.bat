@echo off
setlocal enabledelayedexpansion

echo.
echo [AI-DAN] Checking Python installation...

where python >nul 2>nul
if errorlevel 1 (
    echo [AI-DAN][ERROR] Python was not found on PATH.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo and ensure "Add python.exe to PATH" is enabled.
    exit /b 1
)

python --version
if errorlevel 1 (
    echo [AI-DAN][ERROR] Python is installed but not working correctly.
    exit /b 1
)

echo.
echo [AI-DAN] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [AI-DAN][ERROR] Failed to upgrade pip.
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [AI-DAN][ERROR] Failed to install dependencies.
    exit /b 1
)

echo.
echo [AI-DAN] Environment setup complete.
echo You can now run scripts\start_local.bat
echo.
