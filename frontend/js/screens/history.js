import { $, el, toast, navigateTo } from "../ui.js";
import { api, ApiError } from "../api.js";
import { settings } from "../state.js";

function formatDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

async function loadHistory() {
  const list = $("#history-list");
  list.innerHTML = "";
  list.appendChild(el("p", { class: "muted center" }, "Loading..."));

  try {
    const sessions = await api.listSessions(settings.deviceId);
    list.innerHTML = "";
    if (!sessions.length) {
      list.appendChild(el("p", { class: "muted center" }, "No conversations yet."));
      return;
    }
    sessions.forEach(s => {
      const card = el("div", { class: "history-card" });
      const info = el("div", {}, [
        el("div", { class: "hc-title" }, s.title || "Untitled"),
        el("div", { class: "hc-meta" }, `${s.state} · ${s.language} · ${formatDate(s.updated_at)}`),
      ]);
      info.style.cursor = "pointer";
      info.addEventListener("click", () => openSession(s.id));

      const del = el("button", {
        class: "hc-delete",
        type: "button",
        title: "Delete",
        onclick: async (e) => {
          e.stopPropagation();
          if (!confirm("Delete this conversation?")) return;
          try {
            await api.deleteSession(s.id);
            card.remove();
            if (settings.sessionId === s.id) settings.sessionId = null;
            toast("Deleted", "success", 1200);
          } catch (err) {
            toast("Delete failed", "error");
          }
        },
      }, "🗑");

      card.appendChild(info);
      card.appendChild(del);
      list.appendChild(card);
    });
  } catch (err) {
    list.innerHTML = "";
    const msg = err instanceof ApiError ? err.message : "Could not load.";
    list.appendChild(el("p", { class: "muted center" }, msg));
  }
}

async function openSession(sessionId) {
  try {
    const messages = await api.getMessages(sessionId);
    settings.sessionId = sessionId;
    navigateTo("chat");
    const box = $("#chat-box");
    box.innerHTML = "";
    // Replay messages into the chat screen
    const { initChatScreen } = await import("./chat.js");
    // Use existing helpers by dispatching a custom event for chat to repopulate
    messages.forEach(m => {
      const div = document.createElement("div");
      div.className = `msg ${m.role === "user" ? "user-msg" : "ai-msg"}`;
      div.textContent = m.content;
      box.appendChild(div);
    });
    box.scrollTop = box.scrollHeight;
  } catch (err) {
    toast("Could not open conversation", "error");
  }
}

export function initHistoryScreen() {
  window.addEventListener("screen:enter", (e) => {
    if (e.detail.screen === "history") loadHistory();
  });
}
