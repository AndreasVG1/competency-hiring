<template>
  <main class="seeker-page">
    <section class="panel seeker-panel">
      <nav class="page-actions">
        <RouterLink class="button-secondary" to="/seeker/job-offers">Back to marketplace</RouterLink>
        <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
      </nav>

      <header class="panel-header">
        <p class="eyebrow">Seeker Marketplace</p>
        <h1>Job Offer Detail</h1>
        <p class="content">Review published information before deciding whether to apply.</p>
      </header>

      <ApiErrorNotice v-if="logoutError" :error="logoutError" />
      <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />

      <section class="seeker-section">
        <header class="section-header">
          <h2>Offer</h2>
        </header>

        <p v-if="isOfferLoading" class="section-note">Loading offer...</p>
        <template v-else-if="isOfferNotFound">
          <p class="section-note">Published job offer not found.</p>
          <RouterLink class="button-secondary" to="/seeker/job-offers">Back to published offers</RouterLink>
        </template>
        <template v-else-if="offer">
          <div class="marketplace-offer-header">
            <h3>{{ offer.title }}</h3>
            <JobOfferStatusBadge status="published" />
          </div>
          <dl class="summary-grid">
            <dt>Company</dt>
            <dd>{{ offer.company_name || "Company not provided" }}</dd>
            <dt>Occupation</dt>
            <dd>{{ offer.occupation_label }}</dd>
            <dt>Published</dt>
            <dd>{{ formatDateTime(offer.published_at) }}</dd>
            <dt>Description</dt>
            <dd>{{ offer.description }}</dd>
          </dl>
        </template>
      </section>

      <section v-if="offer && !isOfferNotFound" class="seeker-section">
        <header class="section-header">
          <h2>Requirements</h2>
          <p>Requirements are listed exactly as published by the recruiter.</p>
        </header>

        <JobOfferRequirementsTable :requirements="offer.requirements" :label-resolver="competencyLabel" />
      </section>

      <section v-if="offer && !isOfferNotFound" class="seeker-section">
        <header class="section-header">
          <h2>Apply</h2>
          <p>
            Applying with explicit consent will be enabled in Phase 2B.
          </p>
        </header>
        <div class="table-actions">
          <button class="button-primary" type="button" disabled>Apply (available in Phase 2B)</button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { ApiClientError, seekerClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferRequirementsTable from "../../components/JobOfferRequirementsTable.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useLogout } from "../../composables/useLogout";
import type { PublicJobOfferDetail } from "../../types/domain";

const route = useRoute();
const labelCache = useCatalogLabelCache();
const { isLoggingOut, logoutError, logout } = useLogout();

const offer = ref<PublicJobOfferDetail | null>(null);
const isOfferLoading = ref(true);
const isOfferNotFound = ref(false);
const offerLoadError = ref<unknown | null>(null);

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

  return "Loading label...";
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

async function loadOffer(): Promise<void> {
  const offerId = parseOfferId();
  if (offerId === null) {
    isOfferNotFound.value = true;
    isOfferLoading.value = false;
    offerLoadError.value = "Invalid job offer id.";
    return;
  }

  isOfferLoading.value = true;
  isOfferNotFound.value = false;
  offerLoadError.value = null;
  offer.value = null;

  try {
    const loadedOffer = await seekerClient.getPublishedJobOffer(offerId);
    offer.value = loadedOffer;
    void labelCache.hydrateKeys(loadedOffer.requirements.map((item) => item.competency_key));
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isOfferNotFound.value = true;
      return;
    }
    offerLoadError.value = error;
  } finally {
    isOfferLoading.value = false;
  }
}

onMounted(async () => {
  await loadOffer();
});
</script>
