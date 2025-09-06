// src/api/savings.js
import api from "./axiosInstance";

export async function fetchSavings() {
  const res = await api.get("/api/savings/");
  return res.data;
}
