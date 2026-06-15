import { $, $$, el, toast } from "../ui.js";
import { settings, INDIAN_STATES } from "../state.js";
import { api } from "../api.js";

const BOOKMARK_KEY = "legalease.bookmarks";

function getBookmarks() {
  try { return JSON.parse(localStorage.getItem(BOOKMARK_KEY) || "[]"); }
  catch { return []; }
}
function saveBookmark(item) {
  const list = getBookmarks();
  if (list.find(b => b.id === item.id && b.type === item.type)) return false;
  list.unshift(item);
  localStorage.setItem(BOOKMARK_KEY, JSON.stringify(list));
  return true;
}
function removeBookmark(id, type) {
  const list = getBookmarks().filter(b => !(b.id === id && b.type === type));
  localStorage.setItem(BOOKMARK_KEY, JSON.stringify(list));
}

export { saveBookmark, removeBookmark, getBookmarks };

let emergencyLoaded = false;

function setHelpTab(name) {
  $$(".help-tab").forEach(t => t.classList.toggle("active", t.dataset.helpTab === name));
  ["emergency", "dict", "stations", "bookmarks"].forEach(n => {
    const p = document.getElementById(`help-pane-${n}`);
    if (p) p.classList.toggle("active", n === name);
  });
  if (name === "emergency") loadEmergency();
  if (name === "stations") loadStations();
  if (name === "bookmarks") renderBookmarks();
}

// ---------- Emergency cards ----------
function renderEmergency(card) {
  const node = el("div", { class: `emergency-card ${card.color || ""}` });
  const head = el("div", { class: "ec-head" });
  head.appendChild(el("span", { class: "ec-icon" }, card.icon || "🆘"));
  head.appendChild(el("div", { class: "ec-title" }, card.title || ""));
  if (card.urgency) head.appendChild(el("span", { class: `ec-urgency ${card.color}` }, card.urgency));
  node.appendChild(head);

  const body = el("div", { class: "ec-body" });
  const ol = el("ol");
  (card.steps || []).forEach(s => ol.appendChild(el("li", {}, s)));
  body.appendChild(ol);

  if (card.calls?.length) {
    const calls = el("div", { class: "ec-calls" });
    card.calls.forEach(c => {
      const a = el("a", { class: "ec-call-btn", href: "tel:" + (c.number || "").replace(/\s/g, "") }, [
        el("span", { style: "font-size:18px" }, "📞"),
        el("span", { style: "flex:1" }, c.label),
        el("span", { class: "ec-call-num" }, c.number),
      ]);
      calls.appendChild(a);
    });
    body.appendChild(calls);
  }

  if (card.key_laws?.length) {
    const laws = el("div", { class: "ec-laws" });
    laws.appendChild(el("div", { class: "ec-laws-title" }, "Key laws"));
    card.key_laws.forEach(l => laws.appendChild(el("span", { class: "ec-law-chip" }, l)));
    body.appendChild(laws);
  }
  node.appendChild(body);

  head.addEventListener("click", () => node.classList.toggle("expanded"));
  return node;
}

async function loadEmergency() {
  if (emergencyLoaded) return;
  const box = $("#emergency-list");
  box.innerHTML = '<p class="muted center small">Loading...</p>';
  try {
    const data = await api.emergencyCards();
    box.innerHTML = "";
    (data.cards || []).forEach(c => box.appendChild(renderEmergency(c)));
    emergencyLoaded = true;
  } catch (err) {
    box.innerHTML = '<p class="muted center">Failed to load.</p>';
  }
}

// ---------- Dictionary ----------
function renderDictTerm(t) {
  const card = el("div", { class: "dict-card" });
  const titleRow = el("div", {}, [
    el("span", { class: "dict-term" }, t.term),
    t.category ? el("span", { class: "dict-cat" }, t.category) : null,
  ]);
  card.appendChild(titleRow);
  if (t.en) card.appendChild(el("div", { class: "dict-meaning" }, [el("b", {}, "EN"), document.createTextNode(t.en)]));
  if (t.ta) card.appendChild(el("div", { class: "dict-meaning" }, [el("b", {}, "TA"), document.createTextNode(t.ta)]));
  if (t.hi) card.appendChild(el("div", { class: "dict-meaning" }, [el("b", {}, "HI"), document.createTextNode(t.hi)]));
  return card;
}

