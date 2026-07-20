import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// In-memory bearer token fallback. Used when cookies are blocked or dropped by strict
// browser policies. Kept in module scope (not localStorage) to reduce XSS blast radius —
// on hard page refresh we rely on the httpOnly refresh cookie to re-issue a token.
let bearerToken = null;
export const setBearerToken = (token) => { bearerToken = token || null; };
export const getBearerToken = () => bearerToken;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Attach Authorization header if we have a bearer token in memory
api.interceptors.request.use((config) => {
  if (bearerToken && !config.headers?.Authorization) {
    config.headers = { ...(config.headers || {}), Authorization: `Bearer ${bearerToken}` };
  }
  return config;
});

// Auto-refresh access token on 401. If refresh fails, redirect to /login.
let isRefreshing = false;
let waitingQueue = [];

function processQueue(error) {
  waitingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve();
  });
  waitingQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;
    const url = original.url || "";
    const isAuthEndpoint = url.includes("/auth/login") ||
                           url.includes("/auth/register") ||
                           url.includes("/auth/refresh") ||
                           url.includes("/auth/logout");

    if (status !== 401 || original._retry || isAuthEndpoint) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        waitingQueue.push({ resolve, reject });
      }).then(() => {
        original._retry = true;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;
    try {
      const refreshRes = await api.post("/auth/refresh");
      const newToken = refreshRes?.data?.access_token;
      if (newToken) setBearerToken(newToken);
      processQueue(null);
      return api(original);
    } catch (refreshErr) {
      processQueue(refreshErr);
      setBearerToken(null);
      if (typeof window !== "undefined" &&
          !window.location.pathname.startsWith("/login") &&
          !window.location.pathname.startsWith("/register")) {
        const from = window.location.pathname + window.location.search;
        window.location.assign(`/login?reason=expired&from=${encodeURIComponent(from)}`);
      }
      return Promise.reject(refreshErr);
    } finally {
      isRefreshing = false;
    }
  }
);

// Format FastAPI error detail (which can be string, array, or object) into a display string.
export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const apiErrorMessage = (err) =>
  formatApiErrorDetail(err?.response?.data?.detail) || err?.message || "Request failed";

// Auth
export const authLogin = async (email, password, remember = false) => {
  const data = await api.post("/auth/login", { email, password, remember }).then((r) => r.data);
  if (data?.access_token) setBearerToken(data.access_token);
  return data;
};
export const authRegister = async (email, password, office_name) => {
  const data = await api.post("/auth/register", { email, password, office_name }).then((r) => r.data);
  if (data?.access_token) setBearerToken(data.access_token);
  return data;
};
export const authLogout = async () => {
  try {
    const data = await api.post("/auth/logout").then((r) => r.data);
    return data;
  } finally {
    setBearerToken(null);
  }
};
export const authMe = () => api.get("/auth/me").then((r) => r.data);

// Catalog
export const listProcedures = () => api.get("/procedures").then((r) => r.data.procedures);
export const listCarriers = () => api.get("/carriers").then((r) => r.data.carriers);

// Narratives
export const generateNarrative = (payload) => api.post("/generate", payload).then((r) => r.data);
export const regenerateField = (payload) => api.post("/regenerate", payload).then((r) => r.data);
export const generateVisit = (payload) => api.post("/visits/generate", payload).then((r) => r.data);

export const listHistory = () => api.get("/history").then((r) => r.data);
export const getHistoryItem = (id) => api.get(`/history/${id}`).then((r) => r.data);
export const updateHistoryItem = (id, payload) => api.patch(`/history/${id}`, payload).then((r) => r.data);
export const deleteHistoryItem = (id) => api.delete(`/history/${id}`).then((r) => r.data);

export const listVisits = () => api.get("/visits").then((r) => r.data);

// Appeals
export const createAppeal = (payload) => api.post("/appeals", payload).then((r) => r.data);
export const listAppeals = () => api.get("/appeals").then((r) => r.data);
export const getAppeal = (id) => api.get(`/appeals/${id}`).then((r) => r.data);
export const updateAppeal = (id, payload) => api.patch(`/appeals/${id}`, payload).then((r) => r.data);
export const deleteAppeal = (id) => api.delete(`/appeals/${id}`).then((r) => r.data);
export const setAppealOutcome = (id, outcome, notes) =>
  api.patch(`/appeals/${id}`, { outcome, outcome_notes: notes || null }).then((r) => r.data);
export const getAppealPatterns = (carrier, procedure_code) => {
  const params = new URLSearchParams();
  if (carrier) params.set("carrier", carrier);
  if (procedure_code) params.set("procedure_code", procedure_code);
  return api.get(`/appeals/patterns?${params.toString()}`).then((r) => r.data);
};

