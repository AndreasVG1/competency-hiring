<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/recruiter">Back to recruiter</RouterLink>
        <RouterLink
          v-if="jobOffer"
          class="button-secondary"
          :to="`/recruiter/job-offers/${jobOffer.id}`"
        >
          View read-only
        </RouterLink>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Edit Job Offer</h1>
        <p class="content">Update offer fields, manage requirements, and control publication state.</p>
      </header>

      <ApiErrorNotice v-if="deleteOfferError" :error="deleteOfferError" show-all-messages />

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Offer</h2>
          <p>Editable offer fields and explicit status transitions.</p>
        </header>

        <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />
        <ApiErrorNotice v-if="transitionError" :error="transitionError" show-all-messages />
        <p v-if="transitionSuccessMessage" class="form-success">{{ transitionSuccessMessage }}</p>

        <p v-if="isOfferLoading" class="section-note">Loading offer...</p>
        <p v-else-if="isOfferNotFound" class="section-note">Job offer not found.</p>

        <form v-else-if="jobOffer" class="recruiter-form" @submit.prevent="saveOffer">
          <p class="selected-item">
            <strong>Current status:</strong>
            <JobOfferStatusBadge :status="jobOffer.status" />
          </p>

          <div class="table-actions">
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
          </div>

          <CatalogSearchPicker
            :key="offerOccupationPickerKey"
            label="Occupation"
            placeholder="Search occupations"
            no-results-text="No occupations found."
            :disabled="isUpdatingOffer"
            :busy="isUpdatingOffer"
            :search-fn="searchOccupations"
            @select="selectOfferOccupation"
          />

          <p class="selected-item">
            <strong>Selected occupation:</strong>
            <span v-if="offerForm.occupationKey">
              {{ offerForm.occupationLabel || offerForm.occupationKey }}
              <small>({{ offerForm.occupationKey }})</small>
            </span>
            <span v-else>None</span>
          </p>

          <label class="form-field">
            <span>Description</span>
            <textarea
              v-model="offerForm.description"
              rows="4"
              required
              :disabled="isUpdatingOffer"
            />
          </label>

          <ApiErrorNotice v-if="offerUpdateError" :error="offerUpdateError" show-all-messages />
          <p v-if="offerUpdateSuccessMessage" class="form-success">{{ offerUpdateSuccessMessage }}</p>

          <div class="table-actions">
            <button class="button-primary" type="submit" :disabled="isUpdatingOffer">
              {{ isUpdatingOffer ? "Saving offer..." : "Save offer" }}
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
        </form>
      </section>

      <section class="recruiter-section" v-if="jobOffer">
        <header class="section-header">
          <h2>Requirements</h2>
          <p>Add and maintain competency priorities.</p>
        </header>

        <ApiErrorNotice v-if="requirementsLoadError" :error="requirementsLoadError" show-all-messages />

        <OccupationCompetencySuggestions
          :occupation-key="jobOffer.occupation_key"
          :selected-keys="existingRequirementKeys"
          :disabled="isRequirementsLoading"
          :busy="isAddingRequirement"
          label="Competencies related to selected occupation"
          waiting-text="Select an occupation for this offer to see related competencies."
          @select="addSuggestedRequirement"
        />

        <form class="recruiter-form" @submit.prevent="addRequirement">
          <CatalogSearchPicker
            :key="requirementPickerKey"
            label="Competency"
            placeholder="Search competencies"
            no-results-text="No competencies found."
            :disabled="isRequirementsLoading"
            :busy="isAddingRequirement"
            :search-fn="searchCompetencies"
            @select="selectRequirementCompetency"
          />

          <p class="selected-item">
            <strong>Selected competency:</strong>
            <span v-if="selectedRequirementCompetency">
              {{ selectedRequirementCompetency.label }}
              <small>({{ selectedRequirementCompetency.key }})</small>
            </span>
            <span v-else>None</span>
          </p>

          <EnumSelect
            v-model="newRequirementPriority"
            label="Priority"
            :options="requirementPriorityOptions"
            :disabled="isAddingRequirement || isRequirementsLoading"
          />

          <ApiErrorNotice v-if="addRequirementError" :error="addRequirementError" show-all-messages />
          <p v-if="addRequirementSuccessMessage" class="form-success">{{ addRequirementSuccessMessage }}</p>

          <button class="button-primary" type="submit" :disabled="isAddingRequirement || isRequirementsLoading">
            {{ isAddingRequirement ? "Adding requirement..." : "Add requirement" }}
          </button>
        </form>

        <p v-if="isRequirementsLoading" class="table-note">Loading requirements...</p>
        <p v-else-if="requirementRows.length === 0" class="table-note">No requirements saved yet.</p>

        <table v-else class="competency-table">
          <thead>
            <tr>
              <th>Competency</th>
              <th>Key</th>
              <th>Priority</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in requirementRows" :key="row.id">
              <td>{{ competencyLabel(row.competencyKey) }}</td>
              <td><code>{{ row.competencyKey }}</code></td>
              <td>
                <EnumSelect
                  v-model="row.priorityDraft"
                  label=""
                  :options="requirementPriorityOptions"
                  :disabled="row.isSaving || row.isDeleting"
                />
              </td>
              <td>
                <div class="table-actions">
                  <button
                    class="button-secondary"
                    type="button"
                    :disabled="row.isSaving || row.isDeleting || row.priorityDraft === row.persistedPriority"
                    @click="saveRequirementPriority(row.id)"
                  >
                    {{ row.isSaving ? "Saving..." : "Save" }}
                  </button>
                  <button
                    class="button-danger"
                    type="button"
                    :disabled="row.isSaving || row.isDeleting"
                    @click="deleteRequirement(row.id)"
                  >
                    {{ row.isDeleting ? "Removing..." : "Remove" }}
                  </button>
                </div>
                <ApiErrorNotice v-if="row.error" :error="row.error" />
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiClientError, catalogClient, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import CatalogSearchPicker from "../../components/CatalogSearchPicker.vue";
import EnumSelect from "../../components/EnumSelect.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import OccupationCompetencySuggestions from "../../components/OccupationCompetencySuggestions.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useConfirmDialog } from "../../composables/useConfirmDialog";
import type {
  CatalogItem,
  JobOfferRequirementResponse,
  JobOfferResponse,
  RequirementPriority,
} from "../../types/domain";

