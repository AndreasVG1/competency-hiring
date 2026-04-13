<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/recruiter">Tagasi avalehele</RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Tööandja vaade</p>
      <h1 class="h3 mb-1">Muuda tööandja profiili</h1>
      <p class="text-body-secondary mb-0">Uuenda ettevõtte ja kontaktandmeid.</p>
    </header>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Tööandja profiil</h2>
        <p class="text-body-secondary mb-0">Profiili andmed salvestatakse eraldi tööpakkumistest.</p>
      </header>

      <p v-if="isFirstTimeProfile" class="text-body-secondary mb-0">
        Profiili ei leitud. Täida andmed ja salvesta, et luua profiil.  
      </p>

      <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

      <form class="d-grid gap-3" @submit.prevent="saveProfile">
        <div>
          <label class="form-label" for="recruiter-company-name">Ettevõtte nimi</label>
          <input
            id="recruiter-company-name"
            v-model="profileForm.companyName"
            class="form-control"
            type="text"
            maxlength="255"
            required
            :disabled="isProfileLoading || isProfileSaving"
          />
        </div>

        <div>
          <label class="form-label" for="recruiter-contact-name">Kontaktisik</label>
          <input
            id="recruiter-contact-name"
            v-model="profileForm.contactName"
            class="form-control"
            type="text"
            maxlength="255"
            required
            :disabled="isProfileLoading || isProfileSaving"
          />
        </div>

        <ApiErrorNotice v-if="profileSaveError" :error="profileSaveError" show-all-messages />
        <div v-if="profileSaveSuccessMessage" class="alert alert-success mb-0" role="status">
          {{ profileSaveSuccessMessage }}
        </div>

        <button class="btn btn-primary" type="submit" :disabled="isProfileLoading || isProfileSaving">
          {{ isProfileSaving ? "Profiil salvestamisel..." : "Salvesta muudatused" }}
        </button>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import type { RecruiterProfileResponse } from "../../types/domain";

interface RecruiterProfileFormState {
  companyName: string;
  contactName: string;
}

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
    profileSaveSuccessMessage.value = "Profiil salvestatud.";
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
