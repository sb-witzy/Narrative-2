import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const listProcedures = () => api.get("/procedures").then((r) => r.data.procedures);
export const listCarriers = () => api.get("/carriers").then((r) => r.data.carriers);
export const generateNarrative = (payload) => api.post("/generate", payload).then((r) => r.data);
export const regenerateField = (payload) => api.post("/regenerate", payload).then((r) => r.data);
export const generateVisit = (payload) => api.post("/visits/generate", payload).then((r) => r.data);

export const listHistory = () => api.get("/history").then((r) => r.data);
export const getHistoryItem = (id) => api.get(`/history/${id}`).then((r) => r.data);
export const updateHistoryItem = (id, payload) => api.patch(`/history/${id}`, payload).then((r) => r.data);
export const deleteHistoryItem = (id) => api.delete(`/history/${id}`).then((r) => r.data);

export const listVisits = () => api.get("/visits").then((r) => r.data);

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
