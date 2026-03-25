import { apiRequest } from "./httpClient";
import type {
  AuthenticatedUser,
  AuthTokenResponse,
  LoginRequest,
  RefreshTokenRequest,
  RegisterRequest,
} from "../types/auth";

const AUTH_BASE_PATH = "/api/v1/auth";

export const authClient = {
  register(payload: RegisterRequest): Promise<AuthTokenResponse> {
    return apiRequest<AuthTokenResponse>(`${AUTH_BASE_PATH}/register`, {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  login(payload: LoginRequest): Promise<AuthTokenResponse> {
    return apiRequest<AuthTokenResponse>(`${AUTH_BASE_PATH}/login`, {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  refresh(payload: RefreshTokenRequest): Promise<AuthTokenResponse> {
    return apiRequest<AuthTokenResponse>(`${AUTH_BASE_PATH}/refresh`, {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  logout(payload: RefreshTokenRequest): Promise<void> {
    return apiRequest<void>(`${AUTH_BASE_PATH}/logout`, {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  me(): Promise<AuthenticatedUser> {
    return apiRequest<AuthenticatedUser>(`${AUTH_BASE_PATH}/me`);
  },
};

