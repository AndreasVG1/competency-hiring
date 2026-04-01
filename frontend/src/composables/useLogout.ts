import { ref } from "vue";
import { useRouter } from "vue-router";

import { authClient } from "../api";
import { useAuthStore } from "../stores/auth";

export function useLogout() {
  const router = useRouter();
  const authStore = useAuthStore();

  const isLoggingOut = ref(false);
  const logoutError = ref<string | null>(null);

  async function logout(): Promise<void> {
    if (isLoggingOut.value) {
      return;
    }

    isLoggingOut.value = true;
    logoutError.value = null;

    try {
      await authClient.logout();
    } catch {
      logoutError.value = "Logout request failed. You were signed out locally.";
    } finally {
      authStore.clearSession();
      await router.replace("/auth/login");
      isLoggingOut.value = false;
    }
  }

  return {
    isLoggingOut,
    logoutError,
    logout,
  };
}
