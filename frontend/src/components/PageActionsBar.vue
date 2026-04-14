<template>
  <nav class="d-flex flex-wrap justify-content-end gap-2">
    <slot />
    <RouterLink class="btn btn-outline-secondary" :to="accountRoutePath">Konto andmed</RouterLink>
    <button class="btn btn-outline-danger" type="button" :disabled="isLoggingOut" @click="logout">
      {{ isLoggingOut ? "Logib välja..." : "Logi välja" }}
    </button>
  </nav>
  <ApiErrorNotice v-if="logoutError" :error="logoutError" />
</template>

<script setup lang="ts">
import { computed } from "vue";

import { useLogout } from "../composables/useLogout";
import { useAuthStore } from "../stores/auth";
import ApiErrorNotice from "./ApiErrorNotice.vue";

const authStore = useAuthStore();
const { isLoggingOut, logoutError, logout } = useLogout();

const accountRoutePath = computed(() => {
  if (authStore.role === "recruiter") {
    return "/recruiter/account";
  }
  return "/seeker/account";
});
</script>
