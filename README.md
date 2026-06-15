# ⚖️ LegalEase Pro

AI-powered Indian legal assistant — web + installable PWA + Android APK.

Built with **FastAPI + Gemini 2.0 Flash + Vanilla JS PWA + Capacitor**.

---

## ✨ Features

| Area | Capability |
|------|-----------|
| 💬 Chat | Ask any Indian legal question — IPC/BNS, CrPC, Consumer Protection, IT Act, family law. State-aware answers. |
| 🚨 FIR Drafter | Form-based generator that produces a formal Police Complaint letter to the SHO. |
| 📄 Templates | Rental agreement, RTI, legal notice, consumer complaint, cheque bounce notice, will, DV application, and more. |
| 🕘 History | Every chat saved to SQLite. Resume, delete, search later. |
| 🎤 Voice | Tamil / Hindi / English speech-to-text (Web Speech API). |
| 🔊 Read-aloud | TTS playback of AI replies in the chosen language. |
| 🌙 Dark mode | Automatic theme + manual toggle. |
| 📱 Mobile | Mobile-first UI, PWA installable, Capacitor build for native Android APK. |
| 🛡️ Safety | XSS-safe DOM rendering, rate limiting, structured logs, JSON-mode Gemini calls. |

---

## 🏗️ Architecture

```
legalease-pro/
├── app/                      FastAPI backend
│   ├── main.py              ─ entry point + static mount
│   ├── core/
│   │   ├── config.py        ─ Settings (pydantic-settings)
│   │   ├── logging.py       ─ structlog setup
│   │   └── limiter.py       ─ slowapi rate limiter
│   ├── db/
│   │   ├── database.py      ─ SQLAlchemy engine
│   │   └── models.py        ─ Session, Message, Complaint
│   ├── schemas/             ─ Pydantic request/response models
│   ├── services/
│   │   └── gemini.py        ─ google-genai wrapper + JSON-mode
│   └── routers/
│       ├── chat.py          ─ POST /api/legal/query
│       ├── complaint.py     ─ POST /api/legal/complaint
│       ├── history.py       ─ GET/DELETE /api/history/*
│       └── templates.py     ─ GET /api/templates/
├── frontend/                Mobile-first PWA (served by FastAPI)
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js                ─ Service worker (offline shell)
│   ├── css/styles.css
│   ├── icons/
│   └── js/
│       ├── app.js           ─ bootstrap
│       ├── state.js         ─ localStorage settings
│       ├── api.js           ─ fetch wrapper
│       ├── ui.js            ─ DOM helpers (XSS-safe el())
│       ├── voice.js         ─ Web Speech API
│       └── screens/         ─ chat, complaint, templates, history, settings
├── capacitor.config.json    Capacitor (Android wrapper)
├── package.json
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.ps1                  ─ Windows dev launcher
└── .env.example
```

---

## 🚀 Quick start (Windows)

```powershell
# 1. Get a Gemini API key from https://aistudio.google.com/apikey
# 2. Configure environment
Copy-Item .env.example .env
# Edit .env and paste your GEMINI_API_KEY

# 3. Run (creates venv, installs deps, starts server)
.\run.ps1
```

Open `http://localhost:8001` — that serves both API and the PWA.

### From phone on same WiFi

The script prints your LAN IP at startup, e.g.:
```
 From mobile (same WiFi):  http://192.168.1.5:8001
```

Open that URL in Chrome on the phone → tap menu → **Install app**. You now have a PWA on your home screen.

---

## 🐳 Docker

```bash
export GEMINI_API_KEY=your_key_here
docker compose up -d
# Server on http://localhost:8001
```

---

## 📱 Build a real Android APK (Capacitor)

```powershell
# One-time: install Node deps
npm install

# Add Android platform
npx cap add android

# Sync the frontend into the native project
npx cap sync

# Open in Android Studio (build APK from there)
npx cap open android

# Or build a debug APK from CLI:
cd android
.\gradlew.bat assembleDebug
# APK at: android\app\build\outputs\apk\debug\app-debug.apk
```

> **Note:** Before building, open `frontend/index.html` in the device and ensure the **Settings → API Server** points to your live backend URL (e.g. `https://api.your-domain.com`), not `localhost`.

### Required Android permissions

Edit `android/app/src/main/AndroidManifest.xml` and add inside `<manifest>`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

---

## 🔌 API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/api/health` | Health + version + active model |
| POST   | `/api/legal/query` | Ask a legal question |
| POST   | `/api/legal/complaint` | Generate FIR letter |
| GET    | `/api/history/sessions?device_id=…` | List chat sessions |
| GET    | `/api/history/sessions/{id}/messages` | Get messages |
| DELETE | `/api/history/sessions/{id}` | Delete session |
| GET    | `/api/templates/` | List document templates |
| GET    | `/api/templates/{id}` | Get one template |

Interactive docs: `http://localhost:8001/docs`

---

## 🔐 Production checklist

- [ ] Set `APP_ENV=production` and replace `CORS_ORIGINS=*` with your real origin(s).
- [ ] Move secrets to a real secret manager (don't ship `.env` to prod).
- [ ] Front the server with a reverse proxy (Nginx/Caddy) + HTTPS.
- [ ] Switch `DATABASE_URL` to PostgreSQL for multi-instance.
- [ ] Add an error tracker (Sentry SDK is a one-line drop-in).
- [ ] Add user auth before exposing to the public (phone OTP recommended for India — Supabase or Firebase Auth).
- [ ] Sign the APK with your release key before publishing to Play Store.

---

## ⚠️ Disclaimer

LegalEase Pro is an **educational assistant**, not a substitute for an advocate. AI responses can be incomplete or wrong. For serious matters — arrests, court hearings, large financial disputes — always consult a licensed lawyer.
