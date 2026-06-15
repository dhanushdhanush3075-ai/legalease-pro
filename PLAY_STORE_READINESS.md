# Google Play Store Launch Checklist

## ✅ App Quality
- [x] App name: LegalEase Pro
- [x] Package: com.legalease.pro
- [x] Min SDK 24 (Android 7+) — covers 95%+ devices
- [x] Target SDK 34 (Android 14)
- [x] No crashes during full user journey
- [x] All features verified end-to-end
- [x] Reduced motion + accessibility considered

## ✅ Compliance Documents
- [x] **PRIVACY_POLICY.md** — host at https://legalease.pro/privacy (publicly accessible URL required by Google)
- [x] **TERMS_OF_SERVICE.md** — host at https://legalease.pro/terms
- [x] Disclaimer in onboarding T&C screen + every chat reply

## ✅ Required by Play Console

### Data Safety form (filled per Play Console)
| Data | Collected | Shared | Purpose |
|---|---|---|---|
| Phone number | Yes | No (only Twilio/MSG91 for OTP) | Account management |
| Name | Yes (optional) | No | Account management |
| Email | Yes (optional) | No | Account management |
| App activity (queries) | Yes | No | App functionality, analytics |
| Device or other IDs | Yes (anonymized) | No | Analytics |

### Content rating
- IARC Generally Suitable for ages 13+ (but app restricted to 18+ via ToS)
- May mention crime / violence in legal context — declare appropriately

### Target audience
- Adults 18+

## 📋 Listing assets needed

### Required
- [ ] App icon — 512×512 PNG (high-res)
- [ ] Feature graphic — 1024×500 PNG (banner shown in store)
- [ ] Phone screenshots — 2-8 screenshots, 16:9 or 9:16 (at least 1080p)
- [ ] Short description — 80 chars max
- [ ] Full description — 4000 chars max
- [ ] Category — Education / Lifestyle / News & Magazines

### Short description (draft)
"AI-powered Indian legal companion — IPC/BNS, FIR drafter, case search, free legal aid."

### Long description (draft)
```
⚖️ LegalEase Pro — Bharat's AI Legal Companion

Get plain-language answers to ANY Indian legal question — in English, தமிழ், or हिन्दी. Backed by 250+ verified IPC↔BNS sections, 70+ landmark Supreme Court judgments, and live legal news.

✨ FEATURES

💬 AI Chat
Ask any legal question. Get grounded answers with REAL section citations — no hallucinated laws.

🚨 FIR / Complaint Drafter
Generate a formal police complaint with correct IPC/BNS sections in seconds.

📜 IPC ↔ BNS 2024 Map
Every old IPC section mapped to its new BNS equivalent. Punishment, explanation, examples.

⚖️ Case Law Search
70+ landmark SC judgments (1973–2024). Live search via Indian Kanoon's 6M+ judgment database.

🏛️ Court Locator
Supreme Court, all 25 High Courts, major District Courts, tribunals. Phone, website, eCourts, maps.

🧮 Legal Calculators
Bail check (bailable / cognizable). Limitation period. Court fee estimator by state.

👨‍⚖️ Free Legal Aid Directory
30+ State Legal Services Authorities, NGOs, and Bar Associations. NALSA 15100 one-tap.

🔎 Case Tracker
Enter CNR number — direct links to eCourts district, High Court, Supreme Court status.

🔍 Document Analyser
Upload photo of court notice, FIR, or contract. AI explains in plain language + tells you what to do.

📰 Live Legal News
LiveLaw, Bar & Bench, SCObserver — daily updates on courts and amendments.

🆘 Emergency Helplines
NALSA 15100 (legal aid), NCW 7827170170, CHILDLINE 1098, Cybercrime 1930, Emergency 112.

🔐 Privacy First
Phone OTP login. No location, no contacts, no microphone access (except for voice input within your control). Data stays encrypted on Indian servers.

⚠️ Disclaimer
LegalEase Pro provides legal INFORMATION, not legal ADVICE. Always consult a qualified advocate for serious matters.
```

## 🔐 Signed APK Build

### 1. Generate keystore (ONE TIME, keep safe!)
```bash
keytool -genkey -v -keystore legalease-release.keystore \
  -alias legalease -keyalg RSA -keysize 2048 -validity 25000
```

### 2. Configure `android/key.properties`
```
storePassword=YOUR_KEYSTORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=legalease
storeFile=../legalease-release.keystore
```

### 3. Update `android/app/build.gradle`
```gradle
signingConfigs {
    release {
        storeFile file(keystoreProperties['storeFile'])
        storePassword keystoreProperties['storePassword']
        keyAlias keystoreProperties['keyAlias']
        keyPassword keystoreProperties['keyPassword']
    }
}
buildTypes {
    release {
        signingConfig signingConfigs.release
        minifyEnabled true
        shrinkResources true
    }
}
```

### 4. Build release AAB (Play Store format)
```bash
npm install
npx cap sync android
cd android
./gradlew bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

### 5. Upload to Play Console
1. Create app on https://play.google.com/console
2. Pay $25 one-time developer fee
3. Upload AAB to "Production" track (or "Internal testing" first)
4. Fill App content (privacy, data safety, target audience, news app check)
5. Add store listing (screenshots, descriptions, icon, feature graphic)
6. Submit for review (2-7 days)

## 🌐 Required HTTPS endpoints (for Play approval)

You must host on a public URL (e.g., Cloudflare Pages free tier):
- https://legalease.pro/privacy → PRIVACY_POLICY.md rendered as HTML
- https://legalease.pro/terms → TERMS_OF_SERVICE.md
- https://legalease.pro/support → contact page

## 🟢 Backend production checklist
- [ ] Move backend off `http://localhost` to HTTPS at api.legalease.pro
- [ ] Replace `OTP_DEV_MODE=true` with real SMS provider (Twilio/MSG91/Fast2SMS)
- [ ] `CORS_ORIGINS=https://legalease.pro` (not *)
- [ ] PostgreSQL instead of SQLite (Supabase/Neon/AWS RDS)
- [ ] Sentry for error tracking
- [ ] Rate limit tuned for production load
- [ ] Backups + monitoring (UptimeRobot, BetterStack)

## 🟢 In-app fixes for Play approval
- [ ] Add "Privacy Policy" link in Settings → opens https://legalease.pro/privacy
- [ ] Add "Terms of Service" link in Settings
- [ ] Add app version display ("v1.0.0")
- [ ] Clearly state "Not legal advice" disclaimer on every AI response and in onboarding
- [ ] Restrict to 18+ via age confirmation (already done in T&C)
