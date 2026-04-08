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
            <dt>Application status</dt>
            <dd>{{ offer.applied ? "Applied" : "Not applied" }}</dd>
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

        <JobOfferRequirementsTable
          :requirements="offer.requirements"
          :label-resolver="competencyLabel"
          :activity-indicator-resolver="activityIndicatorsFor"
          :activity-indicator-count-resolver="activityIndicatorCountFor"
          :activity-indicator-loader="loadActivityIndicators"
        />
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
        <p v-if="analysisResult === null" class="section-note">
          No analysis run yet. Use the button above to fetch your private analysis.
        </p>
        <template v-else>
          <MatchingExplanationPanel
            summary-title="Current analysis explanation"
            :explanation="analysisResult.explanation"
            :competency-label="competencyLabel"
          />
          <details class="matching-disclosure">
            <summary class="matching-disclosure-summary">
              <span class="matching-disclosure-closed-label">Show raw analysis payload</span>
              <span class="matching-disclosure-open-label">Hide raw analysis payload</span>
            </summary>
            <JsonPayloadViewer title="Raw analysis payload" :payload="analysisResult" />
          </details>
        </template>
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
            v-if="!hasApplied"
            class="button-primary"
            type="button"
            :disabled="isApplying"
            @click="applyToOffer"
          >
            {{ applyButtonLabel }}
          </button>
          <button
            v-else
            class="button-secondary"
            type="button"
            :disabled="isWithdrawing || currentApplicationId === null"
            @click="withdrawApplication"
          >
            {{ withdrawButtonLabel }}
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
import MatchingExplanationPanel from "../../components/MatchingExplanationPanel.vue";
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
const isWithdrawing = ref(false);
const applyError = ref<unknown | null>(null);
const applySuccessMessage = ref<string | null>(null);
const analysisResult = ref<PrivateMatchingAnalysisResponse | null>(null);
const analysisError = ref<unknown | null>(null);
const isAnalysisLoading = ref(false);
const hasApplied = computed(() => offer.value?.applied ?? false);
const currentApplicationId = computed(() => offer.value?.application_id ?? null);

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

function activityIndicatorsFor(competencyKey: string) {
  return labelCache.getActivityIndicators(competencyKey) ?? [];
}

function activityIndicatorCountFor(competencyKey: string): number {
  return labelCache.getActivityIndicatorCount(competencyKey);
}

async function loadActivityIndicators(competencyKey: string): Promise<void> {
  await labelCache.ensureActivityIndicators(competencyKey);
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
  return "Apply with consent";
});

const withdrawButtonLabel = computed(() => {
  if (isWithdrawing.value) {
    return "Withdrawing...";
  }
  return "Withdraw application";
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
    const created = await seekerClient.applyToJobOffer(offer.value.id);
    offer.value.applied = true;
    offer.value.application_id = created.id;
    applySuccessMessage.value = "Application submitted. The recruiter now sees your application-time snapshot.";
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 409) {
      applySuccessMessage.value = "Application already submitted for this offer.";
      try {
        offer.value = await seekerClient.getPublishedJobOffer(offer.value.id);
      } catch {
        // Keep the page usable even if refresh fails.
      }
    } else {
      applyError.value = error;
    }
  } finally {
    isApplying.value = false;
  }
}

async function withdrawApplication(): Promise<void> {
  if (!offer.value || isWithdrawing.value || !hasApplied.value || currentApplicationId.value === null) {
    return;
  }

  const confirmed = await confirm({
    title: "Withdraw application",
    message:
      "Withdraw this application and remove recruiter access to the application-time snapshot for this offer?",
    confirmLabel: "Withdraw application",
    cancelLabel: "Cancel",
    tone: "danger",
  });
  if (!confirmed) {
    return;
  }

  isWithdrawing.value = true;
  applyError.value = null;
  applySuccessMessage.value = null;

  try {
    await seekerClient.deleteApplication(currentApplicationId.value);
    offer.value.applied = false;
    offer.value.application_id = null;
    applySuccessMessage.value = "Application withdrawn. Recruiter access to this application is removed.";
  } catch (error) {
    applyError.value = error;
  } finally {
    isWithdrawing.value = false;
  }
}

async function runPrivateAnalysis(): Promise<void> {
  if (!offer.value || isAnalysisLoading.value) {
    return;
  }

  isAnalysisLoading.value = true;
  analysisError.value = null;

  try {
    const result = await seekerClient.getPrivateJobOfferAnalysis(offer.value.id);
    analysisResult.value = result;
    const explanationCompetencyKeys = collectExplanationCompetencyKeys(result);
    if (explanationCompetencyKeys.length > 0) {
      void labelCache.hydrateKeys(explanationCompetencyKeys);
    }
  } catch (error) {
    analysisError.value = error;
  } finally {
    isAnalysisLoading.value = false;
  }
}

function collectExplanationCompetencyKeys(result: PrivateMatchingAnalysisResponse): string[] {
  const keys = new Set<string>();

  for (const item of result.explanation.highlights) {
    keys.add(item.competency_key);
  }

  for (const item of result.explanation.gaps) {
    keys.add(item.competency_key);
  }

  for (const item of result.explanation.development_roadmap ?? []) {
    keys.add(item.competency_key);
  }

  return [...keys];
}

watch(
  () => route.params.id,
  async () => {
    await loadOffer();
  },
  { immediate: true },
);
</script>
