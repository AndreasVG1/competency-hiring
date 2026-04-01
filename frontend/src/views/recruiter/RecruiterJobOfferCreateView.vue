<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/recruiter">Back to recruiter</RouterLink>
      
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Create Draft Job Offer</h1>
        <p class="content">Choose an occupation and description. After creation, you will be redirected to edit details.</p>
      </header>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>New Job Offer</h2>
          <p>Create first, then continue in the edit route.</p>
        </header>

        <form class="recruiter-form" @submit.prevent="createJobOffer">
          <CatalogSearchPicker
            :key="occupationPickerKey"
            label="Occupation"
            placeholder="Search occupations"
            no-results-text="No occupations found."
            :disabled="isCreating"
            :busy="isCreating"
            :search-fn="searchOccupations"
            @select="selectOccupation"
          />

          <p class="selected-item">
            <strong>Selected occupation:</strong>
            <span v-if="selectedOccupation">
              {{ selectedOccupation.label }} <small>({{ selectedOccupation.key }})</small>
            </span>
            <span v-else>None</span>
          </p>

          <button
            class="button-secondary"
            type="button"
            :disabled="!selectedOccupation || isCreating"
            @click="clearOccupation"
          >
            Clear occupation
          </button>

          <label class="form-field">
            <span>Description</span>
            <textarea
              v-model="description"
              rows="4"
              required
              :disabled="isCreating"
            />
          </label>

          <ApiErrorNotice v-if="createError" :error="createError" show-all-messages />

          <button class="button-primary" type="submit" :disabled="isCreating || !selectedOccupation">
            {{ isCreating ? "Creating..." : "Create draft offer" }}
          </button>
        </form>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { catalogClient, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import CatalogSearchPicker from "../../components/CatalogSearchPicker.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import type { CatalogItem } from "../../types/domain";

const router = useRouter();

const selectedOccupation = ref<CatalogItem | null>(null);
const occupationPickerKey = ref(0);
const description = ref("");
const isCreating = ref(false);
const createError = ref<unknown | null>(null);

async function searchOccupations(query: string): Promise<CatalogItem[]> {
  return catalogClient.listOccupations({ query, limit: 8 });
}

function selectOccupation(item: CatalogItem): void {
  selectedOccupation.value = item;
  createError.value = null;
}

function clearOccupation(): void {
  selectedOccupation.value = null;
  occupationPickerKey.value += 1;
  createError.value = null;
}

async function createJobOffer(): Promise<void> {
  if (isCreating.value) {
    return;
  }

  if (!selectedOccupation.value) {
    createError.value = "Choose an occupation before creating the offer.";
    return;
  }

  isCreating.value = true;
  createError.value = null;

  try {
    const created = await recruiterClient.createJobOffer({
      occupation_key: selectedOccupation.value.key,
      description: description.value.trim(),
    });
    await router.replace(`/recruiter/job-offers/${created.id}/edit`);
  } catch (error) {
    createError.value = error;
  } finally {
    isCreating.value = false;
  }
}
</script>
