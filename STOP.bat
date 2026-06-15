@echo off
REM Kill any python process holding port 8001
echo Stopping LegalEase Pro server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    echo Killing PID %%a
    taskkill /F /PID %%a >nul 2>nul
)
echo Done.
timeout /t 2 /nobreak >nul
