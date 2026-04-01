<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" :to="backToOfferPath">Back to offer</RouterLink>
        <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Offer Applicants</h1>
        <p class="content">
          Applicants appear only after explicit seeker consent through application.
        </p>
      </header>

      <ApiErrorNotice v-if="logoutError" :error="logoutError" />

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Offer</h2>
          <p>Applicant data below is shared as an application-time snapshot.</p>
        </header>

        <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />

        <p v-if="isOfferLoading" class="section-note">Loading offer...</p>
        <p v-else-if="isOfferNotFound" class="section-note">Job offer not found.</p>
        <template v-else-if="jobOffer">
          <dl class="summary-grid">
            <dt>Title</dt>
            <dd>{{ jobOffer.title }}</dd>
            <dt>Status</dt>
            <dd><JobOfferStatusBadge :status="jobOffer.status" /></dd>
            <dt>Occupation key</dt>
            <dd>{{ jobOffer.occupation_key }}</dd>
          </dl>
        </template>
      </section>

      <section v-if="!isOfferNotFound" class="recruiter-section">
        <header class="section-header">
          <h2>Applicants</h2>
          <p>Only candidates who applied to this offer are visible.</p>
        </header>

        <ApiErrorNotice v-if="applicantsLoadError" :error="applicantsLoadError" show-all-messages />

        <p v-if="isApplicantsLoading" class="section-note">Loading applicants...</p>
        <p v-else-if="applicants.length === 0" class="section-note">No applicants yet.</p>
        <ul v-else class="applicants-list">
          <li v-for="applicant in applicants" :key="applicant.application_id" class="applicant-card">
            <header class="section-header">
              <h3>{{ applicant.shared_profile.full_name }}</h3>
              <p class="snapshot-note">
                Shared at application time on {{ formatDateTime(applicant.snapshot_created_at) }}.
              </p>
            </header>

            <dl class="summary-grid">
              <dt>Applied at</dt>
              <dd>{{ formatDateTime(applicant.applied_at) }}</dd>
              <dt>Consent given at</dt>
              <dd>{{ formatDateTime(applicant.consent_given_at) }}</dd>
              <dt>Location</dt>
              <dd>{{ applicant.shared_profile.location || "Not provided" }}</dd>
              <dt>Occupation key</dt>
              <dd>{{ applicant.shared_profile.occupation_key || "Not provided" }}</dd>
              <dt>Summary</dt>
              <dd>{{ applicant.shared_profile.summary || "Not provided" }}</dd>
            </dl>

            <section>
              <header class="subsection-header">
                <h3>Shared competencies</h3>
                <p>Competency values shown here come from the stored application snapshot.</p>
              </header>

              <p v-if="applicant.shared_profile.competencies.length === 0" class="section-note">
                No competencies were shared.
              </p>
              <table v-else class="competency-table">
                <thead>
                  <tr>
                    <th>Competency</th>
                    <th>Level</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(competency, competencyIndex) in applicant.shared_profile.competencies"
                    :key="`${applicant.application_id}-${competency.competency_key}-${competencyIndex}`"
                  >
                    <td>{{ competencyLabel(competency.competency_key) }}</td>
                    <td>{{ competency.level }}</td>
                  </tr>
                </tbody>
              </table>
            </section>
          </li>
        </ul>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useLogout } from "../../composables/useLogout";
import type { JobOfferResponse, RecruiterApplicantListItem } from "../../types/domain";

const route = useRoute();
const { isLoggingOut, logoutError, logout } = useLogout();
const labelCache = useCatalogLabelCache();

const jobOffer = ref<JobOfferResponse | null>(null);
const applicants = ref<RecruiterApplicantListItem[]>([]);

const isOfferLoading = ref(true);
const isApplicantsLoading = ref(false);
const isOfferNotFound = ref(false);

const offerLoadError = ref<unknown | null>(null);
const applicantsLoadError = ref<unknown | null>(null);

const backToOfferPath = computed(() => {
  const offerId = parseOfferId();
  if (offerId === null) {
    return "/recruiter";
  }
  return `/recruiter/job-offers/${offerId}`;
});

function parseOfferId(): number | null {
  const offerId = Number(route.params.id);
  if (!Number.isInteger(offerId) || offerId <= 0) {
    return null;
  }
  return offerId;
}

function competencyLabel(competencyKey: string): string {
  const label = labelCache.getLabel(competencyKey);
  if (label) {
    return label;
  }

  const state = labelCache.getLabelState(competencyKey);
  if (state === "error") {
    return "Label unavailable";
  }

  return competencyKey;
}

function formatDateTime(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(parsed));
}

async function loadApplicants(): Promise<void> {
  const offerId = parseOfferId();
  if (offerId === null) {
    isOfferNotFound.value = true;
    offerLoadError.value = "Invalid job offer id.";
    isOfferLoading.value = false;
    return;
  }

  isOfferLoading.value = true;
  isApplicantsLoading.value = false;
  isOfferNotFound.value = false;
  offerLoadError.value = null;
  applicantsLoadError.value = null;
  jobOffer.value = null;
  applicants.value = [];

  try {
    jobOffer.value = await recruiterClient.getJobOffer(offerId);
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isOfferNotFound.value = true;
      return;
    }
    offerLoadError.value = error;
    return;
  } finally {
    isOfferLoading.value = false;
  }

  isApplicantsLoading.value = true;
  try {
    const loadedApplicants = await recruiterClient.listApplicants(offerId);
    applicants.value = loadedApplicants;
    const competencyKeys = loadedApplicants.flatMap((item) =>
      item.shared_profile.competencies.map((competency) => competency.competency_key),
    );
    void labelCache.hydrateKeys(competencyKeys);
  } catch (error) {
    applicantsLoadError.value = error;
  } finally {
    isApplicantsLoading.value = false;
  }
}

onMounted(async () => {
  await loadApplicants();
});
</script>
