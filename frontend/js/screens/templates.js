import { $, $$, el, toast, navigateTo } from "../ui.js";
import { api, ApiError } from "../api.js";
import { settings } from "../state.js";

let loaded = false;
let pickedFile = null;

function renderTemplates(templates) {
  const grid = $("#templates-grid");
  grid.innerHTML = "";
  templates.forEach(t => {
    const card = el("button", {
      class: "template-card",
      type: "button",
      onclick: () => startTemplate(t),
    }, [
      el("div", { class: "tc-icon" }, t.icon || "📄"),
      el("div", { class: "tc-title" }, t.title),
      el("span", { class: "tc-cat" }, t.category),
      el("div", { class: "muted small" }, t.description || ""),
    ]);
    grid.appendChild(card);
  });
}

let fieldDefs = null;
let currentTemplate = null;

async function getFieldDefs() {
  if (fieldDefs) return fieldDefs;
  try {
    const resp = await fetch(settings.apiBase.replace(/\/$/, "") + "/api/templates/field-defs");
    fieldDefs = await resp.json();
  } catch {
    fieldDefs = {};
  }
  return fieldDefs;
}

async function openTemplateModal(template) {
  currentTemplate = template;
  const defs = await getFieldDefs();

  $("#tpl-modal-icon").textContent = template.icon || "📄";
  $("#tpl-modal-title").textContent = template.title;
  $("#tpl-modal-desc").textContent = template.description || "";

  const form = $("#tpl-form");
  form.innerHTML = "";
  form.classList.remove("hidden");
  $("#tpl-result").classList.add("hidden");
  $("#tpl-result").innerHTML = "";
  $("#tpl-generate-btn").textContent = "✨ Generate Document";
  $("#tpl-generate-btn").disabled = false;

  (template.fields || []).forEach(name => {
    const def = defs[name] || { label: name, type: "text", required: false };
    const wrap = el("label", { class: "tpl-field" });
    wrap.appendChild(el("span", { class: "tpl-field-label" }, def.label + (def.required ? " *" : "")));
    let input;
    if (def.type === "textarea") {
      input = el("textarea", { name, rows: "3", required: def.required ? "true" : null });
    } else {
      input = el("input", { name, type: def.type || "text", required: def.required ? "true" : null });
    }
    wrap.appendChild(input);
    form.appendChild(wrap);
  });

  $("#tpl-modal").classList.remove("hidden");
  setTimeout(() => form.querySelector("input,textarea")?.focus(), 200);
}

function closeTemplateModal() {
  $("#tpl-modal").classList.add("hidden");
}

function downloadText(text, filename) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderTplResult(data) {
  const box = $("#tpl-result");
  box.innerHTML = "";
  box.classList.remove("hidden");
  $("#tpl-form").classList.add("hidden");

  box.appendChild(el("div", { class: "tpl-result-title" }, data.title || currentTemplate.title));
  const pre = el("pre", { class: "tpl-document" }, data.document || "");
  box.appendChild(pre);

  if (data.next_steps?.length) {
    box.appendChild(el("h4", { class: "tpl-result-h" }, "✅ Next steps"));
    const ul = el("ul");
    data.next_steps.forEach(s => ul.appendChild(el("li", {}, s)));
    box.appendChild(ul);
  }
  if (data.warnings?.length) {
    box.appendChild(el("h4", { class: "tpl-result-h warn" }, "⚠ Warnings"));
    const ul = el("ul");
    data.warnings.forEach(s => ul.appendChild(el("li", { class: "warn-li" }, s)));
    box.appendChild(ul);
  }

  const actions = el("div", { class: "tpl-actions" });
  actions.appendChild(el("button", {
    class: "primary-btn", type: "button",
    onclick: () => { navigator.clipboard?.writeText(data.document || ""); toast("Copied", "success", 1200); },
  }, "📋 Copy"));
  actions.appendChild(el("button", {
    class: "primary-btn", type: "button",
    onclick: () => {
      const fname = (currentTemplate.id || "document") + ".txt";
      downloadText(data.document || "", fname);
    },
  }, "💾 Download"));
  actions.appendChild(el("button", {
    class: "primary-btn", type: "button",
    onclick: () => {
      const url = "https://wa.me/?text=" + encodeURIComponent(data.document || "");
      window.open(url, "_blank", "noopener");
    },
  }, "📤 Share"));
  box.appendChild(actions);

  $("#tpl-generate-btn").textContent = "↻ Regenerate";
  $("#tpl-generate-btn").disabled = false;
}

async function submitTemplate() {
  if (!currentTemplate) return;
  const form = $("#tpl-form");
  // If result already shown and user clicks Regenerate — show form again
  if ($("#tpl-result").classList.contains("hidden") === false && form.classList.contains("hidden")) {
    form.classList.remove("hidden");
    $("#tpl-result").classList.add("hidden");
    $("#tpl-generate-btn").textContent = "✨ Generate Document";
    return;
  }
  const fd = new FormData(form);
  const fields = Object.fromEntries(fd.entries());
  // Basic required check
  for (const name of currentTemplate.fields || []) {
    if (!fields[name] || !String(fields[name]).trim()) {
      toast("Please fill: " + name.replace(/_/g, " "), "error");
      return;
    }
  }

  const btn = $("#tpl-generate-btn");
  btn.disabled = true;
  btn.textContent = "✨ Drafting...";

  try {
    const resp = await fetch(settings.apiBase.replace(/\/$/, "") + "/api/templates/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(settings.authToken ? { Authorization: "Bearer " + settings.authToken } : {}) },
      body: JSON.stringify({
        template_id: currentTemplate.id,
        fields,
        state: settings.state,
      }),
    });
    const data = await resp.json();
    if (data.status === "success" && data.document) {
      renderTplResult(data);
      toast("Document ready!", "success");
    } else {
      toast(data.message || "Generation failed", "error");
      btn.disabled = false;
      btn.textContent = "✨ Generate Document";
    }
  } catch (err) {
    toast("Network error", "error");
    btn.disabled = false;
    btn.textContent = "✨ Generate Document";
  }
}

