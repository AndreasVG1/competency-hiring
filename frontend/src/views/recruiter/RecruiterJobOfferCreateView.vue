<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/recruiter">Tagasi avalehele</RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Tööandja vaade</p>
      <h1 class="h3 mb-1">Loo tööpakkumise mustand</h1>
      <p class="text-body-secondary mb-0">
        Vali ametikoht ja kirjeldus. Pärast loomist suunatakse sind redigeerimise lehele.
      </p>
    </header>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Uus tööpakkumine</h2>
        <p class="text-body-secondary mb-0">Loo esmalt uus tööpakkumine, seejärel jätka redigeerimise lehel.</p>
      </header>

      <form class="d-grid gap-3" @submit.prevent="createJobOffer">
        <CatalogSearchPicker
          :key="occupationPickerKey"
          label="Ametikoht"
          placeholder="Otsi ametikohti"
          no-results-text="Ametikohti ei leitud."
          :disabled="isCreating"
          :busy="isCreating"
          :search-fn="searchOccupations"
          @select="selectOccupation"
        />

        <p class="mb-0 text-break">
          <strong>Valitud ametikoht: </strong>
          <span v-if="selectedOccupation">
            {{ selectedOccupation.label }}
            <span class="d-block small text-body-secondary break-all">({{ selectedOccupation.key }})</span>
          </span>
          <span v-else>Puudub</span>
        </p>

        <div class="d-flex flex-wrap gap-2">
          <button
            class="btn btn-outline-secondary"
            type="button"
            :disabled="!selectedOccupation || isCreating"
            @click="clearOccupation"
          >
            Eemalda ametikoht
          </button>
        </div>

        <div>
          <label class="form-label" for="job-offer-description">Kirjeldus</label>
          <textarea
            id="job-offer-description"
            v-model="description"
            placeholder="Kirjelda tööpakkumist"
            class="form-control"
            rows="4"
            required
            :disabled="isCreating"
          />
        </div>

        <ApiErrorNotice v-if="createError" :error="createError" show-all-messages />

        <button class="btn btn-primary" type="submit" :disabled="isCreating || !selectedOccupation">
          {{ isCreating ? "Loon..." : "Loo mustand" }}
        </button>
      </form>
    </section>
  </div>
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

async function searchOccupations(
  query: string,
  options: { signal?: AbortSignal } = {},
): Promise<CatalogItem[]> {
  return catalogClient.listOccupations({ query, limit: 8 }, { signal: options.signal });
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
    createError.value = "Vali ametikoht enne tööpakkumise koostamist.";
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
