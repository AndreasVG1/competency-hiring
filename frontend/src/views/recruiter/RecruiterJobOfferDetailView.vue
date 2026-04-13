<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/recruiter">Tagasi avalehele</RouterLink>
      <RouterLink v-if="jobOffer" class="btn btn-outline-secondary" :to="`/recruiter/job-offers/${jobOffer.id}/edit`">
        Muuda pakkumist
      </RouterLink>
      <RouterLink
        v-if="jobOffer"
        class="btn btn-outline-secondary"
        :to="`/recruiter/job-offers/${jobOffer.id}/applicants`"
      >
        Vaata kandidaate
      </RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Tööandja vaade</p>
      <h1 class="h3 mb-1">Tööpakkumise Ülevaade</h1>
    </header>

    <ApiErrorNotice v-if="deleteOfferError" :error="deleteOfferError" show-all-messages />

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Tööpakkumine</h2>
      </header>

      <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />
      <ApiErrorNotice v-if="transitionError" :error="transitionError" show-all-messages />
      <div v-if="transitionSuccessMessage" class="alert alert-success mb-0" role="status">
        {{ transitionSuccessMessage }}
      </div>

      <p v-if="isOfferLoading" class="text-body-secondary mb-0">Laen tööpakkumist...</p>
      <p v-else-if="isOfferNotFound" class="text-body-secondary mb-0">Tööpakkumist ei leitud.</p>

      <template v-else-if="jobOffer">
        <dl class="row mb-0">
          <dt class="col-sm-3 text-body-secondary">Pealkiri</dt>
          <dd class="col-sm-9 text-break">{{ jobOffer.title }}</dd>
          <dt class="col-sm-3 text-body-secondary">Staatus</dt>
          <dd class="col-sm-9"><JobOfferStatusBadge :status="jobOffer.status" /></dd>
          <dt class="col-sm-3 text-body-secondary">Ametikoht</dt>
          <dd class="col-sm-9 text-break">
            {{ occupationLabel || jobOffer.occupation_key }}
            <span class="d-block small text-body-secondary break-all">({{ jobOffer.occupation_key }})</span>
          </dd>
          <dt class="col-sm-3 text-body-secondary">Kirjeldus  </dt>
          <dd class="col-sm-9 text-break">{{ jobOffer.description }}</dd>
        </dl>

        <div class="d-flex flex-wrap gap-2">
          <RouterLink class="btn btn-outline-secondary" :to="`/recruiter/job-offers/${jobOffer.id}/edit`">
            Muuda pakkumist
          </RouterLink>
          <RouterLink class="btn btn-outline-secondary" :to="`/recruiter/job-offers/${jobOffer.id}/applicants`">
            Vaata kandidaate
          </RouterLink>
          <button
            v-if="jobOffer.status === 'draft'"
            class="btn btn-primary"
            type="button"
            :disabled="isTransitioning || isDeletingOffer"
            @click="publishOffer"
          >
            {{ isTransitioning ? "Avaldamine..." : "Avalda pakkumine" }}
          </button>
          <button
            v-else-if="jobOffer.status === 'published'"
            class="btn btn-outline-secondary"
            type="button"
            :disabled="isTransitioning || isDeletingOffer"
            @click="archiveOffer"
          >
            {{ isTransitioning ? "Arhiveerimine..." : "Arhiveeri pakkumine" }}
          </button>
          <button
            class="btn btn-outline-danger"
            type="button"
            :disabled="isDeletingOffer || isTransitioning"
            @click="deleteOffer"
          >
            {{ isDeletingOffer ? "Kustutamine..." : "Kustuta pakkumine" }}
          </button>
        </div>
      </template>
    </section>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Kompetentsid</h2>
      </header>

      <ApiErrorNotice v-if="requirementsLoadError" :error="requirementsLoadError" show-all-messages />

      <p v-if="isRequirementsLoading" class="text-body-secondary mb-0">Laadin kompetentse...</p>
      <JobOfferRequirementsTable
        v-else
        :requirements="tableRequirements"
        empty-text="Kompetentse pole veel salvestatud."
        :label-resolver="competencyLabel"
        :activity-indicator-resolver="activityIndicatorsFor"
        :activity-indicator-count-resolver="activityIndicatorCountFor"
        :activity-indicator-loader="loadActivityIndicators"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiClientError, catalogClient, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferRequirementsTable from "../../components/JobOfferRequirementsTable.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useConfirmDialog } from "../../composables/useConfirmDialog";
import type {
  JobOfferRequirementResponse,
  JobOfferResponse,
  PublicJobOfferRequirementItem,
} from "../../types/domain";

const route = useRoute();
const router = useRouter();

const { confirm } = useConfirmDialog();
const labelCache = useCatalogLabelCache();

const jobOffer = ref<JobOfferResponse | null>(null);
const requirements = ref<JobOfferRequirementResponse[]>([]);
const occupationLabel = ref<string | null>(null);

const isOfferLoading = ref(true);
const isRequirementsLoading = ref(false);
const isOfferNotFound = ref(false);
const isDeletingOffer = ref(false);
const isTransitioning = ref(false);

