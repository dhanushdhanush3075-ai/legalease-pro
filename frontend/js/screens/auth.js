import { $, $$, toast } from "../ui.js";
import { settings, INDIAN_STATES } from "../state.js";
import { api, ApiError } from "../api.js";

let resendTimer = null;
let resendCountdown = 0;

function setActiveTab(name) {
  $$(".auth-tab").forEach(t => t.classList.toggle("active", t.dataset.authTab === name));
  $("#auth-phone-form").classList.toggle("active", name === "login");
  $("#auth-signup-form").classList.toggle("active", name === "signup");
}

function startResendCountdown(seconds = 30) {
  clearInterval(resendTimer);
  resendCountdown = seconds;
  const btn = $("#resend-otp");
  const timer = $("#otp-timer");
  btn.disabled = true;
  const tick = () => {
    if (resendCountdown <= 0) {
      btn.disabled = false;
      timer.textContent = "";
      clearInterval(resendTimer);
      return;
    }
    timer.textContent = `(resend in ${resendCountdown}s)`;
    resendCountdown--;
  };
  tick();
  resendTimer = setInterval(tick, 1000);
}

function readOtp() {
  return $$(".otp-input input").map(i => i.value.trim()).join("");
}

function focusOtpBox(index) {
  const inputs = $$(".otp-input input");
  if (inputs[index]) inputs[index].focus();
}

function wireOtpBoxes() {
  const inputs = $$(".otp-input input");
  inputs.forEach((inp, i) => {
    inp.addEventListener("input", (e) => {
      inp.value = inp.value.replace(/\D/g, "").slice(0, 1);
      if (inp.value && i < inputs.length - 1) focusOtpBox(i + 1);
      // auto-submit when all filled
      if (readOtp().length === 6) {
        $("#auth-phone-form").requestSubmit?.() || $("#auth-phone-form").dispatchEvent(new Event("submit", { cancelable: true }));
      }
    });
    inp.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !inp.value && i > 0) focusOtpBox(i - 1);
    });
    inp.addEventListener("paste", (e) => {
      e.preventDefault();
      const txt = (e.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "").slice(0, 6);
      txt.split("").forEach((c, idx) => { if (inputs[idx]) inputs[idx].value = c; });
      focusOtpBox(Math.min(txt.length, 5));
      if (txt.length === 6) {
        $("#auth-phone-form").requestSubmit?.() || $("#auth-phone-form").dispatchEvent(new Event("submit", { cancelable: true }));
      }
    });
  });
}

async function sendOtp(phone, purpose = "login", extra = {}) {
  const submit = $("#auth-submit");
  submit.disabled = true;
  submit.textContent = "Sending OTP...";
  try {
    const data = await api.sendOtp({ phone, purpose, ...extra });
    $("#otp-block").classList.remove("hidden");
    submit.textContent = "Verify & Login";
    submit.disabled = false;
    startResendCountdown(30);
    if (data.dev_code) {
      // Dev mode: SHOW the OTP but make user type it so verification really runs
      toast(`Dev OTP: ${data.dev_code} (type it in to verify)`, "success", 8000);
    } else {
      toast("OTP sent to your phone", "success");
    }
    // Clear any previously typed OTP
    $$(".otp-input input").forEach(i => i.value = "");
    focusOtpBox(0);
    return true;
  } catch (err) {
    submit.textContent = "Send OTP";
    submit.disabled = false;
    toast(err instanceof ApiError ? err.message : "Failed to send OTP", "error");
    return false;
  }
}

async function verifyOtp(phone, code) {
  const submit = $("#auth-submit");
  submit.disabled = true;
  submit.textContent = "Verifying...";
  try {
    const data = await api.verifyOtp({ phone, code });
    settings.authToken = data.token;
    settings.user = data.user;
    toast(`Welcome ${data.user.name || data.user.phone}`, "success");
    showApp();
    return true;
  } catch (err) {
    submit.textContent = "Verify & Login";
    submit.disabled = false;
    toast(err instanceof ApiError ? err.message : "OTP verification failed", "error");
    // clear OTP boxes for retry
    $$(".otp-input input").forEach(i => i.value = "");
    focusOtpBox(0);
    return false;
  }
}

function showApp() {
  $("#auth-screen").classList.add("hidden");
  $("#app-shell").classList.remove("hidden");
  // Land on Home (not Chat) by default
  import("../ui.js").then(({ navigateTo }) => navigateTo("home"));
  window.dispatchEvent(new CustomEvent("auth:logged_in"));
}

function showLogin() {
  $("#auth-screen").classList.remove("hidden");
  $("#app-shell").classList.add("hidden");
}

export async function checkAuthAndBoot() {
  if (!settings.authToken) {
    showLogin();
    return;
  }
  // Verify token still valid
  try {
    const me = await api.me();
    settings.user = me;
    showApp();
  } catch {
    settings.authToken = null;
    settings.user = null;
    showLogin();
  }
}

export function initAuthScreen() {
  // Populate state in signup
  const sel = $("#signup-state");
  if (sel) {
    sel.innerHTML = "";
    INDIAN_STATES.forEach(s => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s;
      sel.appendChild(o);
    });
    sel.value = settings.state;
  }

  // Tab switching
  $$(".auth-tab").forEach(t => {
    t.addEventListener("click", () => setActiveTab(t.dataset.authTab));
  });

  wireOtpBoxes();

  // Phone form: first send OTP, then verify
  let stage = "send"; // "send" | "verify"
  $("#auth-phone-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const phone = $("#auth-phone").value.replace(/\D/g, "");
    if (phone.length !== 10) {
      toast("Enter a valid 10-digit phone", "error");
      return;
    }
    if (stage === "send") {
      const ok = await sendOtp(phone, "login");
      if (ok) stage = "verify";
    } else {
      const code = readOtp();
      if (code.length !== 6) {
        toast("Enter 6-digit OTP", "error");
        return;
      }
      const ok = await verifyOtp(phone, code);
      if (!ok) stage = "verify";
    }
  });

  // Resend
  $("#resend-otp").addEventListener("click", async () => {
    const phone = $("#auth-phone").value.replace(/\D/g, "");
    if (phone.length === 10) await sendOtp(phone, "login");
  });

  // Signup form
  $("#auth-signup-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const phone = $("#signup-phone").value.replace(/\D/g, "");
    const name = $("#signup-name").value.trim();
    const state = $("#signup-state").value;
    if (phone.length !== 10) { toast("Enter 10-digit phone", "error"); return; }
    if (!name) { toast("Enter your name", "error"); return; }

    // Send signup OTP, then switch to login tab to verify
    settings.state = state;
    const ok = await sendOtp(phone, "signup", { name, state });
    if (ok) {
      setActiveTab("login");
      $("#auth-phone").value = phone;
      toast("OTP sent. Verify to complete signup.", "success");
    }
  });

  // Google signin placeholder
  $("#google-signin").addEventListener("click", () => {
    toast("Google sign-in coming soon. Use phone OTP for now.", "info", 3000);
  });
}

export function logout() {
  settings.authToken = null;
  settings.user = null;
  showLogin();
}
