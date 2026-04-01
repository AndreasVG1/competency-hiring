<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Company and Job Offer Setup</h1>
        <p class="content">Manage your company profile, draft offers, and competency requirements.</p>
      </header>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Recruiter Profile</h2>
          <p>Keep your company contact details current.</p>
        </header>

        <p v-if="isFirstTimeProfile" class="section-note">
          No recruiter profile found yet. Fill in details and save to create one.
        </p>

        <ApiErrorNotice
          v-if="profileLoadError"
          :error="profileLoadError"
          show-all-messages
        />

        <form class="recruiter-form" @submit.prevent="saveProfile">
          <label class="form-field">
            <span>Company name</span>
            <input
              v-model="profileForm.companyName"
              type="text"
              maxlength="255"
              required
              :disabled="isProfileLoading || isProfileSaving"
            />
          </label>

          <label class="form-field">
            <span>Contact name</span>
            <input
              v-model="profileForm.contactName"
              type="text"
              maxlength="255"
              required
              :disabled="isProfileLoading || isProfileSaving"
            />
          </label>

          <ApiErrorNotice
            v-if="profileSaveError"
            :error="profileSaveError"
            show-all-messages
          />
          <p v-if="profileSaveSuccessMessage" class="form-success">{{ profileSaveSuccessMessage }}</p>

          <button class="button-primary" type="submit" :disabled="isProfileLoading || isProfileSaving">
            {{ isProfileSaving ? "Saving profile..." : "Save profile" }}
          </button>
        </form>
      </section>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Job Offers</h2>
          <p>Create draft offers and select one to edit requirements.</p>
        </header>

        <ApiErrorNotice
          v-if="jobOffersLoadError"
          :error="jobOffersLoadError"
          show-all-messages
        />

        <form class="recruiter-form" @submit.prevent="createJobOffer">
          <CatalogSearchPicker
            :key="createOfferOccupationPickerKey"
            label="Occupation"
            placeholder="Search occupations"
            no-results-text="No occupations found."
            :disabled="isJobOffersLoading"
            :busy="isCreatingJobOffer"
            :search-fn="searchOccupations"
            @select="selectCreateOfferOccupation"
          />

          <p class="selected-item">
            <strong>Selected occupation:</strong>
            <span v-if="selectedCreateOfferOccupation">
              {{ selectedCreateOfferOccupation.label }}
              <small>({{ selectedCreateOfferOccupation.key }})</small>
            </span>
            <span v-else>None</span>
          </p>

          <button
            class="button-secondary"
            type="button"
            :disabled="!selectedCreateOfferOccupation || isJobOffersLoading || isCreatingJobOffer"
            @click="clearCreateOfferOccupation"
          >
            Clear occupation
          </button>

          <label class="form-field">
            <span>Description</span>
            <textarea
              v-model="createOfferForm.description"
              rows="3"
              required
              :disabled="isJobOffersLoading || isCreatingJobOffer"
            />
          </label>

          <ApiErrorNotice
            v-if="createJobOfferError"
            :error="createJobOfferError"
            show-all-messages
          />
          <p v-if="createJobOfferSuccessMessage" class="form-success">{{ createJobOfferSuccessMessage }}</p>

          <button
            class="button-primary"
            type="submit"
            :disabled="isJobOffersLoading || isCreatingJobOffer || !selectedCreateOfferOccupation"
          >
            {{ isCreatingJobOffer ? "Creating offer..." : "Create draft offer" }}
          </button>
        </form>

        <div v-if="isJobOffersLoading" class="table-note">Loading job offers...</div>
        <div v-else-if="jobOffers.length === 0" class="table-note">No draft offers yet.</div>

        <ul v-else class="offer-list">
          <li v-for="offer in jobOffers" :key="offer.id">
            <button
              class="offer-select"
              type="button"
              :class="{ 'offer-select-active': offer.id === selectedOfferId }"
              :disabled="isUpdatingSelectedOffer"
              @click="selectJobOffer(offer.id)"
            >
              <span>
                <strong>{{ offer.title }}</strong>
                <small>{{ offer.status }}</small>
              </span>
              <code>#{{ offer.id }}</code>
            </button>
          </li>
        </ul>

        <form v-if="selectedOffer" class="recruiter-form" @submit.prevent="saveSelectedOffer">
          <header class="subsection-header">
            <h3>Edit Selected Offer</h3>
            <p>
              Editing <strong>{{ selectedOffer.title }}</strong>
              <small>(#{{ selectedOffer.id }})</small>
            </p>
          </header>

          <label class="form-field">
            <span>Title</span>
            <input
              v-model="selectedOfferForm.title"
              type="text"
              maxlength="255"
              required
              :disabled="isUpdatingSelectedOffer"
            />
          </label>

          <label class="form-field">
            <span>Description</span>
            <textarea
              v-model="selectedOfferForm.description"
              rows="3"
              required
              :disabled="isUpdatingSelectedOffer"
            />
          </label>

          <ApiErrorNotice
            v-if="selectedOfferUpdateError"
            :error="selectedOfferUpdateError"
            show-all-messages
          />
          <p v-if="selectedOfferUpdateSuccessMessage" class="form-success">
            {{ selectedOfferUpdateSuccessMessage }}
          </p>

          <button class="button-primary" type="submit" :disabled="isUpdatingSelectedOffer">
            {{ isUpdatingSelectedOffer ? "Saving offer..." : "Save offer" }}
          </button>
        </form>

        <p v-else class="section-note">Select a draft offer to edit.</p>
      </section>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Requirements for Selected Offer</h2>
          <p>Add and maintain competency priorities for the active draft offer.</p>
        </header>

        <p v-if="!selectedOffer" class="section-note">Select an offer in the Job Offers section first.</p>

        <template v-else>
          <p class="selected-item">
            <strong>Selected offer:</strong>
            {{ selectedOffer.title }} <small>(#{{ selectedOffer.id }})</small>
          </p>

          <ApiErrorNotice
            v-if="requirementsLoadError"
            :error="requirementsLoadError"
            show-all-messages
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

            <ApiErrorNotice
              v-if="addRequirementError"
              :error="addRequirementError"
              show-all-messages
            />
            <p v-if="addRequirementSuccessMessage" class="form-success">
              {{ addRequirementSuccessMessage }}
            </p>

            <button
              class="button-primary"
              type="submit"
              :disabled="isAddingRequirement || isRequirementsLoading"
            >
              {{ isAddingRequirement ? "Adding requirement..." : "Add requirement" }}
            </button>
          </form>

          <div v-if="isRequirementsLoading" class="table-note">Loading requirements...</div>
          <div v-else-if="requirementRows.length === 0" class="table-note">
            No requirements saved for this offer yet.
          </div>

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
        </template>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import { ApiClientError, catalogClient, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import CatalogSearchPicker from "../../components/CatalogSearchPicker.vue";
import EnumSelect from "../../components/EnumSelect.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import type {
  CatalogItem,
  JobOfferRequirementResponse,
  JobOfferResponse,
  RecruiterProfileResponse,
  RequirementPriority,
} from "../../types/domain";

interface RecruiterProfileFormState {
  companyName: string;
  contactName: string;
}

interface JobOfferFormState {
  title: string;
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

const requirementPriorityOptions: { value: RequirementPriority; label: string }[] = [
  { value: "must_have", label: "Must have" },
  { value: "important", label: "Important" },
  { value: "nice_to_have", label: "Nice to have" },
];

const profileForm = reactive<RecruiterProfileFormState>({
  companyName: "",
  contactName: "",
});

const createOfferForm = reactive<JobOfferFormState>({
  title: "",
  description: "",
});

const selectedOfferForm = reactive<JobOfferFormState>({
  title: "",
  description: "",
});

const labelCache = useCatalogLabelCache();

const isFirstTimeProfile = ref(false);
const isProfileLoading = ref(true);
const isProfileSaving = ref(false);
const profileLoadError = ref<unknown | null>(null);
const profileSaveError = ref<unknown | null>(null);
const profileSaveSuccessMessage = ref<string | null>(null);

const jobOffers = ref<JobOfferResponse[]>([]);
const isJobOffersLoading = ref(true);
const jobOffersLoadError = ref<unknown | null>(null);
const selectedOfferId = ref<number | null>(null);

const isCreatingJobOffer = ref(false);
const createJobOfferError = ref<unknown | null>(null);
const createJobOfferSuccessMessage = ref<string | null>(null);
const selectedCreateOfferOccupation = ref<CatalogItem | null>(null);
const createOfferOccupationPickerKey = ref(0);

const isUpdatingSelectedOffer = ref(false);
const selectedOfferUpdateError = ref<unknown | null>(null);
const selectedOfferUpdateSuccessMessage = ref<string | null>(null);

const requirementRows = ref<RequirementRowState[]>([]);
const isRequirementsLoading = ref(false);
const requirementsLoadError = ref<unknown | null>(null);

const selectedRequirementCompetency = ref<CatalogItem | null>(null);
const newRequirementPriority = ref<RequirementPriority>("must_have");
const isAddingRequirement = ref(false);
const addRequirementError = ref<unknown | null>(null);
const addRequirementSuccessMessage = ref<string | null>(null);
const requirementPickerKey = ref(0);
let requirementsRequestCounter = 0;

const selectedOffer = computed<JobOfferResponse | null>(() => {
  if (selectedOfferId.value === null) {
    return null;
  }
  return jobOffers.value.find((offer) => offer.id === selectedOfferId.value) ?? null;
});

function sortOffersDescending(offers: JobOfferResponse[]): JobOfferResponse[] {
  return [...offers].sort((a, b) => {
    const timeDelta = Date.parse(b.created_at) - Date.parse(a.created_at);
    if (timeDelta !== 0) {
      return timeDelta;
    }
    return b.id - a.id;
  });
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

function hydrateProfileForm(profile: RecruiterProfileResponse): void {
  profileForm.companyName = profile.company_name;
  profileForm.contactName = profile.contact_name;
}

function hydrateSelectedOfferForm(offer: JobOfferResponse): void {
  selectedOfferForm.title = offer.title;
  selectedOfferForm.description = offer.description;
}

function selectJobOffer(offerId: number): void {
  if (selectedOfferId.value === offerId) {
    return;
  }

  selectedOfferId.value = offerId;
  selectedOfferUpdateError.value = null;
  selectedOfferUpdateSuccessMessage.value = null;
}

function selectRequirementCompetency(item: CatalogItem): void {
  selectedRequirementCompetency.value = item;
  addRequirementError.value = null;
  addRequirementSuccessMessage.value = null;
}

async function searchCompetencies(query: string): Promise<CatalogItem[]> {
  return catalogClient.listCompetencies({ query, limit: 8 });
}

async function searchOccupations(query: string): Promise<CatalogItem[]> {
  return catalogClient.listOccupations({ query, limit: 8 });
}

function selectCreateOfferOccupation(item: CatalogItem): void {
  selectedCreateOfferOccupation.value = item;
  createOfferForm.title = item.label;
  createJobOfferError.value = null;
  createJobOfferSuccessMessage.value = null;
}

function clearCreateOfferOccupation(): void {
  selectedCreateOfferOccupation.value = null;
  createOfferForm.title = "";
  createJobOfferError.value = null;
  createJobOfferSuccessMessage.value = null;
  createOfferOccupationPickerKey.value += 1;
}

async function loadProfile(): Promise<void> {
  isProfileLoading.value = true;
  isFirstTimeProfile.value = false;
  profileLoadError.value = null;

  try {
    const profile = await recruiterClient.getProfile();
    hydrateProfileForm(profile);
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isFirstTimeProfile.value = true;
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

    if (
      selectedOfferId.value !== null &&
      !jobOffers.value.some((offer) => offer.id === selectedOfferId.value)
    ) {
      selectedOfferId.value = null;
    }
  } catch (error) {
    jobOffersLoadError.value = error;
  } finally {
    isJobOffersLoading.value = false;
  }
}

async function loadRequirementsForSelectedOffer(offerId: number): Promise<void> {
  const requestId = requirementsRequestCounter + 1;
  requirementsRequestCounter = requestId;

  isRequirementsLoading.value = true;
  requirementsLoadError.value = null;
  requirementRows.value = [];

  try {
    const requirements = await recruiterClient.listRequirements(offerId);
    if (requestId !== requirementsRequestCounter || selectedOfferId.value !== offerId) {
      return;
    }
    requirementRows.value = requirements.map(mapRequirementToRow);
    void labelCache.hydrateKeys(requirements.map((item) => item.competency_key));
  } catch (error) {
    if (requestId !== requirementsRequestCounter || selectedOfferId.value !== offerId) {
      return;
    }
    requirementsLoadError.value = error;
  } finally {
    if (requestId === requirementsRequestCounter && selectedOfferId.value === offerId) {
      isRequirementsLoading.value = false;
    }
  }
}

async function saveProfile(): Promise<void> {
  if (isProfileLoading.value || isProfileSaving.value) {
    return;
  }

  isProfileSaving.value = true;
  profileSaveError.value = null;
  profileSaveSuccessMessage.value = null;

  try {
    const profile = await recruiterClient.upsertProfile({
      company_name: profileForm.companyName.trim(),
      contact_name: profileForm.contactName.trim(),
    });

    hydrateProfileForm(profile);
    isFirstTimeProfile.value = false;
    profileSaveSuccessMessage.value = "Recruiter profile saved.";
  } catch (error) {
    profileSaveError.value = error;
  } finally {
    isProfileSaving.value = false;
  }
}

async function createJobOffer(): Promise<void> {
  if (isJobOffersLoading.value || isCreatingJobOffer.value) {
    return;
  }

  if (!selectedCreateOfferOccupation.value) {
    createJobOfferError.value = "Choose an occupation before creating the offer.";
    return;
  }

  isCreatingJobOffer.value = true;
  createJobOfferError.value = null;
  createJobOfferSuccessMessage.value = null;

  try {
    const created = await recruiterClient.createJobOffer({
      title: createOfferForm.title.trim(),
      description: createOfferForm.description.trim(),
    });

    jobOffers.value = [created, ...jobOffers.value.filter((offer) => offer.id !== created.id)];
    selectedOfferId.value = created.id;
    createOfferForm.title = "";
    createOfferForm.description = "";
    selectedCreateOfferOccupation.value = null;
    createOfferOccupationPickerKey.value += 1;
    createJobOfferSuccessMessage.value = "Draft offer created.";
  } catch (error) {
    createJobOfferError.value = error;
  } finally {
    isCreatingJobOffer.value = false;
  }
}

async function saveSelectedOffer(): Promise<void> {
  const offer = selectedOffer.value;
  if (!offer || isUpdatingSelectedOffer.value) {
    return;
  }

  isUpdatingSelectedOffer.value = true;
  selectedOfferUpdateError.value = null;
  selectedOfferUpdateSuccessMessage.value = null;

  try {
    const updated = await recruiterClient.updateJobOffer(offer.id, {
      title: selectedOfferForm.title.trim(),
      description: selectedOfferForm.description.trim(),
    });

    jobOffers.value = sortOffersDescending(
      jobOffers.value.map((candidate) => (candidate.id === updated.id ? updated : candidate)),
    );
    hydrateSelectedOfferForm(updated);
    selectedOfferUpdateSuccessMessage.value = "Draft offer saved.";
  } catch (error) {
    selectedOfferUpdateError.value = error;
  } finally {
    isUpdatingSelectedOffer.value = false;
  }
}

async function addRequirement(): Promise<void> {
  const offer = selectedOffer.value;
  if (!offer || isRequirementsLoading.value || isAddingRequirement.value) {
    return;
  }

  addRequirementError.value = null;
  addRequirementSuccessMessage.value = null;

  if (!selectedRequirementCompetency.value) {
    addRequirementError.value = "Choose a competency before adding.";
    return;
  }

  const selectedKey = selectedRequirementCompetency.value.key;
  if (requirementRows.value.some((row) => row.competencyKey === selectedKey)) {
    addRequirementError.value = "This competency is already a requirement for the selected offer.";
    return;
  }

  isAddingRequirement.value = true;

  try {
    const created = await recruiterClient.addRequirement(offer.id, {
      competency_key: selectedKey,
      priority: newRequirementPriority.value,
    });

    requirementRows.value = [mapRequirementToRow(created), ...requirementRows.value];
    labelCache.setLabel(selectedRequirementCompetency.value.key, selectedRequirementCompetency.value.label);

    selectedRequirementCompetency.value = null;
    newRequirementPriority.value = "must_have";
    requirementPickerKey.value += 1;
    addRequirementSuccessMessage.value = "Requirement added.";
  } catch (error) {
    addRequirementError.value = error;
  } finally {
    isAddingRequirement.value = false;
  }
}

async function saveRequirementPriority(rowId: number): Promise<void> {
  const offer = selectedOffer.value;
  const row = requirementRows.value.find((candidate) => candidate.id === rowId);
  if (!offer || !row || row.isSaving || row.isDeleting || row.priorityDraft === row.persistedPriority) {
    return;
  }

  row.isSaving = true;
  row.error = null;

  try {
    const updated = await recruiterClient.updateRequirement(offer.id, row.id, {
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
  const offer = selectedOffer.value;
  const row = requirementRows.value.find((candidate) => candidate.id === rowId);
  if (!offer || !row || row.isSaving || row.isDeleting) {
    return;
  }

  row.isDeleting = true;
  row.error = null;

  try {
    await recruiterClient.deleteRequirement(offer.id, row.id);
    requirementRows.value = requirementRows.value.filter((candidate) => candidate.id !== row.id);
  } catch (error) {
    row.error = error;
    row.isDeleting = false;
  }
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

watch(selectedOfferId, (offerId) => {
  selectedRequirementCompetency.value = null;
  newRequirementPriority.value = "must_have";
  addRequirementError.value = null;
  addRequirementSuccessMessage.value = null;
  requirementPickerKey.value += 1;

  if (offerId === null) {
    requirementsRequestCounter += 1;
    requirementRows.value = [];
    isRequirementsLoading.value = false;
    requirementsLoadError.value = null;
    selectedOfferForm.title = "";
    selectedOfferForm.description = "";
    return;
  }

  const offer = selectedOffer.value;
  if (offer) {
    hydrateSelectedOfferForm(offer);
  }

  void loadRequirementsForSelectedOffer(offerId);
}, { immediate: true });

onMounted(async () => {
  await Promise.all([loadProfile(), loadJobOffers()]);
});
</script>
