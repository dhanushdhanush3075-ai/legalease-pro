/**
 * Global app state + localStorage-backed settings.
 */

const DEFAULT_API_BASE = (() => {
  // 1. Build-time injected (via window.__LEGALEASE_API_BASE__ in index.html or APK)
  if (typeof window !== "undefined" && window.__LEGALEASE_API_BASE__) {
    return window.__LEGALEASE_API_BASE__;
  }
  // 2. Capacitor native app: hardcoded prod URL (must be set before APK build)
  if (typeof window !== "undefined" && window.Capacitor?.isNativePlatform?.()) {
    return window.__LEGALEASE_PROD_API__ || "https://legalease-api.onrender.com";
  }
  // 3. file:// scheme (opened directly without server) — fall back to public prod
  if (typeof window !== "undefined" && window.location.protocol === "file:") {
    return "https://legalease-api.onrender.com";
  }
  // 4. Default: same origin as page (works for localhost dev + production single-server)
  return window.location.origin;
})();

const STORAGE_KEYS = {
  apiBase: "legalease.apiBase",
  theme: "legalease.theme",
  deviceId: "legalease.deviceId",
  sessionId: "legalease.sessionId",
  state: "legalease.state",
  language: "legalease.language",
  ttsEnabled: "legalease.tts",
  authToken: "legalease.authToken",
  user: "legalease.user",
};

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export const settings = {
  get apiBase() {
    return localStorage.getItem(STORAGE_KEYS.apiBase) || DEFAULT_API_BASE;
  },
  set apiBase(v) { localStorage.setItem(STORAGE_KEYS.apiBase, v); },

  get theme() { return localStorage.getItem(STORAGE_KEYS.theme) || "light"; },
  set theme(v) { localStorage.setItem(STORAGE_KEYS.theme, v); },

  get deviceId() {
    let id = localStorage.getItem(STORAGE_KEYS.deviceId);
    if (!id) { id = uuid(); localStorage.setItem(STORAGE_KEYS.deviceId, id); }
    return id;
  },

  get sessionId() { return localStorage.getItem(STORAGE_KEYS.sessionId) || null; },
  set sessionId(v) {
    if (v) localStorage.setItem(STORAGE_KEYS.sessionId, v);
    else localStorage.removeItem(STORAGE_KEYS.sessionId);
  },

  get state() { return localStorage.getItem(STORAGE_KEYS.state) || "Tamil Nadu"; },
  set state(v) { localStorage.setItem(STORAGE_KEYS.state, v); },

  get language() { return localStorage.getItem(STORAGE_KEYS.language) || "english"; },
  set language(v) { localStorage.setItem(STORAGE_KEYS.language, v); },

  get ttsEnabled() { return localStorage.getItem(STORAGE_KEYS.ttsEnabled) === "true"; },
  set ttsEnabled(v) { localStorage.setItem(STORAGE_KEYS.ttsEnabled, v ? "true" : "false"); },

  get authToken() { return localStorage.getItem(STORAGE_KEYS.authToken) || null; },
  set authToken(v) {
    if (v) localStorage.setItem(STORAGE_KEYS.authToken, v);
    else localStorage.removeItem(STORAGE_KEYS.authToken);
  },

  get user() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEYS.user) || "null"); }
    catch { return null; }
  },
  set user(v) {
    if (v) localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(v));
    else localStorage.removeItem(STORAGE_KEYS.user);
  },

  clearAll() {
    Object.values(STORAGE_KEYS).forEach(k => localStorage.removeItem(k));
  },
};

export const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
  "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal", "Jammu and Kashmir", "Ladakh",
  "Andaman and Nicobar", "Chandigarh", "Dadra and Nagar Haveli",
  "Lakshadweep", "Puducherry",
];
