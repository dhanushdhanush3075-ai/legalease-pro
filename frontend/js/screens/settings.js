import { $, toast } from "../ui.js";
import { settings } from "../state.js";
import { api, ApiError } from "../api.js";
import { logout as authLogout } from "./auth.js";

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  $("#theme-btn").textContent = theme === "dark" ? "☀️" : "🌙";
}

async function pingApi() {
  const status = $("#api-status");
  status.textContent = "Checking...";
  try {
    const data = await api.health();
    status.textContent = `✅ Connected · v${data.version} · ${data.model}`;
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : "No connection";
    status.textContent = "❌ " + msg;
  }
}

export function initSettingsScreen() {
  const apiInput = $("#api-base-input");
  apiInput.value = settings.apiBase;
  pingApi();

  $("#save-api-btn").addEventListener("click", () => {
    const v = apiInput.value.trim();
    if (!v) { toast("Enter a valid URL", "error"); return; }
    try { new URL(v); } catch { toast("Invalid URL", "error"); return; }
    settings.apiBase = v;
    toast("Saved", "success");
    pingApi();
  });

  // Theme toggle
  const darkToggle = $("#dark-toggle");
  darkToggle.checked = settings.theme === "dark";
  darkToggle.addEventListener("change", () => {
    const theme = darkToggle.checked ? "dark" : "light";
    settings.theme = theme;
    applyTheme(theme);
  });

  $("#theme-btn").addEventListener("click", () => {
    const next = settings.theme === "dark" ? "light" : "dark";
    settings.theme = next;
    darkToggle.checked = next === "dark";
    applyTheme(next);
  });

  // TTS toggle
  const ttsToggle = $("#tts-toggle");
  ttsToggle.checked = settings.ttsEnabled;
  ttsToggle.addEventListener("change", () => {
    settings.ttsEnabled = ttsToggle.checked;
  });

  // Clear data
  $("#clear-data-btn").addEventListener("click", () => {
    if (!confirm("This will clear settings, session, device id, and log you out. Continue?")) return;
    settings.clearAll();
    toast("Cleared. Reloading...", "success");
    setTimeout(() => location.reload(), 800);
  });

  // Account info + logout
  const updateAccount = () => {
    const u = settings.user;
    const info = $("#account-info");
    const btn = $("#logout-btn");
    if (u) {
      info.textContent = `${u.name || u.phone || "User"} · +91 ${u.phone || ""} · ${u.state || ""}`;
      btn.classList.remove("hidden");
    } else {
      info.textContent = "Not logged in.";
      btn.classList.add("hidden");
    }
  };
  updateAccount();
  window.addEventListener("auth:logged_in", updateAccount);

  $("#logout-btn").addEventListener("click", async () => {
    try { await api.logout(); } catch {}
    authLogout();
    toast("Logged out", "success");
  });

  applyTheme(settings.theme);
}
