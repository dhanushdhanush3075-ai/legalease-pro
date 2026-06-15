import { $, $$, el, toast } from "../ui.js";
import { api, ApiError } from "../api.js";
import { INDIAN_STATES } from "../state.js";

let landmarkLoaded = false;
let courtsLoaded = false;
let lawyersLoaded = false;

function setTab(name) {
  $$(".laws-tab").forEach(t => t.classList.toggle("active", t.dataset.lawsTab === name));
  ["section", "cases", "landmark", "courts", "calc", "lawyers", "tracker"].forEach(n => {
    const pane = document.getElementById(`laws-pane-${n}`);
    if (pane) pane.classList.toggle("active", n === name);
  });
  if (name === "landmark") loadLandmark();
  if (name === "courts") loadCourts();
  if (name === "lawyers") loadLawyers();
}

function renderSection(s) {
  const card = el("div", { class: "law-card" });
  const head = el("div", { class: "lc-head" });
  const sectionLine = el("div", { class: "lc-section" }, `IPC ${s.ipc || "—"} ↔ BNS ${s.bns || "—"}`);
  head.appendChild(sectionLine);
  head.appendChild(el("span", { class: "lc-tag" }, s.category || ""));
  card.appendChild(head);
  card.appendChild(el("div", { class: "lc-title" }, s.title || ""));
  if (s.punishment) {
    card.appendChild(el("div", { class: "lc-desc" }, [
      el("b", {}, "Punishment: "),
      document.createTextNode(s.punishment),
    ]));
  }
  if (s.keywords?.length) {
    card.appendChild(el("div", { class: "lc-meta" }, [
      el("b", {}, "Tags: "),
      document.createTextNode(s.keywords.join(", ")),
    ]));
  }
  return card;
}

function renderSpecial(s) {
  const card = el("div", { class: "law-card" });
  const head = el("div", { class: "lc-head" });
  head.appendChild(el("div", { class: "lc-section" }, s.code || ""));
  head.appendChild(el("span", { class: "lc-tag bns" }, "SPECIAL ACT"));
  card.appendChild(head);
  card.appendChild(el("div", { class: "lc-title" }, s.name + " — " + s.title));
  if (s.punishment) {
    card.appendChild(el("div", { class: "lc-desc" }, [
      el("b", {}, "Punishment: "),
      document.createTextNode(s.punishment),
    ]));
  }
  return card;
}

function renderCase(c) {
  const card = el("div", { class: "law-card" });
  const head = el("div", { class: "lc-head" });
  head.appendChild(el("div", { class: "lc-section" }, c.title || ""));
  head.appendChild(el("span", { class: "lc-tag" }, String(c.year || "")));
  card.appendChild(head);
  if (c.citation) card.appendChild(el("div", { class: "lc-meta" }, [
    el("b", {}, "Citation: "), document.createTextNode(c.citation),
    document.createTextNode("  ·  "), el("b", {}, "Bench: "), document.createTextNode(c.bench || ""),
  ]));
  if (c.issue) card.appendChild(el("div", { class: "lc-desc" }, [el("b", {}, "Issue: "), document.createTextNode(c.issue)]));
  if (c.ruling) card.appendChild(el("div", { class: "lc-desc" }, [el("b", {}, "Ruling: "), document.createTextNode(c.ruling)]));
  if (c.tags?.length) card.appendChild(el("div", { class: "lc-meta" }, [
    el("b", {}, "Tags: "), document.createTextNode(c.tags.join(", ")),
  ]));
  return card;
}

function renderKanoonResult(r) {
  const card = el("div", { class: "law-card" });
  const head = el("div", { class: "lc-head" });
  head.appendChild(el("div", { class: "lc-section" }, r.title || ""));
  if (r.date) head.appendChild(el("span", { class: "lc-tag" }, String(r.date)));
  card.appendChild(head);
  if (r.court) card.appendChild(el("div", { class: "lc-meta" }, [el("b", {}, "Court: "), document.createTextNode(r.court)]));
  if (r.snippet) card.appendChild(el("div", { class: "lc-desc" }, r.snippet));
  if (r.url) {
    const link = el("a", { class: "lc-link", href: r.url, target: "_blank", rel: "noopener" }, "Open full judgment on Indian Kanoon ↗");
    card.appendChild(link);
  }
  return card;
}

