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

set "VENV_DIR=.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

echo.
if not exist "%VENV_PYTHON%" (
    echo [AI-DAN] Creating local virtual environment in %VENV_DIR%...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [AI-DAN][ERROR] Failed to create virtual environment.
        exit /b 1
    )
)

if not exist "%VENV_PYTHON%" (
    echo [AI-DAN][ERROR] Virtual environment Python executable was not found.
    exit /b 1
)

echo.
echo [AI-DAN] Installing dependencies from requirements.txt into %VENV_DIR%...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [AI-DAN][ERROR] Failed to upgrade pip in the virtual environment.
    exit /b 1
)

"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [AI-DAN][ERROR] Failed to install dependencies in the virtual environment.
    exit /b 1
)

echo.
echo [AI-DAN] Environment setup complete.
echo [AI-DAN] Using virtual environment: %VENV_DIR%
