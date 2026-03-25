import { defineStore } from "pinia";

import { clearAuthSession, saveAuthSession } from "./authSessionStorage";
import type { AuthenticatedUser, AuthTokenResponse, UserRole } from "../types/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  currentUser: AuthenticatedUser | null;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    accessToken: null,
    refreshToken: null,
    currentUser: null,
  }),

  getters: {
    isAuthenticated: (state): boolean => Boolean(state.accessToken && state.currentUser),
    role: (state): UserRole | null => state.currentUser?.role ?? null,
  },

  actions: {
    setSession(authResponse: AuthTokenResponse): void {
      this.accessToken = authResponse.access_token;
      this.refreshToken = authResponse.refresh_token;
      this.currentUser = authResponse.user;
      saveAuthSession({
        accessToken: authResponse.access_token,
        refreshToken: authResponse.refresh_token,
        currentUser: authResponse.user,
      });
    },

    clearSession(): void {
      this.accessToken = null;
      this.refreshToken = null;
      this.currentUser = null;
      clearAuthSession();
    },
  },
});

