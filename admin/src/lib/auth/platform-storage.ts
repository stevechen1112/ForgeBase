/** Separate storage key for platform admin — never collides with tenant auth. */
const STORAGE_KEY = "fb_platform_auth";

function getSessionStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function getLocalStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readPlatformAuthStorage(): string | null {
  const ss = getSessionStorage();
  if (ss) {
    const v = ss.getItem(STORAGE_KEY);
    if (v) return v;
  }
  const ls = getLocalStorage();
  const v = ls?.getItem(STORAGE_KEY) ?? null;
  if (v && ss) {
    ss.setItem(STORAGE_KEY, v);
    ls?.removeItem(STORAGE_KEY);
  }
  return v;
}

export function writePlatformAuthStorage(value: string): void {
  getSessionStorage()?.setItem(STORAGE_KEY, value);
  getLocalStorage()?.removeItem(STORAGE_KEY);
}

export function clearPlatformAuthStorage(): void {
  getSessionStorage()?.removeItem(STORAGE_KEY);
  getLocalStorage()?.removeItem(STORAGE_KEY);
}
