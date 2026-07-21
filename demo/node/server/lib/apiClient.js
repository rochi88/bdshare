const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function apiGet(path) {
  const res = await fetch(`${API_BASE_URL}${path}`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(body.detail || `API error ${res.status}`, res.status);
  return body;
}

async function apiPost(path, data) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(body.detail || `API error ${res.status}`, res.status);
  return body;
}

export { apiGet, apiPost, ApiError };
