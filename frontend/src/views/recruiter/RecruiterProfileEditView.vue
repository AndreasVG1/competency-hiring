<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/recruiter">Back to recruiter</RouterLink>
        <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Edit Recruiter Profile</h1>
        <p class="content">Update company and contact information.</p>
      </header>

      <ApiErrorNotice v-if="logoutError" :error="logoutError" />

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Recruiter Profile</h2>
          <p>Profile details are saved separately from job offers.</p>
        </header>

        <p v-if="isFirstTimeProfile" class="section-note">
          No recruiter profile found yet. Fill in details and save to create one.
        </p>

        <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

        <form class="recruiter-form" @submit.prevent="saveProfile">
          <label class="form-field">
            <span>Company name</span>
            <input
              v-model="profileForm.companyName"
              type="text"
              maxlength="255"
              required
              :disabled="isProfileLoading || isProfileSaving"
            />
          </label>

          <label class="form-field">
            <span>Contact name</span>
            <input
              v-model="profileForm.contactName"
              type="text"
              maxlength="255"
              required
              :disabled="isProfileLoading || isProfileSaving"
            />
          </label>

          <ApiErrorNotice v-if="profileSaveError" :error="profileSaveError" show-all-messages />
          <p v-if="profileSaveSuccessMessage" class="form-success">{{ profileSaveSuccessMessage }}</p>

          <button class="button-primary" type="submit" :disabled="isProfileLoading || isProfileSaving">
            {{ isProfileSaving ? "Saving profile..." : "Save profile" }}
          </button>
        </form>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useLogout } from "../../composables/useLogout";
import type { RecruiterProfileResponse } from "../../types/domain";

interface RecruiterProfileFormState {
  companyName: string;
  contactName: string;
}

const { isLoggingOut, logoutError, logout } = useLogout();

const profileForm = reactive<RecruiterProfileFormState>({
  companyName: "",
  contactName: "",
});

const isFirstTimeProfile = ref(false);
const isProfileLoading = ref(true);
const isProfileSaving = ref(false);
const profileLoadError = ref<unknown | null>(null);
const profileSaveError = ref<unknown | null>(null);
const profileSaveSuccessMessage = ref<string | null>(null);

function hydrateProfileForm(profile: RecruiterProfileResponse): void {
  profileForm.companyName = profile.company_name;
  profileForm.contactName = profile.contact_name;
}

async function loadProfile(): Promise<void> {
  isProfileLoading.value = true;
  isFirstTimeProfile.value = false;
  profileLoadError.value = null;

  try {
    const profile = await recruiterClient.getProfile();
    hydrateProfileForm(profile);
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isFirstTimeProfile.value = true;
      return;
    }

    profileLoadError.value = error;
  } finally {
    isProfileLoading.value = false;
  }
}

async function saveProfile(): Promise<void> {
  if (isProfileLoading.value || isProfileSaving.value) {
    return;
  }

  isProfileSaving.value = true;
  profileSaveError.value = null;
  profileSaveSuccessMessage.value = null;

  try {
    const profile = await recruiterClient.upsertProfile({
      company_name: profileForm.companyName.trim(),
      contact_name: profileForm.contactName.trim(),
    });

    hydrateProfileForm(profile);
    isFirstTimeProfile.value = false;
    profileSaveSuccessMessage.value = "Recruiter profile saved.";
  } catch (error) {
    profileSaveError.value = error;
  } finally {
    isProfileSaving.value = false;
  }
}

onMounted(async () => {
  await loadProfile();
});
</script>