function startTemplate(template) {
  if (template.id === "police_complaint") {
    navigateTo("complaint");
    return;
  }
  openTemplateModal(template);
}

function setDocsTab(name) {
  $$(".docs-tab").forEach(t => t.classList.toggle("active", t.dataset.docsTab === name));
  $("#docs-pane-templates").classList.toggle("active", name === "templates");
  $("#docs-pane-analyse").classList.toggle("active", name === "analyse");
}

function renderAnalysis(data) {
  const box = $("#doc-result");
  box.innerHTML = "";
  box.classList.remove("hidden");

  const card = el("div", { class: "doc-card" });
  card.appendChild(el("div", { class: "doc-type" }, data.doc_type || "Document"));
  card.appendChild(el("div", { class: "doc-title" }, data.title || ""));
  if (data.what_it_is) card.appendChild(el("div", { class: "doc-what" }, data.what_it_is));

  if (data.key_points?.length) {
    data.key_points.forEach(kp => {
      const row = el("div", { class: "doc-kv-row" });
      row.appendChild(el("div", { class: "k" }, String(kp.label || "")));
      row.appendChild(el("div", { class: "v" }, String(kp.value || "—")));
      card.appendChild(row);
    });
  }
  if (data.risk_level) {
    card.appendChild(el("div", { class: `doc-risk ${data.risk_level}` }, "Risk: " + data.risk_level.toUpperCase()));
  }
  if (data.deadline && data.deadline !== "None") {
    card.appendChild(el("div", { class: "doc-kv-row" }, [
      el("div", { class: "k" }, "⏰ Deadline"),
      el("div", { class: "v" }, String(data.deadline)),
    ]));
  }
  box.appendChild(card);

  if (data.what_to_do) {
    const advice = el("div", { class: "doc-card" });
    advice.appendChild(el("div", { class: "doc-type" }, "What to do"));
    advice.appendChild(el("div", { class: "doc-what" }, data.what_to_do));
    box.appendChild(advice);
  }

  if (data.sections_cited?.length) {
    const sec = el("div", { class: "doc-card" });
    sec.appendChild(el("div", { class: "doc-type" }, "Sections cited"));
    sec.appendChild(el("div", { class: "doc-what" }, data.sections_cited.join(" · ")));
    box.appendChild(sec);
  }

  if (data.alerts?.length) {
    const al = el("div", { class: "doc-card" });
    al.appendChild(el("div", { class: "doc-type" }, "⚠️ Alerts"));
    const ul = el("ul", { style: "margin:6px 0 0 18px" });
    data.alerts.forEach(a => ul.appendChild(el("li", {}, String(a))));
    al.appendChild(ul);
    box.appendChild(al);
  }

  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitAnalysis() {
  const text = $("#doc-text").value.trim();
  const lang = $("#doc-lang").value;
  if (!text && !pickedFile) { toast("Upload a file or paste text", "error"); return; }

  const btn = $("#doc-analyse-btn");
  btn.disabled = true;
  btn.textContent = "Analysing...";

  const fd = new FormData();
  fd.append("language", lang);
  if (pickedFile) fd.append("file", pickedFile);
  if (text) fd.append("text", text);

  try {
    const data = await api.analyseDoc(fd);
    if (data.response) {
      renderAnalysis(data.response);
      toast("Analysis ready", "success");
    } else {
      toast(data.message || "Failed", "error");
    }
  } catch (err) {
    toast(err instanceof ApiError ? err.message : "Network error", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyse Document";
  }
}

function setupDocAnalyser() {
  // Always wire docs-tab switching first, even if upload elements are missing
  $$(".docs-tab").forEach(t => t.addEventListener("click", () => setDocsTab(t.dataset.docsTab)));
  $("#doc-analyse-btn")?.addEventListener("click", submitAnalysis);

  const zone = $("#upload-zone");
  const input = $("#doc-file");
  if (!zone || !input) return;
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag");
    if (e.dataTransfer.files?.length) setFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => {
    if (input.files?.length) setFile(input.files[0]);
  });

  function setFile(f) {
    if (f.size > 10 * 1024 * 1024) { toast("File too large (max 10MB)", "error"); return; }
    pickedFile = f;
    zone.classList.add("has-file");
    zone.querySelector("div:nth-child(2)").textContent = "✅ " + f.name;
  }
}

function setupTemplateModal() {
  const modal = document.getElementById("tpl-modal");
  if (!modal || modal.dataset.wired === "1") return;
  modal.dataset.wired = "1";
  document.getElementById("tpl-modal-close")?.addEventListener("click", closeTemplateModal);
  document.getElementById("tpl-generate-btn")?.addEventListener("click", submitTemplate);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeTemplateModal(); });
}

export async function initTemplatesScreen() {
  setupDocAnalyser();
  setupTemplateModal();
  if (loaded) return;
  try {
    const data = await api.listTemplates();
    renderTemplates(data);
    loaded = true;
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : "Could not load templates.";
    $("#templates-grid").innerHTML = "";
    $("#templates-grid").appendChild(el("p", { class: "muted center" }, msg));
  }
}