interface OfferFormState {
  occupationKey: string | null;
  occupationLabel: string | null;
  description: string;
}

interface RequirementRowState {
  id: number;
  competencyKey: string;
  priorityDraft: RequirementPriority;
  persistedPriority: RequirementPriority;
  isSaving: boolean;
  isDeleting: boolean;
  error: unknown | null;
}

const route = useRoute();
const router = useRouter();

const { confirm } = useConfirmDialog();
const labelCache = useCatalogLabelCache();

const requirementPriorityOptions: { value: RequirementPriority; label: string }[] = [
  { value: "must_have", label: "Must have" },
  { value: "important", label: "Important" },
  { value: "nice_to_have", label: "Nice to have" },
];

const jobOffer = ref<JobOfferResponse | null>(null);

const offerForm = reactive<OfferFormState>({
  occupationKey: null,
  occupationLabel: null,
  description: "",
});

const isOfferLoading = ref(true);
const isOfferNotFound = ref(false);
const isUpdatingOffer = ref(false);
const isDeletingOffer = ref(false);
const isTransitioning = ref(false);
const offerLoadError = ref<unknown | null>(null);
const offerUpdateError = ref<unknown | null>(null);
const offerUpdateSuccessMessage = ref<string | null>(null);
const deleteOfferError = ref<unknown | null>(null);
const transitionError = ref<unknown | null>(null);
const transitionSuccessMessage = ref<string | null>(null);
const offerOccupationPickerKey = ref(0);

const requirementRows = ref<RequirementRowState[]>([]);
const isRequirementsLoading = ref(false);
const requirementsLoadError = ref<unknown | null>(null);

const selectedRequirementCompetency = ref<CatalogItem | null>(null);
const newRequirementPriority = ref<RequirementPriority>("must_have");
const isAddingRequirement = ref(false);
const addRequirementError = ref<unknown | null>(null);
const addRequirementSuccessMessage = ref<string | null>(null);
const requirementPickerKey = ref(0);

const existingRequirementKeys = computed(() => requirementRows.value.map((row) => row.competencyKey));

function parseOfferId(): number | null {
  const offerId = Number(route.params.id);
  if (!Number.isInteger(offerId) || offerId <= 0) {
    return null;
  }
  return offerId;
}

function hydrateOfferForm(offer: JobOfferResponse): void {
  offerForm.occupationKey = offer.occupation_key;
  offerForm.occupationLabel = offer.title;
  offerForm.description = offer.description;
  offerOccupationPickerKey.value += 1;
}

function mapRequirementToRow(requirement: JobOfferRequirementResponse): RequirementRowState {
  return {
    id: requirement.id,
    competencyKey: requirement.competency_key,
    priorityDraft: requirement.priority,
    persistedPriority: requirement.priority,
    isSaving: false,
    isDeleting: false,
    error: null,
  };
}

async function searchCompetencies(query: string): Promise<CatalogItem[]> {
  return catalogClient.listCompetencies({ query, limit: 8 });
}

async function searchOccupations(query: string): Promise<CatalogItem[]> {
  return catalogClient.listOccupations({ query, limit: 8 });
}

function selectOfferOccupation(item: CatalogItem): void {
  offerForm.occupationKey = item.key;
  offerForm.occupationLabel = item.label;
  offerUpdateError.value = null;
  offerUpdateSuccessMessage.value = null;
}

function selectRequirementCompetency(item: CatalogItem): void {
  selectedRequirementCompetency.value = item;
  addRequirementError.value = null;
  addRequirementSuccessMessage.value = null;
}

