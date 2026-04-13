<template>
  <section class="d-grid gap-3">
    <header>
      <h2 class="h4 mb-1">Loo konto</h2>
      <p class="text-body-secondary mb-0">Vali oma roll ja loo konto</p>
    </header>

    <form @submit.prevent="submitRegistration">
      <div class="mb-3">
        <label class="form-label" for="register-email">E-post</label>
        <input
          id="register-email"
          v-model="email"
          class="form-control"
          type="email"
          autocomplete="email"
          required
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="register-password">Parool</label>
        <input
          id="register-password"
          v-model="password"
          class="form-control"
          type="password"
          autocomplete="new-password"
          required
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="register-password-confirm">Kinnita parool</label>
        <input
          id="register-password-confirm"
          v-model="confirmPassword"
          class="form-control"
          type="password"
          autocomplete="new-password"
          required
        />
      </div>

      <fieldset class="border rounded-3 p-3 mb-3">
        <legend class="float-none w-auto px-2 fs-6 mb-0">Registreeru kui</legend>
        <div class="form-check">
          <input id="role-seeker" v-model="role" class="form-check-input" type="radio" value="job_seeker" />
          <label class="form-check-label" for="role-seeker">Tööotsija</label>
        </div>
        <div class="form-check">
          <input id="role-recruiter" v-model="role" class="form-check-input" type="radio" value="recruiter" />
          <label class="form-check-label" for="role-recruiter">Tööandja</label>
        </div>
      </fieldset>

      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>

      <button class="btn btn-primary w-100" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? "Konto loomine..." : "Loo konto" }}
      </button>
    </form>

    <RouterLink class="link-primary" to="/auth/login">Sul on juba konto? Logi sisse</RouterLink>
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
    errorMessage.value = "Paroolid ei ühti.";
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
        error.payload.details[0]?.message ?? "Konto loomine ebaõnnestus.";
    } else {
      errorMessage.value = "Konto loomisel tekkis ootamatu viga.";
      console.error("Registration error:", error);
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>
