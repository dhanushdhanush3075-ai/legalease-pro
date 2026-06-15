#!/usr/bin/env pwsh
# ============================================================
# LegalEase Pro — one-click Android APK builder
# Usage: .\build-apk.ps1
# ============================================================
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " LegalEase Pro — APK Builder" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Sanity checks
$missing = @()
if (-not (Get-Command node -ErrorAction SilentlyContinue))     { $missing += "Node.js (https://nodejs.org)" }
if (-not (Get-Command npm  -ErrorAction SilentlyContinue))     { $missing += "npm" }
if (-not $env:JAVA_HOME -and -not (Get-Command java -ErrorAction SilentlyContinue)) { $missing += "Java JDK 17+ (https://adoptium.net)" }

$androidMissing = $false
if (-not $env:ANDROID_HOME -and -not $env:ANDROID_SDK_ROOT) {
    $defaultSdk = "$env:LOCALAPPDATA\Android\Sdk"
    if (Test-Path $defaultSdk) {
        $env:ANDROID_HOME = $defaultSdk
        Write-Host "  Found Android SDK at $defaultSdk - using it." -ForegroundColor Green
    } else {
        $androidMissing = $true
    }
}

if ($missing.Count -gt 0 -or $androidMissing) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host " CANNOT BUILD APK LOCALLY — missing tools" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host ""
    if ($missing.Count -gt 0) {
        Write-Host "Missing:" -ForegroundColor Yellow
        $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    }
    if ($androidMissing) {
        Write-Host "  - Android SDK (install Android Studio: https://developer.android.com/studio)" -ForegroundColor Yellow
        Write-Host "    Then restart terminal and re-run this script." -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host " EASIER ALTERNATIVE — PWABuilder.com (5 min)" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host " 1. Deploy backend to Render.com (free, 10 min)" -ForegroundColor White
    Write-Host "    Push to GitHub, then https://dashboard.render.com/blueprints" -ForegroundColor Gray
    Write-Host ""
    Write-Host " 2. Visit https://www.pwabuilder.com" -ForegroundColor White
    Write-Host "    Paste your deployed URL" -ForegroundColor Gray
    Write-Host ""
    Write-Host " 3. Click 'Package For Stores' -> Android" -ForegroundColor White
    Write-Host "    Download the signed APK + Play Store AAB" -ForegroundColor Gray
    Write-Host ""
    Write-Host " Full guide: APK_BUILD.md" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# 2. Install Node dependencies (Capacitor)
if (-not (Test-Path "node_modules")) {
    Write-Host "==> Installing Capacitor + plugins..." -ForegroundColor Green
    npm install
}

# 3. Init Capacitor if not yet
if (-not (Test-Path "capacitor.config.json")) {
    Write-Host "==> capacitor.config.json missing!" -ForegroundColor Red
    exit 1
}

# 4. Add android platform
if (-not (Test-Path "android")) {
    Write-Host "==> Adding Android platform..." -ForegroundColor Green
    npx cap add android
} else {
    Write-Host "==> Android folder already present" -ForegroundColor Gray
}

# 5. Sync web assets to native project
Write-Host "==> Syncing frontend to native project..." -ForegroundColor Green
npx cap sync android

# 6. Patch AndroidManifest for required permissions
$manifestPath = "android\app\src\main\AndroidManifest.xml"
if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath -Raw
    $perms = @(
        '<uses-permission android:name="android.permission.INTERNET" />',
        '<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />',
        '<uses-permission android:name="android.permission.RECORD_AUDIO" />',
        '<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />',
        '<uses-permission android:name="android.permission.CALL_PHONE" />'
    )
    $addedAny = $false
    foreach ($p in $perms) {
        if ($manifest -notmatch [regex]::Escape($p)) {
            $manifest = $manifest -replace '(<manifest [^>]+>)', "`$1`n    $p"
            $addedAny = $true
        }
    }
    if ($addedAny) {
        Set-Content $manifestPath $manifest -Encoding UTF8
        Write-Host "==> Patched AndroidManifest.xml with required permissions" -ForegroundColor Green
    }
}

# 7. Build debug APK
Write-Host "==> Building debug APK (this may take 2-5 min on first run)..." -ForegroundColor Green
Push-Location android
try {
    .\gradlew.bat assembleDebug
} catch {
    Write-Host "Gradle build failed. Try opening android folder in Android Studio." -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

$apk = "android\app\build\outputs\apk\debug\app-debug.apk"
if (Test-Path $apk) {
    $size = (Get-Item $apk).Length / 1MB
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host " ✅ APK BUILT" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host " Path:  $Root\$apk" -ForegroundColor Yellow
    Write-Host " Size:  $($size.ToString('F1')) MB" -ForegroundColor Yellow
    Write-Host ""
    Write-Host " Install on phone:" -ForegroundColor Cyan
    Write-Host "  1. Enable Developer Options → USB debugging" -ForegroundColor Gray
    Write-Host "  2. Connect phone via USB" -ForegroundColor Gray
    Write-Host "  3. Run:  adb install -r ""$apk""" -ForegroundColor Gray
    Write-Host ""
    Write-Host " Or just copy the APK to phone and tap to install (allow ""Unknown sources"")" -ForegroundColor Gray
    Write-Host ""
    Write-Host " IMPORTANT — set API URL in app:" -ForegroundColor Cyan
    Write-Host "  After install, open app → Settings → API Server" -ForegroundColor Gray
    Write-Host "  Point it to your PC's LAN IP, e.g. http://192.168.1.5:8001" -ForegroundColor Gray
    Write-Host "  Keep run.ps1 running on PC while you test" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "APK not found at expected path. Check build output above." -ForegroundColor Red
    exit 1
}
