import { $, el, toast } from "../ui.js";
import { settings, INDIAN_STATES } from "../state.js";
import { api, ApiError } from "../api.js";
import { isRecognitionSupported, createRecognizer, speak, cancelSpeak } from "../voice.js";
import { t } from "../i18n.js";

const chatBox = () => $("#chat-box");
const typing = () => $("#typing-indicator");

function showTyping() { typing().classList.remove("hidden"); scrollToEnd(); }
function hideTyping() { typing().classList.add("hidden"); }
function scrollToEnd() { const c = chatBox(); c.scrollTop = c.scrollHeight; }

function makeMessage(role, text, citations = [], alerts = []) {
  const wrap = el("div", { class: `msg ${role === "user" ? "user-msg" : "ai-msg"}` });
  wrap.appendChild(el("div", {}, text));

  if (role === "assistant") {
    if (Array.isArray(citations) && citations.length) {
      const sec = el("div", { class: "meta-section" });
      sec.appendChild(el("div", { class: "section-title" }, "📚 Citations"));
      const ul = el("ul");
      citations.forEach(c => {
        const li = el("li");
        if (c.ref) li.appendChild(el("span", { class: "citation-ref" }, c.ref + " — "));
        if (c.name) li.appendChild(document.createTextNode(c.name));
        if (c.meta) {
          li.appendChild(el("br"));
          li.appendChild(el("i", { class: "muted small" }, c.meta));
        }
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      wrap.appendChild(sec);
    }
    if (Array.isArray(alerts) && alerts.length) {
      const sec = el("div", { class: "meta-section" });
      sec.appendChild(el("div", { class: "section-title warn" }, "⚠️ Action Points"));
      const ul = el("ul");
      alerts.forEach(a => {
        const li = el("li", { class: "alert-action" }, typeof a === "string" ? a : (a.text || ""));
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      wrap.appendChild(sec);
    }

    const actions = el("div", { class: "msg-actions" });
    actions.appendChild(el("button", {
      class: "msg-action",
      type: "button",
      onclick: () => {
        navigator.clipboard?.writeText(text);
        toast("Copied", "success", 1200);
      },
    }, "📋 Copy"));
    actions.appendChild(el("button", {
      class: "msg-action",
      type: "button",
      onclick: () => {
        const lang = $("#lang-select").value;
        speak(text, lang);
      },
    }, "🔊 Read"));
    actions.appendChild(el("button", {
      class: "msg-action",
      type: "button",
      onclick: () => {
        const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
        window.open(url, "_blank", "noopener");
      },
    }, "📤 Share"));
    wrap.appendChild(actions);
  }
  return wrap;
}

function addMessage(role, text, citations, alerts) {
  const box = chatBox();
  box.appendChild(makeMessage(role, text, citations, alerts));
  scrollToEnd();
}

async function sendQuery(text) {
  if (!text || !text.trim()) return;
  addMessage("user", text);
  showTyping();

  $("#send-btn").disabled = true;

  try {
    const data = await api.chat({
      query: text,
      state: $("#state-select").value,
      language: $("#lang-select").value,
      session_id: settings.sessionId,
      device_id: settings.deviceId,
    });

    hideTyping();

    if (data.session_id) settings.sessionId = data.session_id;
    const respText = data.response?.text || data.message || "Could not process your question.";

    if (data.status === "success" && data.response) {
      addMessage("assistant", respText, data.response.citations, data.response.alerts);
      if (settings.ttsEnabled) speak(respText, $("#lang-select").value);
    } else {
      addMessage("assistant", "⚠️ " + respText);
      toast(data.message || "AI error", "error", 3500);
    }
  } catch (err) {
    hideTyping();
    const msg = err instanceof ApiError ? err.message : "Network error.";
    addMessage("assistant", "⚠️ " + msg);
    toast(msg, "error");
  } finally {
    $("#send-btn").disabled = false;
  }
}

function setupVoiceInput() {
  const btn = $("#mic-btn");
  if (!isRecognitionSupported()) {
    btn.disabled = true;
    btn.title = "Voice not supported on this device";
    return;
  }

  let recognizer = null;

  btn.addEventListener("click", () => {
    if (recognizer) {
      recognizer.stop();
      return;
    }
    recognizer = createRecognizer($("#lang-select").value);
    if (!recognizer) return;

    btn.classList.add("recording");
    recognizer.onresult = (e) => {
      const transcript = e.results[0]?.[0]?.transcript || "";
      if (transcript) {
        $("#user-input").value = transcript;
        $("#user-input").focus();
      }
    };
    recognizer.onerror = (e) => {
      toast("Voice error: " + e.error, "error");
    };
    recognizer.onend = () => {
      btn.classList.remove("recording");
      recognizer = null;
    };
    try { recognizer.start(); } catch (err) {
      btn.classList.remove("recording");
      recognizer = null;
    }
  });
}

export function initChatScreen() {
  // Populate state dropdown
  const stateSel = $("#state-select");
  stateSel.innerHTML = "";
  INDIAN_STATES.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    stateSel.appendChild(opt);
  });
  stateSel.value = settings.state;
  stateSel.addEventListener("change", () => { settings.state = stateSel.value; });

  const langSel = $("#lang-select");
  langSel.value = settings.language;
  langSel.addEventListener("change", async () => {
    settings.language = langSel.value;
    const { setLang } = await import("../i18n.js");
    setLang(langSel.value);
  });

  // Greet on first load only — use i18n
  const renderWelcome = () => {
    if (chatBox().children.length === 0) {
      addMessage("assistant", t("chat.welcome"), [], []);
    }
  };
  renderWelcome();

  // Re-render welcome on language change (clear chat first)
  window.addEventListener("lang:changed", () => {
    const box = chatBox();
    if (box.children.length <= 1) {
      box.innerHTML = "";
      renderWelcome();
    }
  });

  // Form submit
  $("#chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#user-input");
    const txt = input.value.trim();
    if (!txt) return;
    input.value = "";
    sendQuery(txt);
  });

  // New chat
  $("#new-chat-btn").addEventListener("click", () => {
    cancelSpeak();
    settings.sessionId = null;
    chatBox().innerHTML = "";
    addMessage("assistant", "New conversation started. How can I help?", [], []);
  });

  setupVoiceInput();
}
