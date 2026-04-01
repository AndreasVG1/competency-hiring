<template>
  <section class="content">
    <h2>Create Account</h2>
    <p>Choose your role and create your account.</p>

    <form class="auth-form" @submit.prevent="submitRegistration">
      <label class="form-field">
        <span>Email</span>
        <input v-model="email" type="email" autocomplete="email" required />
      </label>

      <label class="form-field">
        <span>Password</span>
        <input v-model="password" type="password" autocomplete="new-password" required />
      </label>

      <label class="form-field">
        <span>Confirm Password</span>
        <input v-model="confirmPassword" type="password" autocomplete="new-password" required />
      </label>

      <fieldset class="role-fieldset">
        <legend>Register as</legend>
        <label class="radio-option">
          <input v-model="role" type="radio" value="job_seeker" />
          <span>Job seeker</span>
        </label>
        <label class="radio-option">
          <input v-model="role" type="radio" value="recruiter" />
          <span>Recruiter</span>
        </label>
      </fieldset>

      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

      <button class="button-primary" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Creating account..." : "Create account" }}
      </button>
    </form>

    <RouterLink class="inline-link" to="/auth/login">Already have an account? Sign in</RouterLink>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { authClient, ApiClientError } from "../../api";
import { useAuthStore } from "../../stores/auth";
import type { UserRole } from "../../types/auth";

const router = useRouter();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const role = ref<UserRole>("job_seeker");
const errorMessage = ref<string | null>(null);
const isSubmitting = ref(false);

function routeByRole(userRole: UserRole): string {
  return userRole === "recruiter" ? "/recruiter" : "/seeker";
}

async function submitRegistration(): Promise<void> {
  if (isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  errorMessage.value = null;

  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Passwords do not match.";
    isSubmitting.value = false;
    return;
  }

  try {
    const response = await authClient.register({
      email: email.value,
      password: password.value,
      role: role.value,
    });
    authStore.setSession(response);
    await router.replace(routeByRole(response.user.role));
  } catch (error) {
    if (error instanceof ApiClientError) {
      errorMessage.value =
        error.payload.details[0]?.message ?? "Unable to create account.";
    } else {
      errorMessage.value = "Unexpected error while creating account.";
      console.error("Registration error:", error);
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>
