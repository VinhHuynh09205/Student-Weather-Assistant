const AUTH_TOKEN_KEY = "student_weather_token";

type TokenStorage = Pick<Storage, "getItem" | "removeItem" | "setItem">;

export function getStoredAuthToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_KEY) ?? window.sessionStorage.getItem(AUTH_TOKEN_KEY);
}

export function storeAuthToken(token: string, rememberLogin: boolean): void {
  const targetStorage: TokenStorage = rememberLogin ? window.localStorage : window.sessionStorage;
  const otherStorage: TokenStorage = rememberLogin ? window.sessionStorage : window.localStorage;

  otherStorage.removeItem(AUTH_TOKEN_KEY);
  targetStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function replaceStoredAuthToken(token: string): void {
  if (window.localStorage.getItem(AUTH_TOKEN_KEY)) {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    return;
  }

  window.sessionStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearStoredAuthToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.sessionStorage.removeItem(AUTH_TOKEN_KEY);
}
