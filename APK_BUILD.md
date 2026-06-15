# 📱 How to build APK — 3 ways

Your machine status: ✅ Node.js installed · ✅ Java JDK 17 installed · ❌ Android SDK missing

---

## 🥇 OPTION 1: PWABuilder (no install, 5 min) — **RECOMMENDED for you**

Microsoft's free tool. Takes any deployed website and gives you a real Play-Store-ready APK.

### Steps
1. **Deploy backend to Render (free, 10 min)** — see DEPLOY.md "Cloud Deploy" section
   - End result: `https://legalease-api-xxxx.onrender.com`
2. Open https://www.pwabuilder.com
3. Paste your URL → click **"Start"**
4. PWABuilder scans your PWA (we already have manifest.json + service worker)
5. Click **"Package For Stores"** → choose **"Android"**
6. Configure:
   - Package ID: `com.legalease.pro`
   - App name: `LegalEase Pro`
   - Display mode: `standalone`
7. Click **"Generate Package"** — downloads a ZIP with:
   - `signed.apk` — install on phone directly
   - `unsigned.aab` — upload to Play Store

**Total time: 5 minutes. No Android SDK needed.**

---

## 🥈 OPTION 2: Bubblewrap (Google's CLI, 15 min)

Open terminal in `D:\legalease-pro`:

```cmd
npm install -g @bubblewrap/cli
bubblewrap init --manifest https://YOUR-DEPLOYED-URL.onrender.com/manifest.json
bubblewrap build
```

Bubblewrap auto-downloads Android tools on first run (~500 MB). Output: signed APK.

---

## 🥉 OPTION 3: Local Android Studio (30 min setup, full control)

For full Capacitor builds locally.

### Install once (30 min)
1. Download **Android Studio**: https://developer.android.com/studio
2. Install with default options. Accept SDK licenses.
3. Open Android Studio once → let it download SDK (~3 GB)
4. Set environment variable:
   ```powershell
   setx ANDROID_HOME "$env:LOCALAPPDATA\Android\Sdk"
   ```
5. **Restart your terminal**

### Build APK
```cmd
cd D:\legalease-pro
build-apk.ps1
```

Output: `android\app\build\outputs\apk\debug\app-debug.apk`

### Install on phone
1. Enable **Developer Options** on phone (tap "Build number" 7 times in Settings → About)
2. Enable **USB debugging**
3. Connect phone via USB → trust this computer
4. Run:
   ```cmd
   adb install -r android\app\build\outputs\apk\debug\app-debug.apk
   ```

---

## 🤔 Not sure which to pick?

| You want... | Use |
|---|---|
| Quickest APK to test on phone | **Option 1** (PWABuilder) |
| Polished Play Store release | **Option 1** then **Option 3** for signing |
| Full control + offline build | **Option 3** |
| Auto-updating from your URL | **Option 1** (PWABuilder makes TWA — opens your website inside an app shell, always shows latest version) |

---

## 🆘 Common errors

| Error | Fix |
|---|---|
| `JAVA_HOME is not set` | `setx JAVA_HOME "C:\Program Files\Microsoft\jdk-17.0.18.8-hotspot"` then restart terminal |
| `ANDROID_HOME not set` | Install Android Studio first (Option 3), or use Option 1 instead |
| `Could not connect to Gradle` | Check internet, antivirus not blocking |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES` | Use signed APK from `build-apk-release.ps1` instead of debug |
| `App not installed` on phone | Uninstall any old version first, then install new one |
| `License not accepted` | Run `sdkmanager --licenses` and accept all |

---

## ⚡ Why PWABuilder is best for you

You already have:
- ✅ PWA manifest (`frontend/manifest.json`)
- ✅ Service worker (`frontend/sw.js`)
- ✅ Mobile-first design
- ✅ Installable already

PWABuilder takes 3 minutes, no install needed, output works on any Android phone. Sign up needed: none. Cost: free.

**Just deploy the web app first (Render free tier), then point PWABuilder at the URL. APK in your inbox in 5 minutes.**
