import { defineStore } from "pinia";

import { clearAuthSession, readAuthSession, saveAuthSession } from "./authSessionStorage";
import type { AuthenticatedUser, AuthTokenResponse, UserRole } from "../types/auth";

interface AuthState {
  accessToken: string | null;
  currentUser: AuthenticatedUser | null;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    accessToken: null,
    currentUser: null,
  }),

  getters: {
    isAuthenticated: (state): boolean => Boolean(state.accessToken && state.currentUser),
    role: (state): UserRole | null => state.currentUser?.role ?? null,
  },

  actions: {
    setSession(authResponse: AuthTokenResponse): void {
      this.accessToken = authResponse.access_token;
      this.currentUser = authResponse.user;
      saveAuthSession({
        accessToken: authResponse.access_token,
        currentUser: authResponse.user,
      });
    },

    hydrateSession(payload: { accessToken: string; currentUser: AuthenticatedUser }): void {
      this.accessToken = payload.accessToken;
      this.currentUser = payload.currentUser;
      saveAuthSession(payload);
    },

    restoreFromStorage(): boolean {
      const session = readAuthSession();
      if (!session) {
        return false;
      }
      this.accessToken = session.accessToken;
      this.currentUser = session.currentUser;
      return true;
    },

    setCurrentUser(currentUser: AuthenticatedUser): void {
      this.currentUser = currentUser;
      if (this.accessToken) {
        saveAuthSession({
          accessToken: this.accessToken,
          currentUser,
        });
      }
    },

    clearSession(): void {
      this.accessToken = null;
      this.currentUser = null;
      clearAuthSession();
    },
  },
});
