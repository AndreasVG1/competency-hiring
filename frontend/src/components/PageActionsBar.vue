<template>
  <nav class="page-actions">
    <slot />
    <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
  </nav>
  <ApiErrorNotice v-if="logoutError" :error="logoutError" />

</template>

<script setup lang="ts">
import { useLogout } from "../composables/useLogout";
import ApiErrorNotice from "./ApiErrorNotice.vue";

const { isLoggingOut, logoutError, logout } = useLogout();
</script>