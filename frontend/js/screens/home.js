import { $, $$, el, navigateTo } from "../ui.js";
import { settings } from "../state.js";
import { api } from "../api.js";

function greetingByTime() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 21) return "Good evening";
  return "Vanakkam";
}

function renderFeatured(c) {
  const box = $("#home-featured");
  box.innerHTML = "";
  const card = el("div", { class: "law-card", style: "cursor:pointer" });
  card.addEventListener("click", () => navigateTo("laws"));
  const head = el("div", { class: "lc-head" });
  head.appendChild(el("div", { class: "lc-section" }, c.title || ""));
  head.appendChild(el("span", { class: "lc-tag" }, String(c.year || "")));
  card.appendChild(head);
  if (c.citation) card.appendChild(el("div", { class: "lc-meta" }, [el("b", {}, "Citation: "), document.createTextNode(c.citation)]));
  if (c.ruling) card.appendChild(el("div", { class: "lc-desc" }, c.ruling.slice(0, 200) + (c.ruling.length > 200 ? "..." : "")));
  card.appendChild(el("a", { class: "lc-link", href: "javascript:void(0)" }, "View all 70 landmark cases →"));
  box.appendChild(card);
}

async function loadFeatured() {
  try {
    const data = await api.landmarkCases();
    const recent = data.cases.filter(c => c.year >= 2023);
    const pick = recent[Math.floor(Math.random() * recent.length)] || data.cases[0];
    if (pick) renderFeatured(pick);
    else $("#home-featured").innerHTML = '<p class="muted center small">No cases loaded.</p>';
  } catch {
    $("#home-featured").innerHTML = '<p class="muted center small">Login to see featured judgment.</p>';
  }
}

function formatRelative(dateStr) {
  if (!dateStr) return "";
  let d;
  try { d = new Date(dateStr); } catch { return dateStr; }
  if (isNaN(d.getTime())) return dateStr;
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
  if (diff < 7 * 86400) return Math.floor(diff / 86400) + "d ago";
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function renderNewsCard(n) {
  const card = el("a", {
    class: "news-card",
    href: n.url || "#",
    target: "_blank",
    rel: "noopener",
  });
  const head = el("div", { class: "nc-head" });
  head.appendChild(el("span", { class: "nc-source" }, n.source || ""));
  head.appendChild(el("span", { class: "nc-time" }, formatRelative(n.date)));
  card.appendChild(head);
  card.appendChild(el("div", { class: "nc-title" }, n.title || ""));
  if (n.summary) card.appendChild(el("div", { class: "nc-summary" }, n.summary));
  if (n.category) card.appendChild(el("span", { class: "nc-cat" }, n.category));
  return card;
}

async function loadNews() {
  const box = $("#home-news");
  if (!box) return;
  box.innerHTML = '<div class="muted center small">Fetching latest from LiveLaw &amp; SCObserver...</div>';
  try {
    const data = await api.news({ limit: 8 });
    box.innerHTML = "";
    if (!data.items?.length) {
      box.innerHTML = '<div class="muted center small">No news right now.</div>';
      return;
    }
    data.items.forEach(n => box.appendChild(renderNewsCard(n)));
  } catch {
    box.innerHTML = '<div class="muted center small">Could not load news.</div>';
  }
}

async function loadEmergency() {
  const grid = $("#home-emergency");
  if (!grid) return;
  try {
    const data = await api.helplines();
    grid.innerHTML = "";
    Object.values(data).slice(0, 4).forEach(h => {
      const a = el("a", { class: "he-card", href: "tel:" + h.number }, [
        el("div", {}, [
          el("div", { class: "he-num" }, h.number),
          el("div", { class: "he-label" }, h.label),
        ]),
      ]);
      grid.appendChild(a);
    });
  } catch {}
}

function setupActions() {
  const actionMap = {
    chat: "chat",
    complaint: "complaint",
    analyse: "templates",
    laws: "laws",
    cases: "laws",
    courts: "laws",
    lawyers: "laws",
    tracker: "laws",
  };

  $$(".ha-card").forEach(card => {
    card.addEventListener("click", () => {
      const action = card.dataset.action;
      const screen = actionMap[action] || "chat";
      navigateTo(screen);
      // Auto-select tab for laws sub-screens
      setTimeout(() => {
        if (action === "cases") document.querySelector('.laws-tab[data-laws-tab="landmark"]')?.click();
        if (action === "courts") document.querySelector('.laws-tab[data-laws-tab="courts"]')?.click();
        if (action === "lawyers") document.querySelector('.laws-tab[data-laws-tab="lawyers"]')?.click();
        if (action === "tracker") document.querySelector('.laws-tab[data-laws-tab="tracker"]')?.click();
        if (action === "analyse") document.querySelector('.docs-tab[data-docs-tab="analyse"]')?.click();
      }, 120);
    });
  });

  $("#home-ask-btn")?.addEventListener("click", () => navigateTo("chat"));
}

function updateGreeting() {
  const u = settings.user;
  const greet = $("#home-greeting");
  if (greet) {
    const name = u?.name || u?.phone || "";
    greet.textContent = `${greetingByTime()}${name ? ", " + (u?.name || "user") : ""} 🙏`;
  }
}

export function initHomeScreen() {
  setupActions();
  updateGreeting();
  window.addEventListener("auth:logged_in", () => {
    updateGreeting();
    loadNews();
    loadFeatured();
    loadEmergency();
  });
  window.addEventListener("screen:enter", (e) => {
    if (e.detail.screen === "home") {
      updateGreeting();
      loadNews();
      loadFeatured();
      loadEmergency();
    }
  });
  document.getElementById("home-news-refresh")?.addEventListener("click", loadNews);
}
