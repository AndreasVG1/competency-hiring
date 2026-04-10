<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/seeker">Back to profile</RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Job Seeker Area</p>
      <h1 class="h3 mb-1">Edit Profile</h1>
      <p class="text-body-secondary mb-0">Update your private profile and competency data.</p>
    </header>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Profile</h2>
        <p class="text-body-secondary mb-0">
          Keep your core information updated before running matching analysis.
        </p>
      </header>

      <p v-if="isFirstTimeProfile" class="text-body-secondary mb-0">
        No profile found yet. Fill in your details and save to create one.
      </p>

      <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

      <form class="d-grid gap-3" @submit.prevent="saveProfile">
        <div>
          <label class="form-label" for="seeker-full-name">Full name</label>
          <input
            id="seeker-full-name"
            v-model="profileForm.fullName"
            class="form-control"
            type="text"
            maxlength="255"
            required
            :disabled="isProfileLoading || isProfileSaving"
          />
        </div>

        <div>
          <label class="form-label" for="seeker-summary">Summary</label>
          <textarea
            id="seeker-summary"
            v-model="profileForm.summary"
            class="form-control"
            rows="3"
            :disabled="isProfileLoading || isProfileSaving"
          />
        </div>

        <div>
          <label class="form-label" for="seeker-location">Location</label>
          <input
            id="seeker-location"
            v-model="profileForm.location"
            class="form-control"
            type="text"
            maxlength="255"
            :disabled="isProfileLoading || isProfileSaving"
          />
        </div>

        <CatalogSearchPicker
          label="Occupation"
          placeholder="Search occupations"
          no-results-text="No occupations found."
          :disabled="isProfileLoading"
          :busy="isProfileSaving"
          :search-fn="searchOccupations"
          @select="selectOccupation"
        />

        <p class="mb-0 text-break">
          <strong>Selected occupation:</strong>
          <span v-if="profileForm.occupationKey">
            {{ selectedOccupationLabel || profileForm.occupationKey }}
            <span class="d-block small text-body-secondary break-all">({{ profileForm.occupationKey }})</span>
          </span>
          <span v-else>None</span>
        </p>

        <div class="d-flex flex-wrap gap-2">
          <button
            class="btn btn-outline-secondary"
            type="button"
            :disabled="!profileForm.occupationKey || isProfileLoading || isProfileSaving"
            @click="clearOccupation"
          >
            Clear occupation
          </button>
        </div>

        <ApiErrorNotice v-if="profileSaveError" :error="profileSaveError" show-all-messages />
        <div v-if="profileSaveSuccessMessage" class="alert alert-success mb-0" role="status">
          {{ profileSaveSuccessMessage }}
        </div>

        <button class="btn btn-primary" type="submit" :disabled="isProfileLoading || isProfileSaving">
          {{ isProfileSaving ? "Saving profile..." : "Save profile" }}
        </button>
      </form>
    </section>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Competencies</h2>
        <p class="text-body-secondary mb-0">Add competencies and keep levels current.</p>
      </header>

      <ApiErrorNotice v-if="competenciesLoadError" :error="competenciesLoadError" show-all-messages />

      <OccupationCompetencySuggestions
        :occupation-key="profileForm.occupationKey"
        :selected-keys="existingCompetencyKeys"
        :disabled="isCompetenciesLoading"
        :busy="isAddingCompetency"
        label="Competencies related to selected occupation"
        waiting-text="Select an occupation in Profile to see related competencies."
        @select="addSuggestedCompetency"
      />

      <form class="d-grid gap-3" @submit.prevent="addCompetency">
        <CatalogSearchPicker
          :key="competencyPickerKey"
          label="Competency"
          placeholder="Search competencies"
          no-results-text="No competencies found."
          :disabled="isCompetenciesLoading"
          :busy="isAddingCompetency"
          :search-fn="searchCompetencies"
          @select="selectCompetency"
        />

        <p class="mb-0 text-break">
          <strong>Selected competency:</strong>
          <span v-if="selectedCompetency">{{ selectedCompetency.label }}</span>
          <span v-else>None</span>
        </p>

        <EnumSelect
          v-model="newCompetencyLevel"
          label="Level"
          :options="competencyLevelOptions"
          :disabled="isAddingCompetency || isCompetenciesLoading"
        />

        <ApiErrorNotice v-if="addCompetencyError" :error="addCompetencyError" show-all-messages />
        <div v-if="addCompetencySuccessMessage" class="alert alert-success mb-0" role="status">
          {{ addCompetencySuccessMessage }}
        </div>

        <button class="btn btn-primary" type="submit" :disabled="isAddingCompetency || isCompetenciesLoading">
          {{ isAddingCompetency ? "Adding competency..." : "Add competency" }}
        </button>
      </form>

      <p v-if="isCompetenciesLoading" class="text-body-secondary mb-0">Loading competencies...</p>
      <p v-else-if="competencyRows.length === 0" class="text-body-secondary mb-0">No competencies saved yet.</p>

      <div v-else class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th scope="col">Competency</th>
              <th scope="col">Level</th>
              <th scope="col">Context</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in competencyRows" :key="row.id">
              <td class="text-break">{{ competencyLabel(row.competencyKey) }}</td>
              <td>
                <EnumSelect
                  v-model="row.levelDraft"
                  label=""
                  :options="competencyLevelOptions"
                  :disabled="row.isSaving || row.isDeleting"
                />
              </td>
              <td>
                <button
                  v-if="indicatorCount(row.competencyKey) > 0"
                  type="button"
                  class="btn btn-outline-secondary btn-sm"
                  @click="openIndicators(row.competencyKey)"
                >
                  View indicators
                </button>
              </td>
              <td>
                <div class="d-flex flex-wrap gap-2">
                  <button
                    class="btn btn-outline-secondary btn-sm"
                    type="button"
                    :disabled="row.isSaving || row.isDeleting || row.levelDraft === row.persistedLevel"
                    @click="saveCompetencyLevel(row.id)"
                  >
                    {{ row.isSaving ? "Saving..." : "Save" }}
                  </button>
                  <button
                    class="btn btn-outline-danger btn-sm"
                    type="button"
                    :disabled="row.isSaving || row.isDeleting"
                    @click="deleteCompetency(row.id)"
                  >
                    {{ row.isDeleting ? "Removing..." : "Remove" }}
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

  <ActivityIndicatorsOverlay
    :competency-key="overlayCompetencyKey"
    :indicators="activeIndicators"
    :loading="isOverlayLoading"
    :label-resolver="competencyLabel"
    title-id="seeker-edit-indicators-title"
    @close="closeIndicators"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { ApiClientError, catalogClient, seekerClient } from "../../api";
