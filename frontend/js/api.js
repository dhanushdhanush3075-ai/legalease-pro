import { settings } from "./state.js";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, signal, auth = true } = {}) {
  const url = settings.apiBase.replace(/\/$/, "") + path;
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && settings.authToken) headers["Authorization"] = `Bearer ${settings.authToken}`;
  let resp;
  try {
    resp = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e) {
    throw new ApiError("Network error. Check API server.", 0);
  }
  if (resp.status === 401 && auth) {
    settings.authToken = null;
    settings.user = null;
    window.dispatchEvent(new CustomEvent("auth:expired"));
  }
  const text = await resp.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }

  if (!resp.ok) {
    const msg = data?.detail || data?.message || `Request failed (${resp.status})`;
    throw new ApiError(msg, resp.status);
  }
  return data;
}

export const api = {
  health: () => request("/api/health", { auth: false }),

  // Auth
  sendOtp: (payload) => request("/api/auth/send-otp", { method: "POST", body: payload, auth: false }),
  verifyOtp: (payload) => request("/api/auth/verify-otp", { method: "POST", body: payload, auth: false }),
  me: () => request("/api/auth/me"),
  logout: () => request("/api/auth/logout", { method: "POST" }),

  // Chat & complaint
  chat: (payload) => request("/api/legal/query", { method: "POST", body: payload }),
  complaint: (payload) => request("/api/legal/complaint", { method: "POST", body: payload }),

  // History
  listSessions: (deviceId) =>
    request(`/api/history/sessions?device_id=${encodeURIComponent(deviceId)}&limit=50`),
  getMessages: (sessionId) => request(`/api/history/sessions/${sessionId}/messages`),
  deleteSession: (sessionId) =>
    request(`/api/history/sessions/${sessionId}`, { method: "DELETE" }),

  // Templates
  listTemplates: () => request("/api/templates/"),

  // Laws
  lawSection: (q) => request(`/api/laws/section?q=${encodeURIComponent(q || "")}`),
  caseSearch: (q) => request(`/api/laws/cases/search?q=${encodeURIComponent(q)}`),
  landmarkCases: () => request("/api/laws/landmark?limit=100"),

  // Document analyser (multipart upload)
  analyseDoc: (formData) => {
    const headers = settings.authToken ? { Authorization: `Bearer ${settings.authToken}` } : {};
    return fetch(settings.apiBase.replace(/\/$/, "") + "/api/legal/analyse-doc", {
      method: "POST",
      body: formData,
      headers,
    }).then(async r => {
      const text = await r.text();
      let data; try { data = JSON.parse(text); } catch { data = { raw: text }; }
      if (!r.ok) throw new ApiError(data?.detail || data?.message || "Analyse failed", r.status);
      return data;
    });
  },

  // Courts
  listCourts: ({ state = "", city = "", type = "", q = "" } = {}) =>
    request(`/api/courts/?state=${encodeURIComponent(state)}&city=${encodeURIComponent(city)}&type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}&limit=100`),

  // Calculators
  bailCheck: (section) => request(`/api/calc/bail?section=${encodeURIComponent(section)}`),
  limitationList: (q = "") => request(`/api/calc/limitation?q=${encodeURIComponent(q)}`),
  courtFee: (state, claim_value) =>
    request(`/api/calc/court-fee?state=${encodeURIComponent(state)}&claim_value=${claim_value}`),

  // Lawyers / legal aid
  listLawyers: ({ state = "", type = "", q = "" } = {}) =>
    request(`/api/lawyers/?state=${encodeURIComponent(state)}&type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}&limit=100`),
  helplines: () => request("/api/lawyers/helplines"),

  // Case tracker
  trackCnr: (cnr) => request(`/api/tracker/cnr?cnr=${encodeURIComponent(cnr)}`),
  trackParty: (name, state) =>
    request(`/api/tracker/by-party?name=${encodeURIComponent(name)}&state=${encodeURIComponent(state || "")}`),

  // News
  news: ({ q = "", source = "", limit = 30 } = {}) =>
    request(`/api/news/?q=${encodeURIComponent(q)}&source=${encodeURIComponent(source)}&limit=${limit}`),
  newsFeatured: () => request("/api/news/featured"),

  // Core (no AI)
  emergencyCards: () => request("/api/core/emergency-cards", { auth: false }),
  dictionary: (q = "") => request(`/api/core/dictionary?q=${encodeURIComponent(q)}`, { auth: false }),
  policeStations: ({ q = "", state = "", district = "" } = {}) =>
    request(`/api/core/police-stations?q=${encodeURIComponent(q)}&state=${encodeURIComponent(state)}&district=${encodeURIComponent(district)}`, { auth: false }),
};

export { ApiError };
