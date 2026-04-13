<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/recruiter">Tagasi avalehele</RouterLink>
      <RouterLink v-if="jobOffer" class="btn btn-outline-secondary" :to="`/recruiter/job-offers/${jobOffer.id}`">
        Vaata ülevaadet
      </RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Tööandja vaade</p>
      <h1 class="h3 mb-1">Redigeeri tööpakkumist</h1>
      <p class="text-body-secondary mb-0">
        Uuenda pakkumise välju, halda nõudeid ja kontrolli avaldamise olekut.
      </p>
    </header>

    <ApiErrorNotice v-if="deleteOfferError" :error="deleteOfferError" show-all-messages />

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Tööpakkumine</h2>
        <p class="text-body-secondary mb-0">Muudetavad tööpakkumise väljad ja staatus.</p>
      </header>

      <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />
      <ApiErrorNotice v-if="transitionError" :error="transitionError" show-all-messages />
      <div v-if="transitionSuccessMessage" class="alert alert-success mb-0" role="status">
        {{ transitionSuccessMessage }}
      </div>

      <p v-if="isOfferLoading" class="text-body-secondary mb-0">Laen tööpakkumist...</p>
      <p v-else-if="isOfferNotFound" class="text-body-secondary mb-0">Tööpakkumist ei leitud.</p>

      <form v-else-if="jobOffer" class="d-grid gap-3" @submit.prevent="saveOffer">
        <p class="mb-0">
          <strong>Praegune staatus: </strong>
          <JobOfferStatusBadge :status="jobOffer.status" />
        </p>

        <div class="d-flex flex-wrap gap-2">
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
        </div>

        <CatalogSearchPicker
          :key="offerOccupationPickerKey"
          label="Ametikoht"
          placeholder="Otsi ametikohti"
          no-results-text="Ametikohti ei leitud."
          :disabled="isUpdatingOffer"
          :busy="isUpdatingOffer"
          :search-fn="searchOccupations"
          @select="selectOfferOccupation"
        />

        <p class="mb-0 text-break">
          <strong>Valitud ametikoht: </strong>
          <span v-if="offerForm.occupationKey">
            {{ offerForm.occupationLabel || offerForm.occupationKey }}
            <span class="d-block small text-body-secondary break-all">({{ offerForm.occupationKey }})</span>
          </span>
          <span v-else>Puudub</span>
        </p>

        <div>
          <label class="form-label" for="recruiter-offer-description">Kirjeldus</label>
          <textarea
            id="recruiter-offer-description"
            v-model="offerForm.description"
            class="form-control"
            rows="4"
            required
            :disabled="isUpdatingOffer"
          />
        </div>

        <ApiErrorNotice v-if="offerUpdateError" :error="offerUpdateError" show-all-messages />
        <div v-if="offerUpdateSuccessMessage" class="alert alert-success mb-0" role="status">
          {{ offerUpdateSuccessMessage }}
        </div>

        <div class="d-flex flex-wrap gap-2">
          <button class="btn btn-primary" type="submit" :disabled="isUpdatingOffer">
            {{ isUpdatingOffer ? "Salvestan pakkumist..." : "Salvesta pakkumine" }}
          </button>
          <button
            class="btn btn-outline-danger"
            type="button"
            :disabled="isDeletingOffer || isTransitioning"
            @click="deleteOffer"
          >
            {{ isDeletingOffer ? "Kustutan..." : "Kustuta pakkumine" }}
          </button>
        </div>
      </form>
    </section>

    <section v-if="jobOffer" class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Kompetentsid</h2>
        <p class="text-body-secondary mb-0">Lisa ja halda kompetentside prioriteete.</p>
      </header>

      <ApiErrorNotice v-if="requirementsLoadError" :error="requirementsLoadError" show-all-messages />

      <OccupationCompetencySuggestions
        :occupation-key="jobOffer.occupation_key"
        :selected-keys="existingRequirementKeys"
        :disabled="isRequirementsLoading"
        :busy="isAddingRequirement"
        label="Valitud ametikohaga seotud kompetentsid"
        waiting-text="Vali ametikoht, et näha seotud kompetentse."
        @select="addSuggestedRequirement"
      />

      <form class="d-grid gap-3" @submit.prevent="addRequirement">
        <CatalogSearchPicker
          :key="requirementPickerKey"
          label="Kompetents"
          placeholder="Otsi kompetentse"
          no-results-text="Kompetentse ei leitud."
          :disabled="isRequirementsLoading"
          :busy="isAddingRequirement"
          :search-fn="searchCompetencies"
          @select="selectRequirementCompetency"
        />

        <p class="mb-0 text-break">
          <strong>Valitud kompetents: </strong>
          <span v-if="selectedRequirementCompetency">{{ selectedRequirementCompetency.label }}</span>
          <span v-else>Puudub</span>
        </p>

        <EnumSelect
          v-model="newRequirementPriority"
          label="Prioriteet"
          :options="requirementPriorityOptions"
          :disabled="isAddingRequirement || isRequirementsLoading"
        />

        <ApiErrorNotice v-if="addRequirementError" :error="addRequirementError" show-all-messages />
        <div v-if="addRequirementSuccessMessage" class="alert alert-success mb-0" role="status">
          {{ addRequirementSuccessMessage }}
        </div>

        <button class="btn btn-primary" type="submit" :disabled="isAddingRequirement || isRequirementsLoading">
          {{ isAddingRequirement ? "Lisame kompetentsi..." : "Lisa kompetents" }}
        </button>
      </form>

      <p v-if="isRequirementsLoading" class="text-body-secondary mb-0">Laen nõudmisi...</p>
      <p v-else-if="requirementRows.length === 0" class="text-body-secondary mb-0">Nõudmisi pole veel salvestatud.</p>

      <div v-else class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th scope="col">Kompetents</th>
              <th scope="col">Prioriteet</th>
              <th scope="col">Tegevused</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in requirementRows" :key="row.id">
              <td class="text-break">{{ competencyLabel(row.competencyKey) }}</td>
              <td>
                <EnumSelect
                  v-model="row.priorityDraft"
                  label=""
                  :options="requirementPriorityOptions"
                  :disabled="row.isSaving || row.isDeleting"
                />
              </td>
              <td>
                <div class="d-flex flex-wrap gap-2">
                  <button
                    class="btn btn-outline-secondary btn-sm"
                    type="button"
                    :disabled="row.isSaving || row.isDeleting || row.priorityDraft === row.persistedPriority"
                    @click="saveRequirementPriority(row.id)"
                  >
                    {{ row.isSaving ? "Salvestame..." : "Salvesta" }}
                  </button>
                  <button
                    class="btn btn-outline-danger btn-sm"
                    type="button"
                    :disabled="row.isSaving || row.isDeleting"
                    @click="deleteRequirement(row.id)"
                  >
                    {{ row.isDeleting ? "Eemaldame..." : "Eemalda" }}
                  </button>
                </div>
                <ApiErrorNotice v-if="row.error" :error="row.error" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
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
  { value: "must_have", label: "Nõutud" },
  { value: "important", label: "Oluline" },
  { value: "nice_to_have", label: "Soovituslik" },
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