async function searchSections() {
  const q = $("#law-query").value.trim();
  const box = $("#law-results");
  box.innerHTML = "";
  box.appendChild(el("p", { class: "muted center" }, "Searching..."));
  try {
    const data = await api.lawSection(q);
    box.innerHTML = "";
    const total = (data.ipc_bns?.length || 0) + (data.special_acts?.length || 0);
    if (!total) {
      box.appendChild(el("p", { class: "muted center" }, "No matches. Try a section number, keyword, or category."));
      return;
    }
    box.appendChild(el("p", { class: "muted small" }, `${total} match${total > 1 ? "es" : ""} · BNS replaced IPC effective 1 Jul 2024`));
    data.ipc_bns?.forEach(s => box.appendChild(renderSection(s)));
    data.special_acts?.forEach(s => box.appendChild(renderSpecial(s)));
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, err instanceof ApiError ? err.message : "Search failed."));
  }
}

async function searchCases() {
  const q = $("#case-query").value.trim();
  if (!q) { toast("Type a case keyword first", "error"); return; }
  const box = $("#case-results");
  box.innerHTML = "";
  box.appendChild(el("p", { class: "muted center" }, "Searching..."));

  // First search our curated 70 landmark DB (instant + always works)
  try {
    const lm = await api.landmarkCases();
    const ql = q.toLowerCase();
    const matches = (lm.cases || []).filter(c => {
      const hay = (c.title + " " + c.issue + " " + c.ruling + " " + (c.tags||[]).join(" ") + " " + c.category).toLowerCase();
      return hay.includes(ql);
    }).slice(0, 8);

    box.innerHTML = "";
    if (matches.length) {
      box.appendChild(el("p", { class: "muted small" }, `📚 ${matches.length} landmark cases from our database`));
      matches.forEach(c => box.appendChild(renderCase(c)));
    }

    // Then add live Indian Kanoon link
    const data = await api.caseSearch(q);
    if (data.results?.length) {
      box.appendChild(el("p", { class: "muted small", style: "margin-top:14px" }, "🌐 Or search 6M+ judgments live on Indian Kanoon:"));
      data.results.forEach(r => box.appendChild(renderKanoonResult(r)));
    }

    if (!matches.length && !data.results?.length) {
      box.appendChild(el("p", { class: "muted center" }, "No matches. Try simpler keywords like 'rape', 'bail', 'cheque'."));
    }
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, "Search failed."));
  }
}

async function filterByCategory(cat) {
  // Highlight the chip
  document.querySelectorAll(".case-cat-chip").forEach(c => c.classList.toggle("active", c.dataset.cat === cat));
  // Switch to Landmark tab and filter
  setTab("landmark");
  const box = $("#landmark-list");
  box.innerHTML = "";
  box.appendChild(el("p", { class: "muted center" }, "Loading..."));
  try {
    const data = await api.landmarkCases();
    const filtered = (data.cases || []).filter(c => (c.category || "").toLowerCase().includes(cat.toLowerCase()) || (c.tags || []).some(t => t.toLowerCase().includes(cat.toLowerCase())));
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted small" }, `${filtered.length} ${cat} cases · most recent first`));
    filtered.forEach(c => box.appendChild(renderCase(c)));
    landmarkLoaded = true;
  } catch {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, "Failed to load."));
  }
}

async function loadLandmark() {
  if (landmarkLoaded) return;
  const box = $("#landmark-list");
  box.innerHTML = "";
  box.appendChild(el("p", { class: "muted center" }, "Loading landmark cases..."));
  try {
    const data = await api.landmarkCases();
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted small" }, `${data.cases.length} landmark cases · ${data.meta.description}`));
    data.cases.forEach(c => box.appendChild(renderCase(c)));
    landmarkLoaded = true;
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, "Could not load."));
  }
}