// -------- Streaming (SSE-like) --------
// Auth: attach bearer token if we have one in memory.
async function streamSSE(path, payload, { onChunk, onDone, onError, signal }) {
  const url = `${API}${path}`;
  const headers = { "Content-Type": "application/json" };
  if (bearerToken) headers.Authorization = `Bearer ${bearerToken}`;
  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify(payload),
      signal,
    });
  } catch (e) {
    onError?.(e);
    return;
  }
  if (!res.ok || !res.body) {
    onError?.(new Error(`HTTP ${res.status}`));
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buf = "";
  // Parse SSE frames: `event: name\ndata: payload\n\n`
  const dispatch = (event, data) => {
    const clean = data.replace(/\\n/g, "\n");
    if (event === "chunk") onChunk?.(clean);
    else if (event === "done") { try { onDone?.(JSON.parse(clean)); } catch { onDone?.({ raw: clean }); } }
    else if (event === "error") onError?.(new Error(clean));
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const lines = frame.split("\n");
        let event = "message", data = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) event = line.slice(7).trim();
          else if (line.startsWith("data: ")) data += line.slice(6);
        }
        if (event || data) dispatch(event, data);
      }
    }
  } catch (e) {
    if (e?.name !== "AbortError") onError?.(e);
  }
}

// Incrementally parse marker-tagged text as it streams in.
// Feed chunks via feed(text); read current state from .short / .long / .subject / .letter.
export function makeMarkerParser() {
  const state = { short: "", long: "", subject: "", letter: "", buffer: "", current: null };
  const map = { SHORT: "short", LONG: "long", SUBJECT: "subject", LETTER: "letter" };
  const tagRe = /\[(\/?)(SHORT|LONG|SUBJECT|LETTER)\]/i;
  const feed = (chunk) => {
    state.buffer += chunk;
    // Loop: find the next tag; append preceding text to current field; toggle current.
    // Stop when no complete tag is available (leave trailing partial in buffer).
    while (true) {
      const m = state.buffer.match(tagRe);
      if (!m) {
        // No tag anywhere - it could still be forming ("[SHO" etc.). Only flush safe text.
        const bracketIdx = state.buffer.lastIndexOf("[");
        const safeEnd = bracketIdx === -1 ? state.buffer.length : bracketIdx;
        if (safeEnd > 0 && state.current) {
          state[map[state.current]] += state.buffer.slice(0, safeEnd);
          state.buffer = state.buffer.slice(safeEnd);
        }
        return;
      }
      const before = state.buffer.slice(0, m.index);
      if (state.current) state[map[state.current]] += before;
      state.buffer = state.buffer.slice(m.index + m[0].length);
      // Strip a single leading newline right after a tag for tidy display
      if (state.buffer.startsWith("\n")) state.buffer = state.buffer.slice(1);
      const closing = !!m[1], name = m[2].toUpperCase();
      if (closing) state.current = null;
      else state.current = name;
    }
  };
  return { feed, state };
}

export const streamGenerate = (payload, handlers) =>
  streamSSE("/generate/stream", payload, handlers);
export const streamRegenerate = (payload, handlers) =>
  streamSSE("/regenerate/stream", payload, handlers);
export const streamAppeal = (payload, handlers) =>
  streamSSE("/appeals/stream", payload, handlers);

// System / self-update
export const getSystemVersion = () => api.get("/system/version").then((r) => r.data);
export const checkForUpdates = () => api.post("/system/check-updates").then((r) => r.data);
export const startUpdate = () => api.post("/system/update").then((r) => r.data);

// Practice settings
export const getPracticeSettings = () => api.get("/settings/practice").then((r) => r.data);
export const savePracticeSettings = (payload) => api.put("/settings/practice", payload).then((r) => r.data);

// Downloads
async function downloadBlob(url, payload, filename) {
  const res = await api.post(url, payload, { responseType: "blob" });
  const blob = new Blob([res.data], { type: res.headers["content-type"] });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

export const exportPdf = (record) =>
  downloadBlob("/export/pdf", record, `claim-${record.procedure_code || "narrative"}.pdf`);
export const exportTxt = (record) =>
  downloadBlob("/export/txt", record, `claim-${record.procedure_code || "narrative"}.txt`);
export const exportVisitPdf = (visit) =>
  downloadBlob("/export/visit/pdf", visit, `visit-packet-${(visit.id || "draft").slice(0, 8)}.pdf`);
export const exportVisitTxt = (visit) =>
  downloadBlob("/export/visit/txt", visit, `visit-packet-${(visit.id || "draft").slice(0, 8)}.txt`);
export const exportAppealPdf = (appeal) =>
  downloadBlob("/export/appeal/pdf", appeal, `appeal-${appeal.procedure_code || "letter"}.pdf`);
export const exportAppealTxt = (appeal) =>
  downloadBlob("/export/appeal/txt", appeal, `appeal-${appeal.procedure_code || "letter"}.txt`);
