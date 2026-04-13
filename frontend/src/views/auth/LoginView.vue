<template>
  <section class="d-grid gap-3">
    <header>
      <h2 class="h4 mb-1">Logi sisse</h2>
      <p class="text-body-secondary mb-0">Logi sisse, et näha oma profiili</p>
    </header>

    <form @submit.prevent="submitLogin">
      <div class="mb-3">
        <label class="form-label" for="login-email">E-post</label>
        <input
          id="login-email"
          v-model="email"
          class="form-control"
          type="email"
          autocomplete="email"
          required
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="login-password">Parool</label>
        <input
          id="login-password"
          v-model="password"
          class="form-control"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>

      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>

      <button class="btn btn-primary w-100" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Sisselogimine..." : "Logi sisse" }}
      </button>
    </form>

    <RouterLink class="link-primary" to="/auth/register">Loo konto</RouterLink>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { authClient, ApiClientError } from "../../api";
import { useAuthStore } from "../../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const errorMessage = ref<string | null>(null);
const isSubmitting = ref(false);

function routeByRole(role: "job_seeker" | "recruiter"): string {
  return role === "recruiter" ? "/recruiter" : "/seeker";
}

async function submitLogin(): Promise<void> {
  if (isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  errorMessage.value = null;

  try {
    const response = await authClient.login({
      email: email.value,
      password: password.value,
    });
    authStore.setSession(response);
    await router.replace(routeByRole(response.user.role));
  } catch (error) {
    if (error instanceof ApiClientError) {
      errorMessage.value =
        error.payload.details[0]?.message ?? "Sisselogimine ebaõnnestus, kontrollige, et sisestasite õiged andmed.";
    } else {
      errorMessage.value = "Sisselogimisel tekkis ootamatu viga.";
      console.error("Login error:", error);
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>
