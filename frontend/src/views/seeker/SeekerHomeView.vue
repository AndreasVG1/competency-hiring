<template>
  <main class="seeker-page">
    <section class="panel seeker-panel">
      <PageActionsBar>
        <RouterLink class="button-primary" to="/seeker/job-offers">
          Browse published job offers
        </RouterLink>
        <RouterLink class="button-secondary" to="/seeker/edit">Edit profile</RouterLink>
        <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
      </PageActionsBar>

      <header class="panel-header">
        <h1>Profile Overview</h1>
        <p class="content">Review what is currently saved in your private profile.</p>
      </header>

      <ApiErrorNotice v-if="logoutError" :error="logoutError" />
      <ApiErrorNotice v-if="deleteProfileError" :error="deleteProfileError" show-all-messages />

      <section class="seeker-section">
        <header class="section-header">
          <h2>Profile</h2>
        </header>

        <ApiErrorNotice v-if="profileLoadError" :error="profileLoadError" show-all-messages />

        <p v-if="isProfileLoading" class="section-note">Loading profile...</p>

        <template v-else-if="isFirstTimeProfile || !profile">
          <p class="section-note">No profile found yet.</p>
          <RouterLink class="button-primary" to="/seeker/edit">Create profile</RouterLink>
        </template>

        <template v-else>
          <dl class="summary-grid">
            <dt>Full name</dt>
            <dd>{{ profile.full_name }}</dd>
            <dt>Summary</dt>
            <dd>{{ profile.summary || "Not set" }}</dd>
            <dt>Location</dt>
            <dd>{{ profile.location || "Not set" }}</dd>
            <dt>Occupation</dt>
            <dd>
              <span v-if="profile.occupation_key">
                {{ selectedOccupationLabel || profile.occupation_key }}
              </span>
              <span v-else>Not set</span>
            </dd>
          </dl>

          <div class="table-actions">
            <RouterLink class="button-secondary" to="/seeker/edit">Edit profile</RouterLink>
            <button
              class="button-danger"
              type="button"
              :disabled="isDeletingProfile"
              @click="deleteProfile"
            >
              {{ isDeletingProfile ? "Deleting..." : "Delete profile" }}
            </button>
          </div>
        </template>
      </section>

      <section class="seeker-section">
        <header class="section-header">
          <h2>Competencies</h2>
        </header>

        <ApiErrorNotice v-if="competenciesLoadError" :error="competenciesLoadError" show-all-messages />

        <p v-if="isCompetenciesLoading" class="table-note">Loading competencies...</p>
        <p v-else-if="competencies.length === 0" class="table-note">No competencies saved yet.</p>

        <table v-else class="competency-table">
          <thead>
            <tr>
              <th>Competency</th>
              <th>Key</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in competencies" :key="item.id">
              <td>{{ competencyLabel(item.competency_key) }}</td>
              <td><code>{{ item.competency_key }}</code></td>
              <td>{{ formatLevel(item.level) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import { ApiClientError, catalogClient, seekerClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import { useConfirmDialog } from "../../composables/useConfirmDialog";
import { useLogout } from "../../composables/useLogout";
import type { CompetencyLevel, SeekerCompetencyResponse, SeekerProfileResponse } from "../../types/domain";

const { isLoggingOut, logoutError, logout } = useLogout();
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

function formatLevel(level: CompetencyLevel): string {
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
