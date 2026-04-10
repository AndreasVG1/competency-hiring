<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-primary" to="/seeker/job-offers">Browse published job offers</RouterLink>
      <RouterLink class="btn btn-outline-secondary" to="/seeker/edit">Edit profile</RouterLink>
    </PageActionsBar>

    <header>
      <h1 class="h3 mb-1">Profile Overview</h1>
      <p class="text-body-secondary mb-0">Review what is currently saved in your private profile.</p>
    </header>

    <ApiErrorNotice v-if="deleteProfileError" :error="deleteProfileError" show-all-messages />

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-0">Profile</h2>
      </header>

      <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

      <p v-if="isProfileLoading" class="text-body-secondary mb-0">Loading profile...</p>

      <template v-else-if="isFirstTimeProfile || !profile">
        <p class="text-body-secondary mb-0">No profile found yet.</p>
        <div>
          <RouterLink class="btn btn-primary" to="/seeker/edit">Create profile</RouterLink>
        </div>
      </template>

      <template v-else>
        <dl class="row mb-0">
          <dt class="col-sm-3 text-body-secondary">Full name</dt>
          <dd class="col-sm-9 text-break">{{ profile.full_name }}</dd>
          <dt class="col-sm-3 text-body-secondary">Summary</dt>
          <dd class="col-sm-9 text-break">{{ profile.summary || "Not set" }}</dd>
          <dt class="col-sm-3 text-body-secondary">Location</dt>
          <dd class="col-sm-9 text-break">{{ profile.location || "Not set" }}</dd>
          <dt class="col-sm-3 text-body-secondary">Occupation</dt>
          <dd class="col-sm-9 text-break">
            <span v-if="profile.occupation_key">
              {{ selectedOccupationLabel || profile.occupation_key }}
            </span>
            <span v-else>Not set</span>
          </dd>
        </dl>

        <div class="d-flex flex-wrap gap-2">
          <RouterLink class="btn btn-outline-secondary" to="/seeker/edit">Edit profile</RouterLink>
          <button class="btn btn-outline-danger" type="button" :disabled="isDeletingProfile" @click="deleteProfile">
            {{ isDeletingProfile ? "Deleting..." : "Delete profile" }}
          </button>
        </div>
      </template>
    </section>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-0">Competencies</h2>
      </header>

      <ApiErrorNotice v-if="competenciesLoadError" :error="competenciesLoadError" show-all-messages />

      <p v-if="isCompetenciesLoading" class="text-body-secondary mb-0">Loading competencies...</p>
      <CompetencyLevelTable
        v-else
        :rows="competencyTableRows"
        empty-text="No competencies saved yet."
        :label-resolver="competencyLabel"
        :level-formatter="formatLevel"
        :activity-indicator-resolver="activityIndicatorsFor"
        :activity-indicator-count-resolver="activityIndicatorCountFor"
        :activity-indicator-loader="loadActivityIndicators"
        overlay-title-id="seeker-profile-indicators-title"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiClientError, catalogClient, seekerClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import CompetencyLevelTable from "../../components/CompetencyLevelTable.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useConfirmDialog } from "../../composables/useConfirmDialog";
import type { CompetencyLevel, SeekerCompetencyResponse, SeekerProfileResponse } from "../../types/domain";

const { confirm } = useConfirmDialog();
const labelCache = useCatalogLabelCache();

const profile = ref<SeekerProfileResponse | null>(null);
const competencies = ref<SeekerCompetencyResponse[]>([]);

const isFirstTimeProfile = ref(false);
const isProfileLoading = ref(true);
const isCompetenciesLoading = ref(true);
const isDeletingProfile = ref(false);

const selectedOccupationLabel = ref<string | null>(null);

const profileLoadError = ref<unknown | null>(null);
const competenciesLoadError = ref<unknown | null>(null);
const deleteProfileError = ref<unknown | null>(null);

const competencyTableRows = computed(() =>
  competencies.value.map((item) => ({
    id: item.id,
    competency_key: item.competency_key,
    level: item.level,
  })),
);

function formatLevel(level: string): string {
  if (level === "beginner") {
    return "Beginner";
  }
  if (level === "intermediate") {
    return "Intermediate";
  }
  return "Advanced";
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

async function loadProfile(): Promise<void> {
  isProfileLoading.value = true;
  isFirstTimeProfile.value = false;
  profileLoadError.value = null;
  selectedOccupationLabel.value = null;

  try {
    const loadedProfile = await seekerClient.getProfile();
    profile.value = loadedProfile;

    if (loadedProfile.occupation_key) {
      try {
        const occupation = await catalogClient.getOccupation(loadedProfile.occupation_key);
        selectedOccupationLabel.value = occupation.label;
      } catch {
        selectedOccupationLabel.value = null;
      }
    }
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isFirstTimeProfile.value = true;
      profile.value = null;
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
    const loadedCompetencies = await seekerClient.listCompetencies();
    competencies.value = loadedCompetencies;

    for (const item of loadedCompetencies) {
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

    void labelCache.hydrateKeys(loadedCompetencies.map((item) => item.competency_key));
  } catch (error) {
    competenciesLoadError.value = error;
  } finally {
    isCompetenciesLoading.value = false;
  }
}

async function deleteProfile(): Promise<void> {
  if (isDeletingProfile.value) {
    return;
  }

  const confirmed = await confirm({
    title: "Delete profile",
    message: "Delete your profile and all saved competencies?",
    confirmLabel: "Delete profile",
    cancelLabel: "Keep profile",
    tone: "danger",
  });
  if (!confirmed) {
    return;
  }

  isDeletingProfile.value = true;
  deleteProfileError.value = null;

  try {
    await seekerClient.deleteProfile();
    profile.value = null;
    competencies.value = [];
    selectedOccupationLabel.value = null;
    isFirstTimeProfile.value = true;
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      profile.value = null;
      competencies.value = [];
      selectedOccupationLabel.value = null;
      isFirstTimeProfile.value = true;
    } else {
      deleteProfileError.value = error;
    }
  } finally {
    isDeletingProfile.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadProfile(), loadCompetencies()]);
});
</script>
