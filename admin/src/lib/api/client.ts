// Admin API client — 所有對後端 API 的呼叫都經過這個 module
import { clearAuthStorage, readAuthStorage, writeAuthStorage } from "@/lib/auth/storage";

function resolveApiBase(rawBase?: string): string {
  const base = (rawBase || "http://localhost:8000").replace(/\/$/, "");
  return base.endsWith("/api/v1") ? base : `${base}/api/v1`;
}

export const API_BASE = resolveApiBase(process.env.NEXT_PUBLIC_API_URL);

function getTenantIdentifier(): string | null {
  const value = process.env.NEXT_PUBLIC_TENANT_ID || process.env.NEXT_PUBLIC_TENANT_SLUG;
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function buildApiHeaders(token?: string, extraHeaders?: HeadersInit): Headers {
  const headers = new Headers(extraHeaders);
  const tenantIdentifier = getTenantIdentifier();
  if (tenantIdentifier && !headers.has("X-Tenant-ID")) {
    headers.set("X-Tenant-ID", tenantIdentifier);
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

// Token refresh lock — prevent concurrent refresh calls
let refreshPromise: Promise<string | null> | null = null;

async function tryRefreshToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const raw = readAuthStorage();
      if (!raw) return null;
      const stored = JSON.parse(raw);
      const rt = stored?.refresh_token;
      if (!rt) return null;

      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: buildApiHeaders(undefined, { "Content-Type": "application/json" }),
        body: JSON.stringify({ refresh_token: rt }),
      });

      if (!res.ok) return null;

      const data = await res.json();
      writeAuthStorage(JSON.stringify(data));
      window.dispatchEvent(new CustomEvent("auth:refreshed", { detail: data }));
      return data.access_token as string;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string;
};

function formatApiError(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (!payload || typeof payload !== "object") return fallback;

  const record = payload as Record<string, unknown>;
  const detail = record.detail ?? record.error ?? record.message;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (!item || typeof item !== "object") return "";
        const issue = item as Record<string, unknown>;
        const location = Array.isArray(issue.loc)
          ? issue.loc.filter((part) => part !== "body").join(" → ")
          : "";
        const message = typeof issue.msg === "string" ? issue.msg : "輸入資料格式不正確";
        return location ? `${location}：${message}` : message;
      })
      .filter(Boolean);
    if (messages.length) return messages.join("；");
  }

  return fallback;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers = buildApiHeaders(token, { "Content-Type": "application/json" });

  let res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // On 401, try to refresh the token once before giving up
  if (res.status === 401 && !path.startsWith("/auth/refresh")) {
    const newToken = await tryRefreshToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    }
  }

  if (!res.ok) {
    if (res.status === 401) {
      clearAuthStorage();
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    const err = await res.json().catch(() => null);
    throw new Error(formatApiError(err, `操作失敗（HTTP ${res.status}）`));
  }

  if (res.status === 204 || res.status === 205) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return res.json();
}

async function requestForm<T>(path: string, formData: FormData, token?: string): Promise<T> {
  const headers = buildApiHeaders(token);

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    if (res.status === 401) {
      clearAuthStorage();
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    const err = await res.json().catch(() => null);
    throw new Error(formatApiError(err, `上傳失敗（HTTP ${res.status}）`));
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
