@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%\.."

echo ==========================================
echo AI-DAN Local Startup (Windows)
echo ==========================================
echo.

cd /d "%REPO_ROOT%"
if errorlevel 1 (
  echo [ERROR] Could not switch to repository root.
  exit /b 1
)

echo [STEP 1/3] Verifying Python...
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python was not found on this machine.
    echo Install Python 3.11+ and ensure it is on PATH.
    exit /b 1
  )
)

echo [STEP 2/3] Setting up environment...
call "%SCRIPT_DIR%\setup_env.bat"
if errorlevel 1 (
  echo [ERROR] Environment setup failed.
  exit /b 1
)

echo.
echo [STEP 3/3] Starting services...
echo - Backend:  http://localhost:8000
echo - Frontend: http://localhost:8501
echo.
echo Opening two new terminal windows...
echo Close those windows to stop services.
echo.

where py >nul 2>nul
if errorlevel 1 (
  start "AI-DAN Backend" cmd /k "cd /d ""%REPO_ROOT%"" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
  start "AI-DAN Frontend" cmd /k "cd /d ""%REPO_ROOT%"" && python -m streamlit run frontend/command_center.py --server.port 8501"
) else (
  start "AI-DAN Backend" cmd /k "cd /d ""%REPO_ROOT%"" && py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
  start "AI-DAN Frontend" cmd /k "cd /d ""%REPO_ROOT%"" && py -m streamlit run frontend/command_center.py --server.port 8501"
)

echo.
echo AI-DAN is launching.
echo If your browser does not open automatically:
echo - API docs:  http://localhost:8000/docs
echo - UI app:    http://localhost:8501
echo.

exit /b 0