function addSuggestedRequirement(item: CatalogItem): void {
  void addRequirementFromItem(item, { resetPicker: false });
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

async function loadOffer(): Promise<void> {
  const offerId = parseOfferId();
  if (offerId === null) {
    isOfferLoading.value = false;
    isOfferNotFound.value = true;
    offerLoadError.value = "Invalid job offer id.";
    return;
  }

  isOfferLoading.value = true;
  isOfferNotFound.value = false;
  offerLoadError.value = null;
  requirementsLoadError.value = null;
  offerUpdateError.value = null;
  offerUpdateSuccessMessage.value = null;
  deleteOfferError.value = null;
  transitionError.value = null;
  transitionSuccessMessage.value = null;
  requirementRows.value = [];

  try {
    const loadedOffer = await recruiterClient.getJobOffer(offerId);
    jobOffer.value = loadedOffer;
    hydrateOfferForm(loadedOffer);
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
    const requirements = await recruiterClient.listRequirements(offerId);
    requirementRows.value = requirements.map(mapRequirementToRow);
    void labelCache.hydrateKeys(requirements.map((item) => item.competency_key));
  } catch (error) {
    requirementsLoadError.value = error;
  } finally {
    isRequirementsLoading.value = false;
  }
}

async function saveOffer(): Promise<void> {
  if (!jobOffer.value || isUpdatingOffer.value) {
    return;
  }

  if (!offerForm.occupationKey) {
    offerUpdateError.value = "Choose an occupation before saving the offer.";
    return;
  }

  isUpdatingOffer.value = true;
  offerUpdateError.value = null;
  offerUpdateSuccessMessage.value = null;

  try {
    const updated = await recruiterClient.updateJobOffer(jobOffer.value.id, {
      occupation_key: offerForm.occupationKey,
      description: offerForm.description.trim(),
    });
    jobOffer.value = updated;
    hydrateOfferForm(updated);
    offerUpdateSuccessMessage.value = "Draft offer saved.";
  } catch (error) {
    offerUpdateError.value = error;
  } finally {
    isUpdatingOffer.value = false;
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
    hydrateOfferForm(updatedOffer);
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
    hydrateOfferForm(updatedOffer);
    transitionSuccessMessage.value = "Offer archived.";
  } catch (error) {
    transitionError.value = error;
  } finally {
    isTransitioning.value = false;
  }
}

async function addRequirement(): Promise<void> {
  if (!selectedRequirementCompetency.value) {
    addRequirementError.value = "Choose a competency before adding.";
    return;
  }

  await addRequirementFromItem(selectedRequirementCompetency.value, { resetPicker: true });
}

async function addRequirementFromItem(
  item: CatalogItem,
  options: { resetPicker: boolean },
): Promise<void> {
  if (!jobOffer.value || isRequirementsLoading.value || isAddingRequirement.value) {
    return;
  }

  addRequirementError.value = null;
  addRequirementSuccessMessage.value = null;

  if (requirementRows.value.some((row) => row.competencyKey === item.key)) {
    addRequirementError.value = "This competency is already a requirement for this offer.";
    return;
  }

  isAddingRequirement.value = true;

  try {
    const created = await recruiterClient.addRequirement(jobOffer.value.id, {
      competency_key: item.key,
      priority: newRequirementPriority.value,
    });

    requirementRows.value = [mapRequirementToRow(created), ...requirementRows.value];
    labelCache.setLabel(item.key, item.label);

    if (options.resetPicker) {
      selectedRequirementCompetency.value = null;
      newRequirementPriority.value = "must_have";
      requirementPickerKey.value += 1;
    }

    addRequirementSuccessMessage.value = "Requirement added.";
  } catch (error) {
    addRequirementError.value = error;
  } finally {
    isAddingRequirement.value = false;
  }
}

async function saveRequirementPriority(rowId: number): Promise<void> {
  if (!jobOffer.value) {
    return;
  }

  const row = requirementRows.value.find((candidate) => candidate.id === rowId);
  if (!row || row.isSaving || row.isDeleting || row.priorityDraft === row.persistedPriority) {
    return;
  }

  row.isSaving = true;
  row.error = null;

  try {
    const updated = await recruiterClient.updateRequirement(jobOffer.value.id, row.id, {
      priority: row.priorityDraft,
    });

    row.persistedPriority = updated.priority;
    row.priorityDraft = updated.priority;
  } catch (error) {
    row.error = error;
  } finally {
    row.isSaving = false;
  }
}

async function deleteRequirement(rowId: number): Promise<void> {
  if (!jobOffer.value) {
    return;
  }

  const row = requirementRows.value.find((candidate) => candidate.id === rowId);
  if (!row || row.isSaving || row.isDeleting) {
    return;
  }

  row.isDeleting = true;
  row.error = null;

  try {
    await recruiterClient.deleteRequirement(jobOffer.value.id, row.id);
    requirementRows.value = requirementRows.value.filter((candidate) => candidate.id !== row.id);
  } catch (error) {
    row.error = error;
    row.isDeleting = false;
  }
}

watch(
  () => route.params.id,
  () => {
    selectedRequirementCompetency.value = null;
    newRequirementPriority.value = "must_have";
    addRequirementError.value = null;
    addRequirementSuccessMessage.value = null;
    requirementPickerKey.value += 1;
    void loadOffer();
  },
  { immediate: true },
);

onMounted(async () => {
  if (!jobOffer.value && !isOfferLoading.value) {
    await loadOffer();
  }
});
</script>