// ---------------- Courts ----------------
function renderCourt(c) {
  const card = el("div", { class: "court-card" });
  card.appendChild(el("div", { class: "ct-type" }, c.type || ""));
  card.appendChild(el("div", { class: "ct-name" }, c.name || ""));
  if (c.address) card.appendChild(el("div", { class: "ct-addr" }, c.address));
  if (c.phone) card.appendChild(el("div", { class: "ct-phone" }, "📞 " + c.phone));
  if (c.jurisdiction) card.appendChild(el("div", { class: "muted small" }, "Jurisdiction: " + c.jurisdiction));
  const actions = el("div", { class: "ct-actions" });
  if (c.phone) actions.appendChild(el("a", { href: "tel:" + c.phone.replace(/\s/g, "") }, "📞 Call"));
  if (c.website) actions.appendChild(el("a", { href: c.website, target: "_blank", rel: "noopener" }, "🌐 Website"));
  if (c.ecourts) actions.appendChild(el("a", { href: c.ecourts, target: "_blank", rel: "noopener" }, "⚖️ eCourts"));
  const mapsQ = encodeURIComponent((c.name || "") + " " + (c.address || ""));
  actions.appendChild(el("a", { href: `https://www.google.com/maps/search/?api=1&query=${mapsQ}`, target: "_blank", rel: "noopener" }, "📍 Maps"));
  card.appendChild(actions);
  return card;
}

async function loadCourts() {
  const box = $("#court-results");
  if (!box) return;
  if (courtsLoaded) return;
  box.innerHTML = "";
  box.appendChild(el("p", { class: "muted center" }, "Loading courts..."));
  try {
    const data = await api.listCourts({});
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted small" }, `${data.courts.length} courts in directory`));
    data.courts.forEach(c => box.appendChild(renderCourt(c)));
    courtsLoaded = true;
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, err instanceof ApiError ? err.message : "Failed to load."));
  }
}

async function searchCourts() {
  const q = $("#court-query").value.trim();
  const state = $("#court-state").value;
  const box = $("#court-results");
  box.innerHTML = "";
  box.appendChild(el("p", { class: "muted center" }, "Searching..."));
  try {
    const data = await api.listCourts({ q, state });
    box.innerHTML = "";
    if (!data.courts.length) {
      box.appendChild(el("p", { class: "muted center" }, "No courts match."));
      return;
    }
    box.appendChild(el("p", { class: "muted small" }, `${data.courts.length} courts`));
    data.courts.forEach(c => box.appendChild(renderCourt(c)));
  } catch (err) {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, "Search failed."));
  }
}

// ---------------- Calculators ----------------
async function checkBail() {
  const sec = $("#bail-section").value.trim();
  if (!sec) { toast("Enter a section number", "error"); return; }
  const box = $("#bail-result");
  box.innerHTML = "";
  try {
    const data = await api.bailCheck(sec);
    if (data.status === "unknown") {
      box.appendChild(el("div", { class: "calc-result-card bad" }, data.message || "Unknown section."));
      return;
    }
    const card = el("div", { class: "calc-result-card" });
    card.appendChild(el("div", { class: "doc-title" }, data.title || sec));
    const badges = el("div", { style: "margin:6px 0" });
    badges.appendChild(el("span", { class: `badge ${data.bailable ? "green" : "red"}` }, data.bailable ? "BAILABLE" : "NON-BAILABLE"));
    badges.appendChild(el("span", { class: `badge ${data.cognizable ? "red" : "green"}` }, data.cognizable ? "COGNIZABLE" : "NON-COGNIZABLE"));
    badges.appendChild(el("span", { class: "badge gold" }, data.court));
    card.appendChild(badges);
    card.appendChild(el("p", { class: "muted small" }, data.summary));
    box.appendChild(card);
  } catch (err) {
    box.appendChild(el("p", { class: "muted center" }, "Lookup failed."));
  }
}

async function searchLimitation() {
  const q = $("#limit-q").value.trim();
  const box = $("#limit-result");
  box.innerHTML = "";
  try {
    const data = await api.limitationList(q);
    if (!data.items.length) {
      box.appendChild(el("p", { class: "muted center" }, "No matches. Try 'appeal', 'tort', 'consumer'."));
      return;
    }
    data.items.forEach(item => {
      const card = el("div", { class: "calc-result-card" });
      card.appendChild(el("div", { class: "doc-title" }, item.title));
      const period = item.period_years ? `${item.period_years} year${item.period_years > 1 ? "s" : ""}` : (item.period_days ? `${item.period_days} days` : "Varies");
      card.appendChild(el("div", { style: "margin:4px 0" }, [
        el("span", { class: "badge gold" }, item.category || "Civil"),
        el("span", { class: "badge green" }, period),
      ]));
      if (item.note) card.appendChild(el("p", { class: "muted small" }, item.note));
      box.appendChild(card);
    });
  } catch (err) {
    box.appendChild(el("p", { class: "muted center" }, "Lookup failed."));
  }
}

