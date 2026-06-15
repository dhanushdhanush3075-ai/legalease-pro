import { $, $$, navigateTo, toast } from "./ui.js";
import { settings } from "./state.js";
import { initChatScreen } from "./screens/chat.js";
import { initComplaintScreen } from "./screens/complaint.js";
import { initTemplatesScreen } from "./screens/templates.js";
import { initHistoryScreen } from "./screens/history.js";
import { initSettingsScreen } from "./screens/settings.js";
import { initLawsScreen } from "./screens/laws.js";
import { initAuthScreen, checkAuthAndBoot, logout } from "./screens/auth.js";
import { initHomeScreen } from "./screens/home.js";
import { startFlow } from "./screens/onboarding.js";
import { applyI18n } from "./i18n.js";

function setupNav() {
  $$(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => navigateTo(btn.dataset.screen));
  });

  $("#back-btn").addEventListener("click", () => navigateTo("home"));

  window.addEventListener("screen:enter", (e) => {
    if (e.detail.screen === "templates") initTemplatesScreen();
  });
}

function applyInitialTheme() {
  document.documentElement.setAttribute("data-theme", settings.theme);
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

function bindAuthEvents() {
  window.addEventListener("auth:expired", () => {
    toast("Session expired. Please login again.", "error", 3000);
    setTimeout(() => logout(), 800);
  });
  window.addEventListener("auth:logged_in", () => {
    navigateTo("chat");
  });
}

async function init() {
  applyInitialTheme();
  initAuthScreen();
  setupNav();
  initHomeScreen();
  initChatScreen();
  initComplaintScreen();
  initHistoryScreen();
  initSettingsScreen();
  initLawsScreen();
  bindAuthEvents();
  registerServiceWorker();

  // Apply initial translations + listen for lang changes
  applyI18n();
  window.addEventListener("lang:changed", () => applyI18n());

  // Boot flow: splash → onboarding/terms → auth check
  await startFlow();
  await checkAuthAndBoot();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
