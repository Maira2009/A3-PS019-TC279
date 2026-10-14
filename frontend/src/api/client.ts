export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let body: { error?: { code?: string; message?: string } } = {};
    try { body = await response.json(); } catch { /* safe fallback */ }
    throw new ApiError(body.error?.code ?? "REQUEST_FAILED", body.error?.message ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, {
    method: "POST", headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  }),
  put: <T>(path: string, body: unknown) => request<T>(path, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, files: File[], field = "files") => {
    const form = new FormData(); files.forEach(file => form.append(field, file));
    return request<T>(path, { method: "POST", body: form });
  }
};