import ActivityIndicatorsOverlay from "../../components/ActivityIndicatorsOverlay.vue";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import CatalogSearchPicker from "../../components/CatalogSearchPicker.vue";
import EnumSelect from "../../components/EnumSelect.vue";
import OccupationCompetencySuggestions from "../../components/OccupationCompetencySuggestions.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import type {
  CatalogItem,
  CompetencyLevel,
  SeekerCompetencyResponse,
  SeekerProfileResponse,
} from "../../types/domain";

interface ProfileFormState {
  fullName: string;
  summary: string;
  location: string;
  occupationKey: string | null;
}

interface CompetencyRowState {
  id: number;
  competencyKey: string;
  levelDraft: CompetencyLevel;
  persistedLevel: CompetencyLevel;
  isSaving: boolean;
  isDeleting: boolean;
  error: unknown | null;
}

const competencyLevelOptions: { value: CompetencyLevel; label: string }[] = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const profileForm = reactive<ProfileFormState>({
  fullName: "",
  summary: "",
  location: "",
  occupationKey: null,
});

const labelCache = useCatalogLabelCache();

const isFirstTimeProfile = ref(false);
const isProfileLoading = ref(true);
const isProfileSaving = ref(false);
const selectedOccupationLabel = ref<string | null>(null);
const profileLoadError = ref<unknown | null>(null);
const profileSaveError = ref<unknown | null>(null);
const profileSaveSuccessMessage = ref<string | null>(null);