async function searchCompetencies(
  query: string,
  options: { signal?: AbortSignal } = {},
): Promise<CatalogItem[]> {
  return catalogClient.listCompetencies({ query, limit: 8 }, { signal: options.signal });
}

async function searchOccupations(
  query: string,
  options: { signal?: AbortSignal } = {},
): Promise<CatalogItem[]> {
  return catalogClient.listOccupations({ query, limit: 8 }, { signal: options.signal });
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
    return "Pealkiri pole saadaval";
  }

  return "Laadime pealkirja...";
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

    for (const item of requirements) {
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
    offerUpdateError.value = "Vali ametikoht enne tööpakkumise salvestamist.";
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
    offerUpdateSuccessMessage.value = "Mustand salvestatud.";
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
    title: "Kustuta pakkumine",
    message: "Kustuta see tööpakkumine ja kõik nõuded?",
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
    message: "Avalda see pakkumine nüüd? Pärast avaldamist muutub see tööotsijatele nähtavaks.",
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
    hydrateOfferForm(updatedOffer);
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
    message: "Arhiveeri see pakkumine? Arhiveeritud pakkumised ei ole enam tööotsijatele nähtavad.",
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
    hydrateOfferForm(updatedOffer);
    transitionSuccessMessage.value = "Tööpakkumine arhiveeritud.";
  } catch (error) {
    transitionError.value = error;
  } finally {
    isTransitioning.value = false;
  }
}

async function addRequirement(): Promise<void> {
  if (!selectedRequirementCompetency.value) {
    addRequirementError.value = "Vali kompetents enne lisamist.";
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
    addRequirementError.value = "See kompetents on juba valitud.";
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

    addRequirementSuccessMessage.value = "Kompetents lisatud.";
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
