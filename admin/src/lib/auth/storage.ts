const STORAGE_KEY = "fb_auth";

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

export function readAuthStorage(): string | null {
  const sessionStorage = getSessionStorage();
  if (sessionStorage) {
    const sessionValue = sessionStorage.getItem(STORAGE_KEY);
    if (sessionValue) return sessionValue;
  }

  const localStorage = getLocalStorage();
  const localValue = localStorage?.getItem(STORAGE_KEY) ?? null;
  if (localValue && sessionStorage) {
    sessionStorage.setItem(STORAGE_KEY, localValue);
    localStorage?.removeItem(STORAGE_KEY);
  }

  return localValue;
}

export function writeAuthStorage(value: string): void {
  const sessionStorage = getSessionStorage();
  if (sessionStorage) {
    sessionStorage.setItem(STORAGE_KEY, value);
  }
  const localStorage = getLocalStorage();
  if (localStorage) {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function clearAuthStorage(): void {
  getSessionStorage()?.removeItem(STORAGE_KEY);
  getLocalStorage()?.removeItem(STORAGE_KEY);
}