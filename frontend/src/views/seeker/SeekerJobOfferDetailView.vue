<template>
  <main class="seeker-page">
    <section class="panel seeker-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/seeker/job-offers">Back to marketplace</RouterLink>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Seeker Marketplace</p>
        <h1>Job Offer Detail</h1>
        <p class="content">Review published information before deciding whether to apply.</p>
      </header>

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
          <h2>Private analysis</h2>
          <p>
            Run a private analysis to review your current match details. This is decision support only and
            does not make hiring decisions.
          </p>
        </header>
        <ApiErrorNotice v-if="analysisError" :error="analysisError" show-all-messages />
        <div class="table-actions">
          <button
            class="button-secondary"
            type="button"
            :disabled="isAnalysisLoading"
            @click="runPrivateAnalysis"
          >
            {{ analysisButtonLabel }}
          </button>
        </div>
        <JsonPayloadViewer
          title="Current analysis result"
          :payload="analysisResult"
          empty-text="No analysis run yet. Use the button above to fetch your private analysis."
        />
      </section>

      <section v-if="offer && !isOfferNotFound" class="seeker-section">
        <header class="section-header">
          <h2>Apply</h2>
          <p>
            Applying is an explicit consent action. If you apply, your profile snapshot at application time
            is shared with the recruiter for this offer.
          </p>
        </header>
        <ApiErrorNotice v-if="applyError" :error="applyError" show-all-messages />
        <p v-if="applySuccessMessage" class="form-success">{{ applySuccessMessage }}</p>
        <p class="consent-callout">
          Consent note: only data captured at the moment you apply is shared for this application.
        </p>
        <div class="table-actions">
          <button
            class="button-primary"
            type="button"
            :disabled="isApplying || hasApplied"
            @click="applyToOffer"
          >
            {{ applyButtonLabel }}
          </button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { ApiClientError, seekerClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferRequirementsTable from "../../components/JobOfferRequirementsTable.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import JsonPayloadViewer from "../../components/JsonPayloadViewer.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useConfirmDialog } from "../../composables/useConfirmDialog";
import type { PrivateMatchingAnalysisResponse, PublicJobOfferDetail } from "../../types/domain";

const route = useRoute();
const labelCache = useCatalogLabelCache();
const { confirm } = useConfirmDialog();

const offer = ref<PublicJobOfferDetail | null>(null);
const isOfferLoading = ref(true);
const isOfferNotFound = ref(false);
const offerLoadError = ref<unknown | null>(null);
const isApplying = ref(false);
const hasApplied = ref(false);
const applyError = ref<unknown | null>(null);
const applySuccessMessage = ref<string | null>(null);
const analysisResult = ref<PrivateMatchingAnalysisResponse | null>(null);
const analysisError = ref<unknown | null>(null);
const isAnalysisLoading = ref(false);

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

const applyButtonLabel = computed(() => {
  if (isApplying.value) {
    return "Applying...";
  }
  if (hasApplied.value) {
    return "Application sent";
  }
  return "Apply with consent";
});

const analysisButtonLabel = computed(() => {
  if (isAnalysisLoading.value) {
    return "Running analysis...";
  }
  return "Run private analysis";
});

async function loadOffer(): Promise<void> {
  isOfferLoading.value = true;
  isOfferNotFound.value = false;
  offerLoadError.value = null;
  offer.value = null;
  hasApplied.value = false;
  applyError.value = null;
  applySuccessMessage.value = null;
  analysisResult.value = null;
  analysisError.value = null;
  isAnalysisLoading.value = false;

  const offerId = parseOfferId();
  if (offerId === null) {
    isOfferNotFound.value = true;
    isOfferLoading.value = false;
    offerLoadError.value = "Invalid job offer id.";
    return;
  }

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

async function applyToOffer(): Promise<void> {
  if (!offer.value || isApplying.value || hasApplied.value) {
    return;
  }

  const confirmed = await confirm({
    title: "Apply with consent",
    message:
      "Apply to this offer and share your application-time profile snapshot with the recruiter for this offer?",
    confirmLabel: "Apply with consent",
    cancelLabel: "Cancel",
    tone: "primary",
  });
  if (!confirmed) {
    return;
  }

  isApplying.value = true;
  applyError.value = null;
  applySuccessMessage.value = null;

  try {
    await seekerClient.applyToJobOffer(offer.value.id);
    hasApplied.value = true;
    applySuccessMessage.value = "Application submitted. The recruiter now sees your application-time snapshot.";
  } catch (error) {
    applyError.value = error;
    if (error instanceof ApiClientError && error.statusCode === 409) {
      hasApplied.value = true;
    }
  } finally {
    isApplying.value = false;
  }
}

async function runPrivateAnalysis(): Promise<void> {
  if (!offer.value || isAnalysisLoading.value) {
    return;
  }

  isAnalysisLoading.value = true;
  analysisError.value = null;

  try {
    analysisResult.value = await seekerClient.getPrivateJobOfferAnalysis(offer.value.id);
  } catch (error) {
    analysisError.value = error;
  } finally {
    isAnalysisLoading.value = false;
  }
}

watch(
  () => route.params.id,
  async () => {
    await loadOffer();
  },
  { immediate: true },
);
</script>
