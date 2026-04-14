<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/seeker/job-offers">Tagasi tööpakkumiste juurde</RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Tööpakkumised</p>
      <h1 class="h3 mb-1">Tööpakkumise üksikasjad</h1>
      <p class="text-body-secondary mb-0">Vaata tööpakkumise teavet enne kandideerimisotsuse langetamist.</p>
    </header>

    <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-0">Tööpakkumine</h2>
      </header>

      <p v-if="isOfferLoading" class="text-body-secondary mb-0">Tööpakkumise laadimine...</p>
      <template v-else-if="isOfferNotFound">
        <p class="text-body-secondary mb-0">Avaldatud tööpakkumist ei leitud.</p>
        <div>
          <RouterLink class="btn btn-outline-secondary" to="/seeker/job-offers">Tagasi tööpakkumiste juurde</RouterLink>
        </div>
      </template>
      <template v-else-if="offer">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
          <h3 class="h6 mb-0 text-break">{{ offer.title }}</h3>
          <JobOfferStatusBadge status="published" />
        </div>

        <dl class="row mb-0">
          <dt class="col-sm-3 text-body-secondary">Ettevõte</dt>
          <dd class="col-sm-9 text-break">{{ offer.company_name || "Ettevõte pole määratud" }}</dd>
          <dt class="col-sm-3 text-body-secondary">Ametikoht</dt>
          <dd class="col-sm-9 text-break">{{ offer.occupation_label }}</dd>
          <dt class="col-sm-3 text-body-secondary">Avaldatud</dt>
          <dd class="col-sm-9 text-break">{{ formatDateTime(offer.published_at) }}</dd>
          <dt class="col-sm-3 text-body-secondary">Kandideerimise staatus</dt>
          <dd class="col-sm-9 text-break">{{ offer.applied ? "Kandideeritud" : "Kandideerimata" }}</dd>
          <dt class="col-sm-3 text-body-secondary">Kirjeldus</dt>
          <dd class="col-sm-9 text-break">{{ offer.description }}</dd>
        </dl>
      </template>
    </section>

    <section v-if="offer && !isOfferNotFound" class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Nõuded</h2>
        <p class="text-body-secondary mb-0">Nõuded on loetletud täpselt nii, nagu need on avaldanud värbaja.</p>
      </header>

      <JobOfferRequirementsTable
        :requirements="offer.requirements"
        :label-resolver="competencyLabel"
        :activity-indicator-resolver="activityIndicatorsFor"
        :activity-indicator-count-resolver="activityIndicatorCountFor"
        :activity-indicator-loader="loadActivityIndicators"
      />
    </section>

    <section v-if="offer && !isOfferNotFound" class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Privaatne analüüs</h2>
        <p class="text-body-secondary mb-0">
          Käivita sobivusanalüüs, et vaadata oma sobivust töökohale. Sinu andmeid ei edastata tööandjale.
        </p>
      </header>
      <ApiErrorNotice v-if="analysisError" :error="analysisError" show-all-messages />
      <div class="d-flex flex-wrap gap-2">
        <button class="btn btn-outline-secondary" type="button" :disabled="isAnalysisLoading" @click="runPrivateAnalysis">
          {{ analysisButtonLabel }}
        </button>
      </div>
      <p v-if="analysisResult === null" class="text-body-secondary mb-0">
        Analüüsi pole veel käivitatud. Vajuta nupule, et käivitada analüüs.
      </p>
      <template v-else>
        <MatchingExplanationPanel
          summary-title="Sobivusanalüüsi kokkuvõte"
          :explanation="analysisResult.explanation"
          :competency-label="competencyLabel"
        />
        <details class="matching-disclosure">
          <summary class="matching-disclosure-summary">
            <span class="matching-disclosure-closed-label">Näita analüüsi üksikasju</span>
            <span class="matching-disclosure-open-label">Peida analüüsi üksikasjad</span>
          </summary>
          <JsonPayloadViewer title="Analüüsi üksikasjad" :payload="analysisResult" />
        </details>
      </template>
    </section>

    <section v-if="offer && !isOfferNotFound" class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Kandideerimine</h2>
        <p class="text-body-secondary mb-0">
          Kandideerimine on selgesõnaline nõusoleku tegevus. Kui kandideerid, jagatakse sinu profiili hetkeseis kandideerimise ajal
          värbajaga selle pakkumise jaoks.
        </p>
      </header>
      <ApiErrorNotice v-if="applyError" :error="applyError" show-all-messages />
      <div v-if="applySuccessMessage" class="alert alert-success mb-0" role="status">
        {{ applySuccessMessage }}
      </div>
      <div class="alert alert-info mb-0">
        Tähelepanek: värbajaga jagatakse e-post ja profiili hetkeseis kandideerimise ajal. Värbajale ei kajastu hiljem tehtud muudatused.
      </div>
      <div class="d-flex flex-wrap gap-2">
        <button v-if="!hasApplied" class="btn btn-primary" type="button" :disabled="isApplying" @click="applyToOffer">
          {{ applyButtonLabel }}
        </button>
        <button
          v-else
          class="btn btn-outline-secondary"
          type="button"
          :disabled="isWithdrawing || currentApplicationId === null"
          @click="withdrawApplication"
        >
          {{ withdrawButtonLabel }}
        </button>
      </div>
    </section>
  </div>
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
    return "Kandideerimine...";
  }
  return "Kandideeri nõusolekuga";
});

const withdrawButtonLabel = computed(() => {
  if (isWithdrawing.value) {
    return "Tühistamine...";
  }
  return "Tühista kandideerimine";
});

const analysisButtonLabel = computed(() => {
  if (isAnalysisLoading.value) {
    return "Analüüsi käivitamine...";
  }
  return "Käivita sobivusanalüüs";
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

    for (const requirement of loadedOffer.requirements) {
      if (
        requirement.competency_label != null &&
        typeof requirement.activity_indicator_count === "number"
      ) {
        labelCache.setCompetencyMeta(
          requirement.competency_key,
          requirement.competency_label,
          requirement.activity_indicator_count,
        );
      }
    }

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
    title: "Kandideeri pakkumisele",
    message:
      "Kandideerides sellele pakkumisele jagatakse sinu e-post ja profiili hetkeseis kandideerimise ajal värbajaga.",
    confirmLabel: "Kandideeri nõusolekuga",
    cancelLabel: "Tagasi",
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
    applySuccessMessage.value = "Kandideerimine esitatud. Värbaja näeb nüüd sinu kandideerimiseaegset profiili.";
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 409) {
      applySuccessMessage.value = "Kandideerimine on juba selle pakkumise jaoks esitatud.";
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
    title: "Tühista kandideerimine",
    message:
      "Kas soovid tühistada selle kandideerimise ja eemaldada värbaja juurdepääsu kandideerimiseaegsele profiilile?",
    confirmLabel: "Tühista kandideerimine",
    cancelLabel: "Tagasi",
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
    applySuccessMessage.value = "Kandideerimine tühistatud. Värbaja juurdepääs sellele kandideerimisele on eemaldatud.";
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
