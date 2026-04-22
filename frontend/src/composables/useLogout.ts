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
      title: "Logi välja",
      message: "Logi välja? Töötosija või tööandja funktsionaalsustele ligi pääsemiseks pead uuesti sisse logima.",
      confirmLabel: "Logi välja",
      cancelLabel: "Tagasi",
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
