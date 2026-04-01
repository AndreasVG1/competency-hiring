<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/recruiter/edit">Edit profile</RouterLink>
        <RouterLink class="button-primary" to="/recruiter/job-offers/new">Create job offer</RouterLink>
        <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
      </PageActionsBar>

      <header class="panel-header">
        <h1>Recruiter Overview</h1>
        <p class="content">Review your profile information and draft job offers.</p>
      </header>

      <ApiErrorNotice v-if="logoutError" :error="logoutError" />

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Recruiter Profile</h2>
        </header>

        <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

        <p v-if="isProfileLoading" class="section-note">Loading profile...</p>
        <template v-else-if="isFirstTimeProfile || !profile">
          <p class="section-note">No recruiter profile found yet.</p>
          <RouterLink class="button-primary" to="/recruiter/edit">Create profile</RouterLink>
        </template>

        <dl v-else class="summary-grid">
          <dt>Company name</dt>
          <dd>{{ profile.company_name }}</dd>
          <dt>Contact name</dt>
          <dd>{{ profile.contact_name }}</dd>
        </dl>
      </section>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Job Offers</h2>
          <p>Open an offer to review details, status, and available actions.</p>
        </header>

        <ApiErrorNotice v-if="jobOffersLoadError" :error="jobOffersLoadError" show-all-messages />

        <p v-if="isJobOffersLoading" class="table-note">Loading job offers...</p>
        <p v-else-if="jobOffers.length === 0" class="table-note">No draft offers yet.</p>

        <ul v-else class="offer-list">
          <li v-for="offer in jobOffers" :key="offer.id">
            <RouterLink class="offer-select" :to="`/recruiter/job-offers/${offer.id}`">
              <span>
                <strong>{{ offer.title }}</strong>
                <JobOfferStatusBadge :status="offer.status" />
              </span>
              <code>#{{ offer.id }}</code>
            </RouterLink>
          </li>
        </ul>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useLogout } from "../../composables/useLogout";
import type { JobOfferResponse, RecruiterProfileResponse } from "../../types/domain";

const { isLoggingOut, logoutError, logout } = useLogout();

const profile = ref<RecruiterProfileResponse | null>(null);
const isFirstTimeProfile = ref(false);
const isProfileLoading = ref(true);
const profileLoadError = ref<unknown | null>(null);

const jobOffers = ref<JobOfferResponse[]>([]);
const isJobOffersLoading = ref(true);
const jobOffersLoadError = ref<unknown | null>(null);

function sortOffersDescending(offers: JobOfferResponse[]): JobOfferResponse[] {
  return [...offers].sort((a, b) => {
    const timeDelta = Date.parse(b.created_at) - Date.parse(a.created_at);
    if (timeDelta !== 0) {
      return timeDelta;
    }
    return b.id - a.id;
  });
}

async function loadProfile(): Promise<void> {
  isProfileLoading.value = true;
  isFirstTimeProfile.value = false;
  profileLoadError.value = null;

  try {
    profile.value = await recruiterClient.getProfile();
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isFirstTimeProfile.value = true;
      profile.value = null;
      return;
    }

    profileLoadError.value = error;
  } finally {
    isProfileLoading.value = false;
  }
}

async function loadJobOffers(): Promise<void> {
  isJobOffersLoading.value = true;
  jobOffersLoadError.value = null;

  try {
    const offers = await recruiterClient.listJobOffers();
    jobOffers.value = sortOffersDescending(offers);
  } catch (error) {
    jobOffersLoadError.value = error;
  } finally {
    isJobOffersLoading.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadProfile(), loadJobOffers()]);
});
</script>