const isCompetenciesLoading = ref(true);
const competenciesLoadError = ref<unknown | null>(null);
const competencyRows = ref<CompetencyRowState[]>([]);

const selectedCompetency = ref<CatalogItem | null>(null);
const newCompetencyLevel = ref<CompetencyLevel>("beginner");
const isAddingCompetency = ref(false);
const addCompetencyError = ref<unknown | null>(null);
const addCompetencySuccessMessage = ref<string | null>(null);
const competencyPickerKey = ref(0);
const overlayCompetencyKey = ref<string | null>(null);
const isOverlayLoading = ref(false);
const existingCompetencyKeys = computed(() => competencyRows.value.map((row) => row.competencyKey));
const activeIndicators = computed(() => {
  if (overlayCompetencyKey.value === null) {
    return [];
  }
  return labelCache.getActivityIndicators(overlayCompetencyKey.value) ?? [];
});

function mapResponseToRow(response: SeekerCompetencyResponse): CompetencyRowState {
  return {
    id: response.id,
    competencyKey: response.competency_key,
    levelDraft: response.level,
    persistedLevel: response.level,
    isSaving: false,
    isDeleting: false,
    error: null,
  };
}

function hydrateProfileForm(profile: SeekerProfileResponse): void {
  profileForm.fullName = profile.full_name;
  profileForm.summary = profile.summary ?? "";
  profileForm.location = profile.location ?? "";
  profileForm.occupationKey = profile.occupation_key;
}

function toOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

async function searchOccupations(
  query: string,
  options: { signal?: AbortSignal } = {},
): Promise<CatalogItem[]> {
  return catalogClient.listOccupations({ query, limit: 8 }, { signal: options.signal });
}

async function searchCompetencies(
  query: string,
  options: { signal?: AbortSignal } = {},
): Promise<CatalogItem[]> {
  return catalogClient.listCompetencies({ query, limit: 8 }, { signal: options.signal });
}

function selectOccupation(item: CatalogItem): void {
  profileForm.occupationKey = item.key;
  selectedOccupationLabel.value = item.label;
  profileSaveSuccessMessage.value = null;
}

function clearOccupation(): void {
  profileForm.occupationKey = null;
  selectedOccupationLabel.value = null;
  profileSaveSuccessMessage.value = null;
}

function selectCompetency(item: CatalogItem): void {
  selectedCompetency.value = item;
  addCompetencyError.value = null;
  addCompetencySuccessMessage.value = null;
}

function indicatorCount(competencyKey: string): number {
  return labelCache.getActivityIndicatorCount(competencyKey);
}

function openIndicators(competencyKey: string): void {
  overlayCompetencyKey.value = competencyKey;
  isOverlayLoading.value = true;
  void (async () => {
    try {
      await labelCache.ensureActivityIndicators(competencyKey);
    } finally {
      if (overlayCompetencyKey.value === competencyKey) {
        isOverlayLoading.value = false;
      }
    }
  })();
}

function closeIndicators(): void {
  overlayCompetencyKey.value = null;
  isOverlayLoading.value = false;
}

function addSuggestedCompetency(item: CatalogItem): void {
  void addCompetencyFromItem(item, { resetPicker: false });
}

