import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const listProcedures = () => api.get("/procedures").then((r) => r.data.procedures);
export const generateNarrative = (payload) => api.post("/generate", payload).then((r) => r.data);
export const listHistory = () => api.get("/history").then((r) => r.data);
export const getHistoryItem = (id) => api.get(`/history/${id}`).then((r) => r.data);
export const deleteHistoryItem = (id) => api.delete(`/history/${id}`).then((r) => r.data);
