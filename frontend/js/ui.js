/**
 * UI primitives: toast, screen routing, DOM helpers.
 */

export function $(sel, root = document) { return root.querySelector(sel); }
export function $$(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

/** Build a DOM element with safe text. Never use innerHTML for untrusted content. */
export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (v !== null && v !== undefined) {
      node.setAttribute(k, v);
    }
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    if (typeof child === "string") node.appendChild(document.createTextNode(child));
    else node.appendChild(child);
  }
  return node;
}

let toastTimer = null;
export function toast(message, type = "info", duration = 2400) {
  const t = $("#toast");
  t.textContent = String(message || "");
  t.className = `toast ${type}`;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), duration);
}

const titles = {
  home: "LegalEase Pro",
  chat: "AI Chat",
  complaint: "Draft FIR",
  templates: "Documents",
  laws: "Laws & Cases",
  help: "Help & Reference",
  history: "History",
  settings: "Settings",
};

export function navigateTo(screenId) {
  $$(".screen").forEach(s => s.classList.toggle("active", s.id === `screen-${screenId}`));
  $$(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.screen === screenId));
  $("#screen-title").textContent = titles[screenId] || "LegalEase Pro";
  // Show ← back button on every screen except Home
  const back = $("#back-btn");
  if (back) back.classList.toggle("hidden", screenId === "home");
  window.dispatchEvent(new CustomEvent("screen:enter", { detail: { screen: screenId } }));
}
