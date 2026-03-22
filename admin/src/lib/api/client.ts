// Admin API client — 所有對後端 API 的呼叫都經過這個 module
function resolveApiBase(rawBase?: string): string {
  const base = (rawBase || "http://localhost:8000").replace(/\/$/, "");
  return base.endsWith("/api/v1") ? base : `${base}/api/v1`;
}

export const API_BASE = resolveApiBase(process.env.NEXT_PUBLIC_API_URL);

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

async function requestForm<T>(path: string, formData: FormData, token?: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }

  return res.json();
}

export const apiClient = {
  get: <T>(path: string, token?: string) =>
    request<T>(path, { method: "GET", token }),

  post: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "POST", body, token }),

  put: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "PUT", body, token }),

  patch: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "PATCH", body, token }),

  del: <T>(path: string, token?: string) =>
    request<T>(path, { method: "DELETE", token }),

  postForm: <T>(path: string, formData: FormData, token?: string) =>
    requestForm<T>(path, formData, token),
};
