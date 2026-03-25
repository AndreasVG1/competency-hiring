import { authClient, ApiClientError } from "../api";
import type { AuthenticatedUser } from "../types/auth";
import type { useAuthStore } from "../stores/auth";

type AuthStore = ReturnType<typeof useAuthStore>;

async function loadCurrentUser(): Promise<AuthenticatedUser> {
  return authClient.me();
}

export async function bootstrapAuthSession(authStore: AuthStore): Promise<void> {
  const hadStoredSession = authStore.restoreFromStorage();
  if (!hadStoredSession) {
    return;
  }

  try {
    const currentUser = await loadCurrentUser();
    authStore.setCurrentUser(currentUser);
    return;
  } catch (error) {
    if (!(error instanceof ApiClientError) || error.statusCode !== 401) {
      authStore.clearSession();
      return;
    }
  }

  try {
    const refreshedSession = await authClient.refresh();
    authStore.setSession(refreshedSession);
    const currentUser = await loadCurrentUser();
    authStore.setCurrentUser(currentUser);
  } catch {
    authStore.clearSession();
  }
}
