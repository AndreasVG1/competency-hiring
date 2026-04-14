<template>
  <div class="d-grid gap-4">
    <PageActionsBar />

    <header>
      <h1 class="h3 mb-1">Konto andmed</h1>
      <p class="text-body-secondary mb-0">Halda oma konto turvaseadeid.</p>
    </header>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Parooli muutmine</h2>
        <p class="text-body-secondary mb-0">E-posti aadressi muuta ei saa.</p>
      </header>

      <div>
        <label class="form-label" for="account-email">E-post</label>
        <input id="account-email" class="form-control" type="email" :value="email" readonly disabled />
      </div>

      <form class="d-grid gap-3" @submit.prevent="submitPasswordChange">
        <div>
          <label class="form-label" for="old-password">Vana parool</label>
          <input
            id="old-password"
            v-model="form.oldPassword"
            class="form-control"
            type="password"
            autocomplete="current-password"
            required
            :disabled="isSubmittingPasswordChange || isDeletingAccount"
          />
        </div>

        <div>
          <label class="form-label" for="new-password">Uus parool</label>
          <input
            id="new-password"
            v-model="form.newPassword"
            class="form-control"
            type="password"
            autocomplete="new-password"
            required
            :disabled="isSubmittingPasswordChange || isDeletingAccount"
          />
        </div>

        <div>
          <label class="form-label" for="confirm-new-password">Kinnita uus parool</label>
          <input
            id="confirm-new-password"
            v-model="form.confirmNewPassword"
            class="form-control"
            type="password"
            autocomplete="new-password"
            required
            :disabled="isSubmittingPasswordChange || isDeletingAccount"
          />
        </div>

        <ApiErrorNotice v-if="passwordChangeError" :error="passwordChangeError" show-all-messages />
        <ApiErrorNotice v-if="deleteAccountError" :error="deleteAccountError" show-all-messages />

        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-primary" type="submit" :disabled="isSubmittingPasswordChange || isDeletingAccount">
            {{ isSubmittingPasswordChange ? "Parooli muutmine..." : "Muuda parooli" }}
          </button>
          <button
            class="btn btn-outline-danger"
            type="button"
            :disabled="isSubmittingPasswordChange || isDeletingAccount"
            @click="submitAccountDelete"
          >
            {{ isDeletingAccount ? "Konto kustutamine..." : "Kustuta konto" }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { authClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useConfirmDialog } from "../../composables/useConfirmDialog";
import { useAuthStore } from "../../stores/auth";

interface PasswordFormState {
  oldPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}

const router = useRouter();
const authStore = useAuthStore();
const { confirm } = useConfirmDialog();

const form = reactive<PasswordFormState>({
  oldPassword: "",
  newPassword: "",
  confirmNewPassword: "",
});

const isSubmittingPasswordChange = ref(false);
const isDeletingAccount = ref(false);
const passwordChangeError = ref<unknown | null>(null);
const deleteAccountError = ref<unknown | null>(null);

const email = computed(() => authStore.currentUser?.email ?? "");

async function clearSessionAndRedirectToLogin(): Promise<void> {
  authStore.clearSession();
  await router.replace("/auth/login");
}

async function submitPasswordChange(): Promise<void> {
  if (isSubmittingPasswordChange.value || isDeletingAccount.value) {
    return;
  }

  const confirmed = await confirm({
    title: "Muuda parooli",
    message: "Kas soovite parooli muuta? Pärast muudatust tuleb uuesti sisse logida.",
    confirmLabel: "Muuda parooli",
    cancelLabel: "Tühista",
    tone: "primary",
  });
  if (!confirmed) {
    return;
  }

  isSubmittingPasswordChange.value = true;
  passwordChangeError.value = null;

  try {
    await authClient.changePassword({
      old_password: form.oldPassword,
      new_password: form.newPassword,
      confirm_new_password: form.confirmNewPassword,
    });
    await clearSessionAndRedirectToLogin();
  } catch (error) {
    passwordChangeError.value = error;
  } finally {
    isSubmittingPasswordChange.value = false;
  }
}

async function submitAccountDelete(): Promise<void> {
  if (isSubmittingPasswordChange.value || isDeletingAccount.value) {
    return;
  }

  const confirmed = await confirm({
    title: "Kustuta konto",
    message: "Kas soovite konto jäädavalt kustutada? Seda tegevust ei saa tagasi võtta.",
    confirmLabel: "Kustuta konto",
    cancelLabel: "Tühista",
    tone: "danger",
  });
  if (!confirmed) {
    return;
  }

  isDeletingAccount.value = true;
  deleteAccountError.value = null;

  try {
    await authClient.deleteAccount({ current_password: form.oldPassword });
    await clearSessionAndRedirectToLogin();
  } catch (error) {
    deleteAccountError.value = error;
  } finally {
    isDeletingAccount.value = false;
  }
}
</script>