const offerLoadError = ref<unknown | null>(null);
const requirementsLoadError = ref<unknown | null>(null);
const deleteOfferError = ref<unknown | null>(null);
const transitionError = ref<unknown | null>(null);
const transitionSuccessMessage = ref<string | null>(null);

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

const tableRequirements = computed<PublicJobOfferRequirementItem[]>(() => {
  return requirements.value.map((item) => ({
    competency_key: item.competency_key,
    priority: item.priority,
  }));
});

async function loadOffer(): Promise<void> {
  const offerId = parseOfferId();
  if (offerId === null) {
    isOfferNotFound.value = true;
    offerLoadError.value = "Invalid job offer id.";
    isOfferLoading.value = false;
    return;
  }

  isOfferLoading.value = true;
  isOfferNotFound.value = false;
  offerLoadError.value = null;
  requirementsLoadError.value = null;
  transitionError.value = null;
  transitionSuccessMessage.value = null;
  requirements.value = [];
  occupationLabel.value = null;

  try {
    const loadedOffer = await recruiterClient.getJobOffer(offerId);
    jobOffer.value = loadedOffer;

    try {
      const occupation = await catalogClient.getOccupation(loadedOffer.occupation_key);
      occupationLabel.value = occupation.label;
    } catch {
      occupationLabel.value = null;
    }

    await loadRequirements(offerId);
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isOfferNotFound.value = true;
      jobOffer.value = null;
      return;
    }

    offerLoadError.value = error;
  } finally {
    isOfferLoading.value = false;
  }
}

async function loadRequirements(offerId: number): Promise<void> {
  isRequirementsLoading.value = true;
  requirementsLoadError.value = null;

  try {
    const loadedRequirements = await recruiterClient.listRequirements(offerId);
    requirements.value = loadedRequirements;

    for (const item of loadedRequirements) {
      if (
        item.competency_label != null &&
        typeof item.activity_indicator_count === "number"
      ) {
        labelCache.setCompetencyMeta(
          item.competency_key,
          item.competency_label,
          item.activity_indicator_count,
        );
      }
    }

    void labelCache.hydrateKeys(loadedRequirements.map((item) => item.competency_key));
  } catch (error) {
    requirementsLoadError.value = error;
  } finally {
    isRequirementsLoading.value = false;
  }
}

async function deleteOffer(): Promise<void> {
  if (!jobOffer.value || isDeletingOffer.value || isTransitioning.value) {
    return;
  }

  const confirmed = await confirm({
    title: "Kustuta pakkumine",
    message: "Kustuta see pakkumine ja kõik nõuded?",
    confirmLabel: "Kustuta pakkumine",
    cancelLabel: "Tagasi",
    tone: "danger",
  });
  if (!confirmed) {
    return;
  }

  isDeletingOffer.value = true;
  deleteOfferError.value = null;

  try {
    await recruiterClient.deleteJobOffer(jobOffer.value.id);
    await router.replace("/recruiter");
  } catch (error) {
    deleteOfferError.value = error;
  } finally {
    isDeletingOffer.value = false;
  }
}

async function publishOffer(): Promise<void> {
  if (!jobOffer.value || jobOffer.value.status !== "draft" || isTransitioning.value || isDeletingOffer.value) {
    return;
  }

  const confirmed = await confirm({
    title: "Avalda pakkumine",
    message: "Avalda see pakkumine? Pärast avaldamist muutub see tööotsijatele nähtavaks.",
    confirmLabel: "Avalda pakkumine",
    cancelLabel: "Tagasi",
    tone: "primary",
  });
  if (!confirmed) {
    return;
  }

  isTransitioning.value = true;
  transitionError.value = null;
  transitionSuccessMessage.value = null;

  try {
    const updatedOffer = await recruiterClient.publishJobOffer(jobOffer.value.id);
    jobOffer.value = updatedOffer;
    transitionSuccessMessage.value = "Tööpakkumine avaldatud.";
  } catch (error) {
    transitionError.value = error;
  } finally {
    isTransitioning.value = false;
  }
}

async function archiveOffer(): Promise<void> {
  if (
    !jobOffer.value ||
    jobOffer.value.status !== "published" ||
    isTransitioning.value ||
    isDeletingOffer.value
  ) {
    return;
  }

  const confirmed = await confirm({
    title: "Arhiveeri pakkumine",
    message: "Arhiveeri see pakkumine nüüd? Arhiveeritud pakkumised ei ole enam tööotsijatele nähtavad.",
    confirmLabel: "Arhiveeri pakkumine",
    cancelLabel: "Tagasi",
    tone: "danger",
  });
  if (!confirmed) {
    return;
  }

  isTransitioning.value = true;
  transitionError.value = null;
  transitionSuccessMessage.value = null;

  try {
    const updatedOffer = await recruiterClient.archiveJobOffer(jobOffer.value.id);
    jobOffer.value = updatedOffer;
    transitionSuccessMessage.value = "Tööpakkumine arhiveeritud.";
  } catch (error) {
    transitionError.value = error;
  } finally {
    isTransitioning.value = false;
  }
}

onMounted(async () => {
  await loadOffer();
});
</script>