async function loadProfile(): Promise<void> {
  isProfileLoading.value = true;
  isFirstTimeProfile.value = false;
  profileLoadError.value = null;

  try {
    const profile = await seekerClient.getProfile();
    hydrateProfileForm(profile);

    if (profile.occupation_key) {
      try {
        const occupation = await catalogClient.getOccupation(profile.occupation_key);
        selectedOccupationLabel.value = occupation.label;
      } catch (_error) {
        selectedOccupationLabel.value = null;
      }
    }
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isFirstTimeProfile.value = true;
      selectedOccupationLabel.value = null;
      return;
    }

    profileLoadError.value = error;
  } finally {
    isProfileLoading.value = false;
  }
}

async function loadCompetencies(): Promise<void> {
  isCompetenciesLoading.value = true;
  competenciesLoadError.value = null;

  try {
    const competencies = await seekerClient.listCompetencies();
    competencyRows.value = competencies.map(mapResponseToRow);

    for (const item of competencies) {
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

    void labelCache.hydrateKeys(competencies.map((item) => item.competency_key));
  } catch (error) {
    competenciesLoadError.value = error;
  } finally {
    isCompetenciesLoading.value = false;
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
    const profile = await seekerClient.upsertProfile({
      full_name: profileForm.fullName.trim(),
      summary: toOptionalText(profileForm.summary),
      location: toOptionalText(profileForm.location),
      occupation_key: profileForm.occupationKey,
    });

    hydrateProfileForm(profile);
    isFirstTimeProfile.value = false;
    profileSaveSuccessMessage.value = "Profile saved.";
  } catch (error) {
    profileSaveError.value = error;
  } finally {
    isProfileSaving.value = false;
  }
}

async function addCompetency(): Promise<void> {
  if (!selectedCompetency.value) {
    addCompetencyError.value = "Choose a competency before adding.";
    return;
  }

  await addCompetencyFromItem(selectedCompetency.value, { resetPicker: true });
}

async function addCompetencyFromItem(
  item: CatalogItem,
  options: { resetPicker: boolean },
): Promise<void> {
  if (isAddingCompetency.value || isCompetenciesLoading.value) {
    return;
  }

  addCompetencyError.value = null;
  addCompetencySuccessMessage.value = null;

  if (competencyRows.value.some((row) => row.competencyKey === item.key)) {
    addCompetencyError.value = "This competency is already in your profile.";
    return;
  }

  isAddingCompetency.value = true;

  try {
    const created = await seekerClient.createCompetency({
      competency_key: item.key,
      level: newCompetencyLevel.value,
    });

    competencyRows.value = [mapResponseToRow(created), ...competencyRows.value];
    labelCache.setLabel(item.key, item.label);

    if (options.resetPicker) {
      selectedCompetency.value = null;
      newCompetencyLevel.value = "beginner";
      competencyPickerKey.value += 1;
    }

    addCompetencySuccessMessage.value = "Competency added.";
  } catch (error) {
    addCompetencyError.value = error;
  } finally {
    isAddingCompetency.value = false;
  }
}

async function saveCompetencyLevel(rowId: number): Promise<void> {
  const row = competencyRows.value.find((candidate) => candidate.id === rowId);
  if (!row || row.isSaving || row.isDeleting || row.levelDraft === row.persistedLevel) {
    return;
  }

  row.isSaving = true;
  row.error = null;

  try {
    const updated = await seekerClient.updateCompetency(row.id, {
      level: row.levelDraft,
    });

    row.persistedLevel = updated.level;
    row.levelDraft = updated.level;
  } catch (error) {
    row.error = error;
  } finally {
    row.isSaving = false;
  }
}

async function deleteCompetency(rowId: number): Promise<void> {
  const row = competencyRows.value.find((candidate) => candidate.id === rowId);
  if (!row || row.isSaving || row.isDeleting) {
    return;
  }

  row.isDeleting = true;
  row.error = null;

  try {
    await seekerClient.deleteCompetency(row.id);
    competencyRows.value = competencyRows.value.filter((candidate) => candidate.id !== row.id);
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

onMounted(async () => {
  await Promise.all([loadProfile(), loadCompetencies()]);
});
</script>
