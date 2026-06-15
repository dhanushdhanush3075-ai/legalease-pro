@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title LegalEase Pro - GitHub Setup

echo.
echo ================================================
echo  LegalEase Pro - Push to GitHub
echo ================================================
echo.

REM 1. Check git
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git is not installed.
    echo Download: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM 2. Init repo if needed
if not exist ".git" (
    echo Initializing git repo on branch main...
    git init -b main
)

REM 3. Stage everything (gitignore excludes .env, DB, venv)
echo Staging files...
git add .

REM 4. Commit if there's anything staged
git diff --cached --quiet
if errorlevel 1 (
    set "MSG=Initial commit: LegalEase Pro"
    set /p MSG_IN=Commit message [press Enter for default]:
    if not "!MSG_IN!"=="" set "MSG=!MSG_IN!"
    git commit -m "!MSG!"
) else (
    echo Nothing new to commit.
)

REM 5. Check for gh CLI
where gh >nul 2>nul
if errorlevel 1 (
    echo.
    echo ================================================
    echo GitHub CLI not installed - manual push required
    echo ================================================
    echo.
    echo Step A: Install gh CLI from https://cli.github.com/
    echo         OR create repo manually:
    echo.
    echo Step B: Open https://github.com/new
    echo         Repository name: legalease-pro
    echo         Make it Public, do NOT add README/license
    echo         Click "Create repository"
    echo.
    echo Step C: Copy the commands shown like this:
    echo.
    echo   git remote add origin https://github.com/YOUR-USERNAME/legalease-pro.git
    echo   git branch -M main
    echo   git push -u origin main
    echo.
    pause
    exit /b 0
)

REM 6. gh CLI present - create + push
git remote -v 2>nul | findstr /C:"origin" >nul
if errorlevel 1 (
    echo.
    set "REPO_NAME=legalease-pro"
    set /p REPO_NAME_IN=GitHub repo name [press Enter for legalease-pro]:
    if not "!REPO_NAME_IN!"=="" set "REPO_NAME=!REPO_NAME_IN!"
    echo.
    echo Creating GitHub repo: !REPO_NAME!
    gh repo create "!REPO_NAME!" --public --source=. --remote=origin --push
    if errorlevel 1 (
        echo.
        echo [ERROR] gh repo create failed.
        echo Run this once first to authenticate:
        echo   gh auth login
        pause
        exit /b 1
    )
) else (
    echo Origin remote exists. Pushing latest...
    git push -u origin main
)

echo.
echo ================================================
echo  SUCCESS - Pushed to GitHub
echo ================================================
echo.
echo NEXT STEPS:
echo.
echo 1. APK build - GitHub Actions runs automatically
echo    Go to your repo, click Actions tab
echo    Wait 5-7 min for "Build Android APK" to finish
echo    Click Releases tab on right side to download .apk
echo.
echo 2. Deploy backend to Render free tier:
echo    https://dashboard.render.com/blueprints
echo    Click New Blueprint, connect your repo
echo    Add secret: GEMINI_API_KEY = your key
echo    Wait 10 min for deploy
echo.
echo 3. View your repo:
echo    gh repo view --web
echo.
pause
endlocal
