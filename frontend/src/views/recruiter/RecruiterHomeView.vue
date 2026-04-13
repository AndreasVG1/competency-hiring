<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/recruiter/edit">Muuda profiili</RouterLink>
      <RouterLink class="btn btn-primary" to="/recruiter/job-offers/new">Koosta tööpakkumine</RouterLink>
    </PageActionsBar>

    <header>
      <h1 class="h3 mb-1">Tööandja Ülevaade</h1>
      <p class="text-body-secondary mb-0">Vaata oma profiili teavet ja koosta tööpakkumisi.</p>
    </header>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-0">Tööandja profiil</h2>
      </header>

      <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

      <p v-if="isProfileLoading" class="text-body-secondary mb-0">Laen profiili...</p>
      <template v-else-if="isFirstTimeProfile || !profile">
        <p class="text-body-secondary mb-0">Tööandja profiili ei leitud.</p>
        <div>
          <RouterLink class="btn btn-primary" to="/recruiter/edit">Loo profiil</RouterLink>
        </div>
      </template>

      <dl v-else class="row mb-0">
        <dt class="col-sm-3 text-body-secondary">Ettevõtte nimi</dt>
        <dd class="col-sm-9 text-break">{{ profile.company_name }}</dd>
        <dt class="col-sm-3 text-body-secondary">Kontaktisik</dt>
        <dd class="col-sm-9 text-break">{{ profile.contact_name }}</dd>
      </dl>
    </section>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Tööpakkumised</h2>
        <p class="text-body-secondary mb-0">Ava tööpakkumine, et vaadata üksikasju, staatust ja saadaolevaid toiminguid.</p>
      </header>

      <ApiErrorNotice v-if="jobOffersLoadError" :error="jobOffersLoadError" show-all-messages />

      <p v-if="isJobOffersLoading" class="text-body-secondary mb-0">Laen tööpakkumisi...</p>
      <p v-else-if="jobOffers.length === 0" class="text-body-secondary mb-0">Tööpakkumisi ei leitud.</p>

      <ul v-else class="list-group">
        <li v-for="offer in jobOffers" :key="offer.id" class="list-group-item">
          <RouterLink class="text-decoration-none text-reset d-block" :to="`/recruiter/job-offers/${offer.id}`">
            <div class="d-flex justify-content-between align-items-start gap-3">
              <div class="min-w-0">
                <div class="d-flex flex-wrap gap-2 align-items-center">
                  <strong class="text-break">{{ offer.title }}</strong>
                  <JobOfferStatusBadge :status="offer.status" />
                </div>
              </div>
              <code class="text-body-secondary">#{{ offer.id }}</code>
            </div>
          </RouterLink>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import type { JobOfferResponse, RecruiterProfileResponse } from "../../types/domain";

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
