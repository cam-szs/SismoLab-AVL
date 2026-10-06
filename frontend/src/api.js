import { translateError } from "./errorMessages";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = Array.isArray(payload?.detail)
      ? payload.detail.map((item) => `${item.loc?.at(-1) ?? ""}: ${item.msg}`).join("; ")
      : payload?.detail;
    throw new Error(translateError(detail || payload?.error) || "Error del backend");
  }
  return response.json();
}
