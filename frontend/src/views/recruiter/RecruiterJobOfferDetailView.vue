<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/recruiter">Back to recruiter</RouterLink>
        <RouterLink
          v-if="jobOffer"
          class="button-secondary"
          :to="`/recruiter/job-offers/${jobOffer.id}/edit`"
        >
          Edit offer
        </RouterLink>
        <RouterLink
          v-if="jobOffer"
          class="button-secondary"
          :to="`/recruiter/job-offers/${jobOffer.id}/applicants`"
        >
          View applicants
        </RouterLink>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Job Offer Details</h1>
        <p class="content">Read-only view for a single offer and its requirements.</p>
      </header>

      <ApiErrorNotice v-if="deleteOfferError" :error="deleteOfferError" show-all-messages />

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Offer</h2>
          <p>Read-only summary and publication controls for this offer.</p>
        </header>

        <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />
        <ApiErrorNotice v-if="transitionError" :error="transitionError" show-all-messages />
        <p v-if="transitionSuccessMessage" class="form-success">{{ transitionSuccessMessage }}</p>

        <p v-if="isOfferLoading" class="section-note">Loading offer...</p>
        <p v-else-if="isOfferNotFound" class="section-note">Job offer not found.</p>

        <template v-else-if="jobOffer">
          <dl class="summary-grid">
            <dt>Title</dt>
            <dd>{{ jobOffer.title }}</dd>
            <dt>Status</dt>
            <dd><JobOfferStatusBadge :status="jobOffer.status" /></dd>
            <dt>Occupation</dt>
            <dd>
              {{ occupationLabel || jobOffer.occupation_key }}
              <small>({{ jobOffer.occupation_key }})</small>
            </dd>
            <dt>Description</dt>
            <dd>{{ jobOffer.description }}</dd>
          </dl>

          <div class="table-actions">
            <RouterLink class="button-secondary" :to="`/recruiter/job-offers/${jobOffer.id}/edit`">
              Edit offer
            </RouterLink>
            <RouterLink class="button-secondary" :to="`/recruiter/job-offers/${jobOffer.id}/applicants`">
              View applicants
            </RouterLink>
            <button
              v-if="jobOffer.status === 'draft'"
              class="button-primary"
              type="button"
              :disabled="isTransitioning || isDeletingOffer"
              @click="publishOffer"
            >
              {{ isTransitioning ? "Publishing..." : "Publish offer" }}
            </button>
            <button
              v-else-if="jobOffer.status === 'published'"
              class="button-secondary"
              type="button"
              :disabled="isTransitioning || isDeletingOffer"
              @click="archiveOffer"
            >
              {{ isTransitioning ? "Archiving..." : "Archive offer" }}
            </button>
            <button
              class="button-danger"
              type="button"
              :disabled="isDeletingOffer || isTransitioning"
              @click="deleteOffer"
            >
              {{ isDeletingOffer ? "Deleting..." : "Delete offer" }}
            </button>
          </div>
        </template>
      </section>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Requirements</h2>
          <p>Read-only list of competency requirements for this offer.</p>
        </header>

        <ApiErrorNotice v-if="requirementsLoadError" :error="requirementsLoadError" show-all-messages />

        <p v-if="isRequirementsLoading" class="table-note">Loading requirements...</p>
        <JobOfferRequirementsTable
          v-else
          :requirements="tableRequirements"
          empty-text="No requirements saved yet."
          :label-resolver="competencyLabel"
        />
      </section>
    </section>
  </main>
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
    title: "Delete offer",
    message: "Delete this draft offer and all requirements?",
    confirmLabel: "Delete offer",
    cancelLabel: "Keep offer",
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
    title: "Publish offer",
    message: "Publish this offer now? After publishing, seekers can discover and view it in the marketplace.",
    confirmLabel: "Publish offer",
    cancelLabel: "Keep draft",
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
    transitionSuccessMessage.value = "Offer published.";
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
    title: "Archive offer",
    message: "Archive this offer now? Archived offers are no longer visible in the seeker marketplace.",
    confirmLabel: "Archive offer",
    cancelLabel: "Keep published",
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
    transitionSuccessMessage.value = "Offer archived.";
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
