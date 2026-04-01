import { ref } from "vue";
import { useRouter } from "vue-router";

import { authClient } from "../api";
import { useAuthStore } from "../stores/auth";
import { useConfirmDialog } from "./useConfirmDialog";

export function useLogout() {
  const router = useRouter();
  const authStore = useAuthStore();
  const { confirm } = useConfirmDialog();

  const isLoggingOut = ref(false);
  const logoutError = ref<string | null>(null);

  async function logout(): Promise<void> {
    if (isLoggingOut.value) {
      return;
    }

    const confirmed = await confirm({
      title: "Log out",
      message: "Log out now? You will need to sign in again to access seeker or recruiter features.",
      confirmLabel: "Log out",
      cancelLabel: "Stay signed in",
      tone: "danger",
    });
    if (!confirmed) {
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