async function searchDict() {
  const q = $("#dict-query").value.trim();
  const box = $("#dict-results");
  box.innerHTML = '<p class="muted center small">Searching...</p>';
  try {
    const data = await api.dictionary(q);
    box.innerHTML = "";
    if (!data.terms?.length) {
      box.innerHTML = '<p class="muted center small">No terms match. Try: bail, FIR, summons.</p>';
      return;
    }
    box.appendChild(el("p", { class: "muted small" }, `${data.terms.length} terms`));
    data.terms.forEach(t => box.appendChild(renderDictTerm(t)));
  } catch {
    box.innerHTML = '<p class="muted center small">Search failed.</p>';
  }
}

// ---------- Police stations ----------
function renderStation(s) {
  const card = el("div", { class: "ps-card" });
  card.appendChild(el("div", { class: "ps-name" }, s.name));
  if (s.address) card.appendChild(el("div", { class: "ps-meta" }, "📍 " + s.address));
  card.appendChild(el("div", { class: "ps-meta" }, `🏙️ ${s.district || ""}, ${s.state || ""}`));
  if (s.phone) card.appendChild(el("div", { class: "ps-meta", style: "color:var(--primary);font-weight:600;font-family:var(--font-mono)" }, "📞 " + s.phone));
  const actions = el("div", { class: "ps-actions" });
  if (s.phone) actions.appendChild(el("a", { href: "tel:" + s.phone.replace(/\s/g, "") }, "📞 Call"));
  const mapsQ = encodeURIComponent((s.name || "") + " " + (s.address || ""));
  actions.appendChild(el("a", { href: `https://www.google.com/maps/search/?api=1&query=${mapsQ}`, target: "_blank", rel: "noopener" }, "📍 Maps"));
  card.appendChild(actions);
  return card;
}

let stationsLoaded = false;
async function loadStations() {
  if (stationsLoaded) return;
  const box = $("#ps-results");
  box.innerHTML = '<p class="muted center small">Loading stations...</p>';
  try {
    const data = await api.policeStations({});
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted small" }, `${data.stations.length} stations · also dial 112 for emergency`));
    data.stations.forEach(s => box.appendChild(renderStation(s)));
    stationsLoaded = true;
  } catch {
    box.innerHTML = '<p class="muted center small">Failed to load.</p>';
  }
}

async function searchStations() {
  const q = $("#ps-query").value.trim();
  const state = $("#ps-state").value;
  const box = $("#ps-results");
  box.innerHTML = '<p class="muted center small">Searching...</p>';
  try {
    const data = await api.policeStations({ q, state });
    box.innerHTML = "";
    if (!data.stations.length) {
      box.innerHTML = '<p class="muted center small">No match. Always dial 112 / 100 for emergency.</p>';
      return;
    }
    box.appendChild(el("p", { class: "muted small" }, `${data.stations.length} stations`));
    data.stations.forEach(s => box.appendChild(renderStation(s)));
  } catch {
    box.innerHTML = '<p class="muted center small">Search failed.</p>';
  }
}

// ---------- Bookmarks ----------
function renderBookmarks() {
  const box = $("#bookmark-list");
  const list = getBookmarks();
  box.innerHTML = "";
  if (!list.length) {
    box.innerHTML = '<p class="muted center small">Nothing saved yet. Tap ⭐ on any section or case to bookmark.</p>';
    return;
  }
  box.appendChild(el("p", { class: "muted small" }, `${list.length} saved items`));
  list.forEach(item => {
    const card = el("div", { class: "law-card" });
    card.appendChild(el("div", { class: "lc-head" }, [
      el("div", { class: "lc-section" }, item.title || item.id),
      el("span", { class: "lc-tag" }, item.type || "saved"),
    ]));
    if (item.description) card.appendChild(el("div", { class: "lc-desc" }, item.description));
    const del = el("button", {
      class: "msg-action",
      type: "button",
      onclick: () => { removeBookmark(item.id, item.type); renderBookmarks(); toast("Removed", "success", 1000); },
    }, "🗑 Remove");
    card.appendChild(del);
    box.appendChild(card);
  });
}

export function initHelpScreen() {
  $$(".help-tab").forEach(t => t.addEventListener("click", () => setHelpTab(t.dataset.helpTab)));
  $("#dict-search-btn")?.addEventListener("click", searchDict);
  $("#dict-query")?.addEventListener("keydown", e => { if (e.key === "Enter") searchDict(); });
  $("#ps-search-btn")?.addEventListener("click", searchStations);
  $("#ps-query")?.addEventListener("keydown", e => { if (e.key === "Enter") searchStations(); });

  const stateSel = $("#ps-state");
  if (stateSel) {
    stateSel.innerHTML = '<option value="">All states</option>';
    INDIAN_STATES.forEach(s => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s;
      stateSel.appendChild(o);
    });
  }

  loadEmergency();
}
