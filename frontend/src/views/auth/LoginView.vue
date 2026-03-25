<template>
  <section class="content">
    <h2>Login</h2>
    <p>Sign in to continue to your dashboard.</p>

    <form class="auth-form" @submit.prevent="submitLogin">
      <label class="form-field">
        <span>Email</span>
        <input v-model="email" type="email" autocomplete="email" required />
      </label>

      <label class="form-field">
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>

      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

      <button class="button-primary" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Signing in..." : "Sign in" }}
      </button>
    </form>

    <RouterLink class="inline-link" to="/auth/register">Create an account</RouterLink>
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
        error.payload.details[0]?.message ?? "Unable to sign in with provided credentials.";
    } else {
      errorMessage.value = "Unexpected error while signing in.";
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>
