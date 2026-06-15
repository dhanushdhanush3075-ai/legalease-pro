# LegalEase Pro - dev launcher (PowerShell)
# Usage:  .\run.ps1            # creates venv, installs deps, runs server
#         .\run.ps1 -Setup     # just install deps, don't run
#         .\run.ps1 -NoVenv    # use system python

param(
  [switch]$Setup,
  [switch]$NoVenv
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not $NoVenv) {
  if (-not (Test-Path "$Root\.venv")) {
    Write-Host "Creating virtual env..." -ForegroundColor Cyan
    python -m venv .venv
  }
  $py = "$Root\.venv\Scripts\python.exe"
  $pip = "$Root\.venv\Scripts\pip.exe"
} else {
  $py = "python"
  $pip = "pip"
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $pip install -q --upgrade pip
& $pip install -q -r requirements.txt

if ($Setup) { Write-Host "Setup complete." -ForegroundColor Green; exit 0 }

if (-not (Test-Path "$Root\.env")) {
  Write-Warning ".env not found. Copy .env.example to .env and add your GEMINI_API_KEY."
  exit 1
}

# Find a LAN-accessible IP for mobile testing
$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
       Where-Object { $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual" } |
       Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
       Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " LegalEase Pro starting on http://0.0.0.0:8001" -ForegroundColor Green
if ($ip) { Write-Host " From mobile (same WiFi):  http://${ip}:8001" -ForegroundColor Yellow }
Write-Host " Docs:  http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

& $py -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
