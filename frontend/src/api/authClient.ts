import { apiRequest } from "./httpClient";
import type {
  AuthenticatedUser,
  AuthTokenResponse,
  LoginRequest,
  RefreshTokenRequest,
  RegisterRequest,
} from "../types/auth";

const AUTH_BASE_PATH = "/api/v1/auth";
const CSRF_COOKIE_NAME = "competency_hiring_csrf_token";

function readCookieValue(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = document.cookie.match(new RegExp(`(?:^|; )${escapedName}=([^;]*)`));
  if (!match) {
    return null;
  }
  return decodeURIComponent(match[1]);
}

function readCsrfToken(): string | null {
  return readCookieValue(CSRF_COOKIE_NAME);
}

export const authClient = {
  register(payload: RegisterRequest): Promise<AuthTokenResponse> {
    return apiRequest<AuthTokenResponse>(`${AUTH_BASE_PATH}/register`, {
      method: "POST",
      body: payload,
      auth: false,
      credentials: "include",
    });
  },

  login(payload: LoginRequest): Promise<AuthTokenResponse> {
    return apiRequest<AuthTokenResponse>(`${AUTH_BASE_PATH}/login`, {
      method: "POST",
      body: payload,
      auth: false,
      credentials: "include",
    });
  },

  refresh(payload?: RefreshTokenRequest): Promise<AuthTokenResponse> {
    const csrfToken = readCsrfToken();
    return apiRequest<AuthTokenResponse>(`${AUTH_BASE_PATH}/refresh`, {
      method: "POST",
      body: payload,
      auth: false,
      credentials: "include",
      headers: csrfToken ? { "x-csrf-token": csrfToken } : {},
    });
  },

  logout(payload?: RefreshTokenRequest): Promise<void> {
    const csrfToken = readCsrfToken();
    return apiRequest<void>(`${AUTH_BASE_PATH}/logout`, {
      method: "POST",
      body: payload,
      auth: false,
      credentials: "include",
      headers: csrfToken ? { "x-csrf-token": csrfToken } : {},
    });
  },

  me(): Promise<AuthenticatedUser> {
    return apiRequest<AuthenticatedUser>(`${AUTH_BASE_PATH}/me`);
  },
};