async function estimateFee() {
  const state = $("#fee-state").value;
  const value = parseFloat($("#fee-value").value || "0");
  if (!value || value <= 0) { toast("Enter a claim value", "error"); return; }
  const box = $("#fee-result");
  box.innerHTML = "";
  try {
    const data = await api.courtFee(state, value);
    const card = el("div", { class: "calc-result-card" });
    card.appendChild(el("div", { class: "doc-title" }, `Estimated court fee · ${state}`));
    card.appendChild(el("div", { style: "margin:6px 0" }, [
      el("span", { class: "badge gold" }, data.applicable_slab || ""),
      el("span", { class: "badge green" }, data.estimate_inr ? `₹${data.estimate_inr.toLocaleString("en-IN")}` : "—"),
    ]));
    card.appendChild(el("p", { class: "muted small" }, `Maximum: ${data.max_fee} · ${data.act}`));
    card.appendChild(el("p", { class: "muted small" }, data.disclaimer));
    box.appendChild(card);
  } catch (err) {
    box.appendChild(el("p", { class: "muted center" }, "Estimate failed."));
  }
}

// ---------------- Lawyers / Legal Aid ----------------
function renderHelpline(h) {
  const card = el("a", {
    class: "helpline-card",
    href: "tel:" + (h.number || ""),
  }, [
    el("div", { class: "hp-num" }, h.number || ""),
    el("div", { class: "hp-label" }, h.label || ""),
    el("div", { class: "hp-hours" }, h.hours || ""),
  ]);
  return card;
}

function renderLawyer(l) {
  const card = el("div", { class: "court-card" });
  card.appendChild(el("div", { class: "ct-type" }, l.type || ""));
  card.appendChild(el("div", { class: "ct-name" }, l.name || ""));
  if (l.address) card.appendChild(el("div", { class: "ct-addr" }, l.address));
  if (l.phone) card.appendChild(el("div", { class: "ct-phone" }, "📞 " + l.phone));
  if (l.specialization?.length) {
    card.appendChild(el("div", { class: "muted small" }, "Handles: " + l.specialization.join(", ")));
  }
  if (l.free) card.appendChild(el("div", { class: "muted small", style: "color:var(--primary);font-weight:700" }, "✓ FREE legal aid"));
  const actions = el("div", { class: "ct-actions" });
  if (l.phone) actions.appendChild(el("a", { href: "tel:" + l.phone.replace(/\s/g, "") }, "📞 Call"));
  if (l.website) actions.appendChild(el("a", { href: l.website, target: "_blank", rel: "noopener" }, "🌐 Site"));
  if (l.email) actions.appendChild(el("a", { href: "mailto:" + l.email }, "✉ Email"));
  card.appendChild(actions);
  return card;
}

async function loadLawyers() {
  if (lawyersLoaded) return;
  const grid = $("#helpline-grid");
  const box = $("#lawyer-results");
  if (!grid || !box) return;
  try {
    const helplines = await api.helplines();
    grid.innerHTML = "";
    Object.values(helplines).forEach(h => grid.appendChild(renderHelpline(h)));
  } catch {}
  try {
    const data = await api.listLawyers({});
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted small" }, `${data.entries.length} legal aid clinics & NGOs`));
    data.entries.forEach(e => box.appendChild(renderLawyer(e)));
    lawyersLoaded = true;
  } catch {
    box.innerHTML = "";
    box.appendChild(el("p", { class: "muted center" }, "Failed to load."));
  }
}

async function searchLawyers() {
  const q = $("#lawyer-query").value.trim();
  const state = $("#lawyer-state").value;
  const box = $("#lawyer-results");
  box.innerHTML = "";
  try {
    const data = await api.listLawyers({ q, state });
    if (!data.entries.length) {
      box.appendChild(el("p", { class: "muted center" }, "No clinics match. Call NALSA 15100 for any state."));
      return;
    }
    box.appendChild(el("p", { class: "muted small" }, `${data.entries.length} matches`));
    data.entries.forEach(e => box.appendChild(renderLawyer(e)));
  } catch {
    box.appendChild(el("p", { class: "muted center" }, "Search failed."));
  }
}

