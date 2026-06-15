# 🚀 LegalEase Pro — Complete Deployment Guide

Choose your path:

| Goal | Section | Time |
|------|---------|------|
| 🏠 Run on your PC | [Local Dev](#-local-dev) | 5 min |
| 🌐 Live on the Internet (free) | [Cloud Deploy](#-cloud-deploy-web-app) | 15 min |
| 📱 APK on your phone | [Android Build](#-android-build-installable-apk) | 30 min |
| 🏪 Google Play Store | [Play Store](#-google-play-store-release) | 2 hours |

---

## 🏠 Local Dev

### Easiest (Windows)
1. Install Python 3.11+ → tick **"Add Python to PATH"**
2. Get a Gemini API key → https://aistudio.google.com/apikey
3. Open `.env`, paste key after `GEMINI_API_KEY=`
4. Double-click **`START.bat`** in this folder

Browser opens at http://localhost:8001 automatically.

Stop: double-click **`STOP.bat`**.

### Manual (any OS)
```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Phone on same WiFi
The `START.bat` output prints your LAN IP, e.g.:
```
From your phone:  http://192.168.1.5:8001
```
Open that URL in Chrome on your phone. Tap menu → **Add to Home Screen** = instant PWA install.

---

## 🌐 Cloud Deploy (Web App)

### Option A: Render.com (recommended — free tier with database)

1. Push this repo to GitHub.
2. Go to https://dashboard.render.com/blueprints
3. Connect your repo → Render auto-detects `render.yaml`
4. After deploy starts, set the secret:
   - `GEMINI_API_KEY` = your key
5. Free tier sleeps after 15 min idle. Upgrade to `starter` ($7/mo) for always-on.

URL: `https://legalease-api-xxxx.onrender.com`

### Option B: Fly.io (free tier, Mumbai region)

```bash
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
fly auth signup
fly launch --no-deploy --copy-config
fly secrets set GEMINI_API_KEY=your_key
fly deploy
```

URL: `https://legalease-pro.fly.dev`

### Option C: Railway

1. https://railway.app → New Project → Deploy from GitHub
2. Railway auto-detects `railway.json` + Dockerfile
3. Add env var: `GEMINI_API_KEY`
4. Add a PostgreSQL database from the Railway marketplace
5. Set `DATABASE_URL` env var (Railway auto-injects)

### Option D: Docker anywhere

```bash
docker build -t legalease-pro .
docker run -d -p 8001:8001 \
  -e GEMINI_API_KEY=your_key \
  -e APP_ENV=production \
  -v $(pwd)/data:/app/data \
  --name legalease-pro \
  legalease-pro
```

### Option E: Split — Vercel (frontend) + Render (backend)

Cheaper for high frontend traffic.
1. Backend on Render (as Option A above) → note URL.
2. Edit `frontend/index.html` line:  
   `window.__LEGALEASE_PROD_API__ = "https://your-render-url.onrender.com";`
3. `vercel deploy` from the project root (uses `vercel.json`).
4. Result: static frontend on Vercel CDN + API on Render.

### Production checklist
- [ ] `APP_ENV=production`
- [ ] `CORS_ORIGINS=https://your-domain.com` (not `*`)
- [ ] `OTP_DEV_MODE=false` (then wire Twilio/MSG91 in `app/routers/auth.py`)
- [ ] `JWT_SECRET=` set to a long random string (NOT the default!)
- [ ] PostgreSQL `DATABASE_URL` (not SQLite, for multi-instance)
- [ ] Privacy Policy URL added to Play Console / website footer
- [ ] Sentry / similar error tracker wired

---

## 📱 Android Build (installable APK)

### Prerequisites (one-time)
1. **Java JDK 17+** → https://adoptium.net (Temurin)
2. **Android Studio** → https://developer.android.com/studio
   - During install, accept SDK + create AVD
3. **Node.js 18+** → https://nodejs.org
4. Set environment variable `ANDROID_HOME` to your SDK path  
   e.g. `setx ANDROID_HOME "C:\Users\YourName\AppData\Local\Android\Sdk"`
5. Restart your terminal.

### Build a debug APK (for personal sideload)
```powershell
cd D:\legalease-pro
.\build-apk.ps1
```
Output: `android\app\build\outputs\apk\debug\app-debug.apk` (~6 MB)

### Install on phone
Option 1 — copy file:
1. Copy the `.apk` to your phone via USB.
2. On phone: tap the APK → allow "Install unknown apps" for your file manager.

Option 2 — adb:
```powershell
adb install -r android\app\build\outputs\apk\debug\app-debug.apk
```

### Before building APK — set the API URL

By default the APK tries to hit `https://legalease-api.onrender.com`. To point it at YOUR deployed backend:

Edit `frontend/index.html` line:
```html
window.__LEGALEASE_PROD_API__ = "https://your-deployed-api.com";
```

Then rebuild:
```powershell
.\build-apk.ps1
```

You can also override at runtime in the app → Settings → API Server.

---

## 🏪 Google Play Store Release

### 1. Build a SIGNED release APK + AAB

```powershell
cd D:\legalease-pro
.\build-apk-release.ps1
```

First run: it generates `legalease-release.keystore` and asks for passwords.  
**⚠ BACKUP `legalease-release.keystore` + write the passwords down. Lose them = you can NEVER update your Play Store app.**

Outputs:
- `android\app\build\outputs\apk\release\app-release.apk`  (for sideload testing)
- `android\app\build\outputs\bundle\release\app-release.aab` (upload this to Play Store)

### 2. Create the Play Console app
1. Sign up at https://play.google.com/console — one-time **$25 fee**
2. Create new app → fill basic info
3. Upload the **AAB** to "Production" track (or "Internal testing" first)

### 3. Required listing assets

| Asset | Size | Notes |
|---|---|---|
| App icon | 512×512 PNG | Already in `frontend/icons/` (convert SVG to PNG via squoosh.app) |
| Feature graphic | 1024×500 PNG | Banner shown on store |
| Phone screenshots | 1080×1920+ | 2-8 screenshots |
| Short description | 80 chars | See `PLAY_STORE_READINESS.md` for drafted copy |
| Full description | 4000 chars | Same file |
| Privacy Policy URL | public HTTPS | Host `PRIVACY_POLICY.md` rendered as HTML |
| Terms URL | public HTTPS | Same for `TERMS_OF_SERVICE.md` |

### 4. Required Play Console forms
- **Data Safety** form: see table in `PLAY_STORE_READINESS.md`
- **Content rating** IARC: General audiences with mention of crime in legal context
- **Target audience**: 18+
- **News app**: NO

### 5. Submit for review
2-7 day review by Google. They especially check:
- Privacy Policy is reachable + accurate
- Data Safety form matches what app actually collects
- Disclaimer that AI ≠ legal advice (we have this on every chat reply + onboarding)

---

## 🔌 Backend production setup (do these AFTER first deploy)

### Real OTP (replace dev mode)

Edit `app/routers/auth.py` `send_otp` function. Add Twilio or MSG91 call:

```python
# Twilio example
from twilio.rest import Client
twilio = Client(account_sid, auth_token)
twilio.messages.create(
    body=f"Your LegalEase OTP is {code}. Valid 5 min.",
    from_="+1234567890",  # your Twilio number
    to=f"+91{req.phone}"
)
```

Add `OTP_DEV_MODE=false` to env. Dev codes will no longer be exposed in API responses.

### Migrate from SQLite to PostgreSQL

Set `DATABASE_URL=postgresql://user:pass@host/dbname` in env. `psycopg2-binary` already in Dockerfile. App auto-creates tables on startup.

### Add Sentry (1 line)
```python
import sentry_sdk
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.1)
```
Set `SENTRY_DSN` env var.

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Install Python 3.11+, tick "Add to PATH" |
| `cannot be loaded because running scripts is disabled` (PowerShell) | Use `START.bat` instead, or `powershell -ExecutionPolicy Bypass -File run.ps1` |
| Port 8001 in use | `STOP.bat` then start again, or change port in `.env` |
| Page blank / unstyled | Browser cache. Press Ctrl+Shift+Del → clear all → Ctrl+F5 |
| `gradlew: command not found` (APK build) | Use `.\gradlew.bat` on Windows |
| APK builds but won't install | Enable "Install unknown apps" in phone settings for your browser/file manager |
| Render free tier sleeps | Upgrade to Starter ($7/mo) for always-on |
| OTP not sending in production | You forgot to wire Twilio/MSG91; see "Real OTP" section above |

---

## 📁 Files reference

| File | Purpose |
|------|---------|
| `START.bat` / `STOP.bat` | Windows double-click start/stop |
| `run.ps1` / `run.sh` | PowerShell / Bash dev launcher |
| `build-apk.ps1` | Debug APK (sideload) |
| `build-apk-release.ps1` | Signed release APK + AAB (Play Store) |
| `Dockerfile` | Production container |
| `docker-compose.yml` | Single-host stack with volume |
| `render.yaml` | Render.com one-click deploy |
| `fly.toml` | Fly.io deploy |
| `railway.json` | Railway deploy |
| `vercel.json` | Vercel frontend-only deploy |
| `.github/workflows/deploy.yml` | CI smoke test + optional Fly deploy |
| `PRIVACY_POLICY.md` | Required for Play Store + web compliance |
| `TERMS_OF_SERVICE.md` | Same |
| `PLAY_STORE_READINESS.md` | Detailed Play Store checklist |
| `DEPLOY.md` | This file |
