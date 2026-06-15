import { $, el, toast } from "../ui.js";
import { settings, INDIAN_STATES } from "../state.js";
import { api, ApiError } from "../api.js";

function populateStates() {
  const sel = $("#complaint-state");
  if (sel.children.length > 0) return;
  INDIAN_STATES.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s; opt.textContent = s;
    sel.appendChild(opt);
  });
  sel.value = settings.state;
}

function renderResult(resp) {
  const box = $("#complaint-result");
  box.innerHTML = "";
  box.classList.remove("hidden");

  box.appendChild(el("h3", {}, "Generated Complaint Letter"));
  box.appendChild(el("pre", {}, resp.fir_text || ""));

  if (resp.ipc_sections) {
    box.appendChild(el("h3", {}, "Applicable Sections"));
    box.appendChild(el("p", { class: "muted small" }, resp.ipc_sections));
  }

  if (Array.isArray(resp.alerts) && resp.alerts.length) {
    box.appendChild(el("h3", {}, "Important Notes"));
    const ul = el("ul");
    resp.alerts.forEach(a => ul.appendChild(el("li", { class: "muted small" }, String(a))));
    box.appendChild(ul);
  }

  const actions = el("div", { class: "msg-actions" });
  actions.appendChild(el("button", {
    class: "msg-action", type: "button",
    onclick: () => {
      navigator.clipboard?.writeText(resp.fir_text || "");
      toast("Copied", "success", 1200);
    },
  }, "📋 Copy letter"));
  actions.appendChild(el("button", {
    class: "msg-action", type: "button",
    onclick: () => {
      const url = `https://wa.me/?text=${encodeURIComponent(resp.fir_text || "")}`;
      window.open(url, "_blank", "noopener");
    },
  }, "📤 Share"));
  actions.appendChild(el("button", {
    class: "msg-action", type: "button",
    onclick: () => downloadText(resp.fir_text || "", "complaint-letter.txt"),
  }, "💾 Download"));
  box.appendChild(actions);

  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

function downloadText(text, filename) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function submitComplaint(form) {
  const fd = new FormData(form);
  const payload = Object.fromEntries(fd.entries());
  payload.device_id = settings.deviceId;

  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true;
  btn.textContent = "Drafting...";

  try {
    const data = await api.complaint(payload);
    if (data.status === "success" && data.response) {
      renderResult(data.response);
      toast("Complaint drafted", "success");
    } else {
      toast(data.message || "Failed to draft", "error");
    }
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : "Network error.";
    toast(msg, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Complaint Letter";
  }
}

export function initComplaintScreen() {
  populateStates();
  const form = $("#complaint-form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitComplaint(form);
  });
}