// ---------------- Case Tracker ----------------
function renderTrackerLinks(links, header) {
  const wrap = el("div", { class: "calc-result-card" });
  wrap.appendChild(el("div", { class: "doc-title" }, header));
  Object.entries(links).forEach(([label, url]) => {
    const cleanLabel = label.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    const link = el("a", {
      href: url, target: "_blank", rel: "noopener",
      style: "display:block;padding:8px 12px;margin-top:6px;background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--primary);font-weight:600;font-size:13px;text-decoration:none;",
    }, "→ " + cleanLabel);
    wrap.appendChild(link);
  });
  return wrap;
}

async function lookupCnr() {
  const cnr = $("#cnr-input").value.trim();
  if (!cnr) { toast("Enter a CNR number", "error"); return; }
  const box = $("#cnr-result");
  box.innerHTML = "";
  try {
    const data = await api.trackCnr(cnr);
    if (data.status === "invalid") {
      box.appendChild(el("div", { class: "calc-result-card bad" }, data.message));
      return;
    }
    box.appendChild(renderTrackerLinks(data.links, `CNR ${data.cnr}`));
    box.appendChild(el("p", { class: "muted small", style: "margin-top:8px" }, data.message || ""));
  } catch (err) {
    box.appendChild(el("p", { class: "muted center" }, "Lookup failed."));
  }
}

async function searchParty() {
  const name = $("#party-input").value.trim();
  if (name.length < 3) { toast("Enter at least 3 characters", "error"); return; }
  const box = $("#party-result");
  box.innerHTML = "";
  try {
    const data = await api.trackParty(name);
    box.appendChild(renderTrackerLinks(data.links, `Search: "${name}"`));
    box.appendChild(el("p", { class: "muted small", style: "margin-top:8px" }, data.note || ""));
  } catch {
    box.appendChild(el("p", { class: "muted center" }, "Search failed."));
  }
}

export function initLawsScreen() {
  $$(".laws-tab").forEach(t => t.addEventListener("click", () => setTab(t.dataset.lawsTab)));
  $("#law-search-btn").addEventListener("click", searchSections);
  $("#law-query").addEventListener("keydown", (e) => { if (e.key === "Enter") searchSections(); });
  $("#case-search-btn").addEventListener("click", searchCases);
  $("#case-query").addEventListener("keydown", (e) => { if (e.key === "Enter") searchCases(); });

  // Case category chips
  document.querySelectorAll(".case-cat-chip").forEach(chip => {
    chip.addEventListener("click", () => filterByCategory(chip.dataset.cat));
  });

  // Courts
  const stateSel = $("#court-state");
  if (stateSel) {
    stateSel.innerHTML = '<option value="">All states</option>';
    INDIAN_STATES.forEach(s => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s;
      stateSel.appendChild(o);
    });
  }
  $("#court-search-btn")?.addEventListener("click", searchCourts);
  $("#court-query")?.addEventListener("keydown", (e) => { if (e.key === "Enter") searchCourts(); });

  // Calculators
  $("#bail-check-btn")?.addEventListener("click", checkBail);
  $("#bail-section")?.addEventListener("keydown", (e) => { if (e.key === "Enter") checkBail(); });
  $("#limit-btn")?.addEventListener("click", searchLimitation);
  $("#limit-q")?.addEventListener("keydown", (e) => { if (e.key === "Enter") searchLimitation(); });
  $("#fee-btn")?.addEventListener("click", estimateFee);

  // Court fee states
  const feeSel = $("#fee-state");
  if (feeSel) {
    ["Tamil Nadu", "Maharashtra", "Karnataka", "Delhi", "default"].forEach(s => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s === "default" ? "Other (default)" : s;
      feeSel.appendChild(o);
    });
  }

  // Lawyers
  const lawyerStateSel = $("#lawyer-state");
  if (lawyerStateSel) {
    lawyerStateSel.innerHTML = '<option value="">All states</option>';
    INDIAN_STATES.forEach(s => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s;
      lawyerStateSel.appendChild(o);
    });
  }
  $("#lawyer-search-btn")?.addEventListener("click", searchLawyers);
  $("#lawyer-query")?.addEventListener("keydown", (e) => { if (e.key === "Enter") searchLawyers(); });

  // Case Tracker
  $("#cnr-btn")?.addEventListener("click", lookupCnr);
  $("#cnr-input")?.addEventListener("keydown", (e) => { if (e.key === "Enter") lookupCnr(); });
  $("#party-btn")?.addEventListener("click", searchParty);
  $("#party-input")?.addEventListener("keydown", (e) => { if (e.key === "Enter") searchParty(); });
}
