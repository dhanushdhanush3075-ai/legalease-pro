#!/usr/bin/env pwsh
# ============================================================
# LegalEase Pro — SIGNED RELEASE APK + AAB builder
# Output: signed APK + AAB ready for Play Store upload
# Usage: .\build-apk-release.ps1
# ============================================================
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " LegalEase Pro — RELEASE APK + AAB" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# --- Pre-flight ---
if (-not (Get-Command keytool -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] 'keytool' not found. Install Java JDK 17+ from https://adoptium.net" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "android")) {
    Write-Host "Android folder missing — running base build first..." -ForegroundColor Yellow
    .\build-apk.ps1
}

# --- Step 1: Generate keystore if missing (ONE TIME ONLY — keep safe!) ---
$ksPath = "$Root\legalease-release.keystore"
if (-not (Test-Path $ksPath)) {
    Write-Host ""
    Write-Host "==> Generating release keystore (one-time)..." -ForegroundColor Green
    Write-Host "    You'll be asked to set passwords + identity. WRITE THEM DOWN." -ForegroundColor Yellow
    Write-Host "    Without this keystore you can NEVER update your Play Store app." -ForegroundColor Yellow
    Write-Host ""
    keytool -genkeypair -v `
        -keystore $ksPath `
        -alias legalease `
        -keyalg RSA -keysize 2048 -validity 25000 `
        -storetype JKS
    if (-not (Test-Path $ksPath)) {
        Write-Host "[ERROR] Keystore generation failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "==> Keystore created at: $ksPath" -ForegroundColor Green
    Write-Host "    BACKUP THIS FILE + PASSWORDS RIGHT NOW." -ForegroundColor Red
    Write-Host ""
}

# --- Step 2: Prompt for passwords (or use env) ---
$storePass = if ($env:LEGALEASE_KEYSTORE_PASS) { $env:LEGALEASE_KEYSTORE_PASS } else { Read-Host -Prompt "Keystore password" -AsSecureString | ConvertFrom-SecureString -AsPlainText }
$keyPass = if ($env:LEGALEASE_KEY_PASS) { $env:LEGALEASE_KEY_PASS } else { Read-Host -Prompt "Key password (often same as keystore)" -AsSecureString | ConvertFrom-SecureString -AsPlainText }

# --- Step 3: Write key.properties (consumed by build.gradle) ---
$keyProps = @"
storePassword=$storePass
keyPassword=$keyPass
keyAlias=legalease
storeFile=$ksPath
"@
$keyPropsFile = "$Root\android\key.properties"
Set-Content -Path $keyPropsFile -Value $keyProps -Encoding UTF8
Write-Host "==> key.properties written" -ForegroundColor Green

# --- Step 4: Patch build.gradle for signing if not done ---
$gradleFile = "$Root\android\app\build.gradle"
if (Test-Path $gradleFile) {
    $gradle = Get-Content $gradleFile -Raw
    if ($gradle -notmatch "signingConfigs\s*\{[^}]*release") {
        $signingBlock = @"

def keystorePropertiesFile = rootProject.file("key.properties")
def keystoreProperties = new Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        release {
            if (keystorePropertiesFile.exists()) {
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
            }
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
            shrinkResources false
        }
    }
}
"@
        Add-Content -Path $gradleFile -Value $signingBlock
        Write-Host "==> Patched build.gradle with signing config" -ForegroundColor Green
    }
}

# --- Step 5: Sync frontend ---
Write-Host "==> Syncing frontend..." -ForegroundColor Green
npx cap sync android

# --- Step 6: Build signed APK + AAB ---
Write-Host "==> Building signed APK + AAB (3-7 min)..." -ForegroundColor Green
Push-Location android
try {
    .\gradlew.bat assembleRelease bundleRelease
} finally {
    Pop-Location
}

$apkOut = "$Root\android\app\build\outputs\apk\release\app-release.apk"
$aabOut = "$Root\android\app\build\outputs\bundle\release\app-release.aab"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " ✅ RELEASE ARTIFACTS BUILT" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

if (Test-Path $apkOut) {
    $sz = ((Get-Item $apkOut).Length / 1MB).ToString("F1")
    Write-Host " APK (sideload):    $apkOut  ($sz MB)" -ForegroundColor Yellow
} else {
    Write-Host " ⚠ APK not produced — check gradle output above" -ForegroundColor Red
}
if (Test-Path $aabOut) {
    $sz = ((Get-Item $aabOut).Length / 1MB).ToString("F1")
    Write-Host " AAB (Play Store):  $aabOut  ($sz MB)" -ForegroundColor Yellow
} else {
    Write-Host " ⚠ AAB not produced" -ForegroundColor Red
}

Write-Host ""
Write-Host " NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Sideload APK on a phone for testing:" -ForegroundColor Gray
Write-Host "       adb install -r `"$apkOut`"" -ForegroundColor Gray
Write-Host "  2. Upload AAB to Google Play Console:" -ForegroundColor Gray
Write-Host "       https://play.google.com/console" -ForegroundColor Gray
Write-Host "  3. See PLAY_STORE_READINESS.md for listing details." -ForegroundColor Gray
Write-Host ""
Write-Host " ⚠ Keep `legalease-release.keystore` safe — losing it means" -ForegroundColor Red
Write-Host "   you can NEVER push updates to the same Play Store app." -ForegroundColor Red
Write-Host ""
