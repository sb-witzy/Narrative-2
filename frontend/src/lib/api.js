import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

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
export const authLogin = (email, password) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);
export const authRegister = (email, password, office_name) =>
  api.post("/auth/register", { email, password, office_name }).then((r) => r.data);
export const authLogout = () => api.post("/auth/logout").then((r) => r.data);
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
