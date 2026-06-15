@echo off
REM ============================================================
REM LegalEase Pro - One-click start (double-click this file)
REM No PowerShell policy issues, just plain CMD.
REM ============================================================

cd /d "%~dp0"
title LegalEase Pro Server

echo.
echo ================================================
echo  LegalEase Pro - Starting server...
echo ================================================
echo.

REM 1. Check python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.11+ from https://python.org/downloads/
    echo Make sure to CHECK "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

REM 2. Check .env
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Copying .env.example to .env...
    copy .env.example .env
    echo.
    echo Please edit .env and set your GEMINI_API_KEY, then re-run this script.
    echo Get a key from: https://aistudio.google.com/apikey
    pause
    exit /b 1
)

REM 3. Install deps if needed
echo Checking dependencies...
python -c "import fastapi, uvicorn, google.genai" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies for the first time...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM 4. Find local IP for mobile testing
echo.
for /f "tokens=14" %%i in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    set "LANIP=%%i"
    goto :done
)
:done

echo ================================================
echo  Server running:    http://localhost:8001
if defined LANIP echo  From your phone:   http://%LANIP%:8001
echo  API docs:          http://localhost:8001/docs
echo ================================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM 5. Open browser automatically after 3 seconds (in background)
start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8001/"

REM 6. Run server (this blocks until Ctrl+C)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

pause
