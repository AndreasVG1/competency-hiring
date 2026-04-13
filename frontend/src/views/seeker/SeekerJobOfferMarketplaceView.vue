<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" to="/seeker">Tagasi oma profiilile</RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Tööpakkumised</p>
      <div class="d-flex flex-wrap align-items-center gap-2">
        <h1 class="h3 mb-0">Avaldatud tööpakkumised</h1>
        <JobOfferStatusBadge status="published" />
      </div>
      <p class="text-body-secondary mb-0">
        Sirvi hetkel avaldatud tööpakkumisi.
      </p>
    </header>

    <ApiErrorNotice v-if="occupationsLoadError" :error="occupationsLoadError" show-all-messages />

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Filtrid</h2>
        <p class="text-body-secondary mb-0">Rakenda filtreid, et kitsendada nimekirja.</p>
      </header>

      <MarketplaceFilterBar
        :query="draftQuery"
        :occupation-key="draftOccupationKey"
        :applied-state="draftAppliedState"
        :occupation-options="occupationOptions"
        :disabled="isOffersLoading || isOccupationsLoading"
        @update:query="draftQuery = $event"
        @update:occupation-key="draftOccupationKey = $event"
        @update:applied-state="draftAppliedState = $event"
        @apply="applyFilters"
        @clear="clearFilters"
      />

      <div class="row g-3">
        <div class="col-12 col-md-3">
          <label class="d-grid gap-1">
            <span class="form-label mb-0">Tööpakkumiste arv</span>
            <select v-model.number="limit" class="form-select" :disabled="isOffersLoading" @change="applyFilters">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
            </select>
          </label>
        </div>
      </div>
    </section>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Tulemused</h2>
        <p v-if="offers.length > 0" class="text-body-secondary mb-0">
          Kuvatakse {{ pageStart }}-{{ pageEnd }} avaldatud pakkumist.
        </p>
      </header>

      <ApiErrorNotice v-if="offersLoadError" :error="offersLoadError" show-all-messages />

      <p v-if="isOffersLoading" class="text-body-secondary mb-0">Laen tööpakkumisi...</p>
      <p v-else-if="offers.length === 0" class="text-body-secondary mb-0">Tööpakkumisi ei leitud.</p>

      <ul v-else class="list-group">
        <li v-for="offer in offers" :key="offer.id" class="list-group-item">
          <div class="d-flex justify-content-between align-items-start gap-3">
            <div class="min-w-0 flex-grow-1">
              <div class="d-flex flex-wrap align-items-center gap-2">
                <h3 class="h6 mb-0 text-break">{{ offer.title }}</h3>
                <JobOfferStatusBadge status="published" />
                <span v-if="offer.applied" class="badge text-bg-info">Kandideeritud</span>
              </div>
              <p class="text-body-secondary mb-1 text-break">
                {{ offer.company_name || "Ettevõte pole esitatud" }} | {{ offer.occupation_label }}
              </p>
              <p class="mb-1 text-break">{{ offer.short_description }}</p>
              <p class="text-body-secondary mb-0">Avaldatud {{ formatDateTime(offer.published_at) }}</p>
            </div>
            <div class="flex-shrink-0">
              <RouterLink class="btn btn-outline-secondary btn-sm" :to="`/seeker/job-offers/${offer.id}`">
                Vaata üksikasju
              </RouterLink>
            </div>
          </div>
        </li>
      </ul>

      <div class="d-flex flex-wrap gap-2 justify-content-end">
        <button class="btn btn-outline-secondary" type="button" :disabled="!canGoPrevious" @click="goPreviousPage">
          Tagasi
        </button>
        <button class="btn btn-outline-secondary" type="button" :disabled="!canGoNext" @click="goNextPage">
          Edasi
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { catalogClient, seekerClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import MarketplaceFilterBar from "../../components/MarketplaceFilterBar.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import type { CatalogItem, PublicJobOfferListItem } from "../../types/domain";

const DEFAULT_LIMIT = 10;
const OCCUPATION_FILTER_LIMIT = 100;

const occupationOptions = ref<CatalogItem[]>([]);
const offers = ref<PublicJobOfferListItem[]>([]);

const draftQuery = ref("");
const draftOccupationKey = ref("");
const draftAppliedState = ref("");
const appliedQuery = ref("");
const appliedOccupationKey = ref("");
const appliedAppliedState = ref("");

const limit = ref(DEFAULT_LIMIT);
const offset = ref(0);

const isOffersLoading = ref(true);
const isOccupationsLoading = ref(true);

const offersLoadError = ref<unknown | null>(null);
const occupationsLoadError = ref<unknown | null>(null);

const canGoPrevious = computed(() => !isOffersLoading.value && offset.value > 0);
const canGoNext = computed(() => !isOffersLoading.value && offers.value.length === limit.value);

const pageStart = computed(() => {
  if (offers.value.length === 0) {
    return 0;
  }
  return offset.value + 1;
});

const pageEnd = computed(() => {
  if (offers.value.length === 0) {
    return 0;
  }
  return offset.value + offers.value.length;
});

function normalizeFilterValue(value: string): string {
  return value.trim();
}

function mapAppliedFilter(value: string): boolean | undefined {
  if (value === "applied") {
    return true;
  }
  if (value === "not_applied") {
    return false;
  }
  return undefined;
}

function formatDateTime(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(parsed));
}

async function loadOccupations(): Promise<void> {
  isOccupationsLoading.value = true;
  occupationsLoadError.value = null;

  try {
    occupationOptions.value = await catalogClient.listOccupations({
      limit: OCCUPATION_FILTER_LIMIT,
    });
  } catch (error) {
    occupationsLoadError.value = error;
  } finally {
    isOccupationsLoading.value = false;
  }
}

async function loadOffers(): Promise<void> {
  isOffersLoading.value = true;
  offersLoadError.value = null;

  try {
    offers.value = await seekerClient.listPublishedJobOffers({
      query: appliedQuery.value || undefined,
      occupation_key: appliedOccupationKey.value || undefined,
      applied: mapAppliedFilter(appliedAppliedState.value),
      limit: limit.value,
      offset: offset.value,
    });
  } catch (error) {
    offersLoadError.value = error;
  } finally {
    isOffersLoading.value = false;
  }
}

async function applyFilters(): Promise<void> {
  appliedQuery.value = normalizeFilterValue(draftQuery.value);
  appliedOccupationKey.value = normalizeFilterValue(draftOccupationKey.value);
  appliedAppliedState.value = draftAppliedState.value;
  offset.value = 0;
  await loadOffers();
}

async function clearFilters(): Promise<void> {
  draftQuery.value = "";
  draftOccupationKey.value = "";
  draftAppliedState.value = "";
  appliedQuery.value = "";
  appliedOccupationKey.value = "";
  appliedAppliedState.value = "";
  offset.value = 0;
  await loadOffers();
}

async function goPreviousPage(): Promise<void> {
  if (!canGoPrevious.value) {
    return;
  }
  offset.value = Math.max(0, offset.value - limit.value);
  await loadOffers();
}

async function goNextPage(): Promise<void> {
  if (!canGoNext.value) {
    return;
  }
  offset.value += limit.value;
  await loadOffers();
}

onMounted(async () => {
  await Promise.all([loadOccupations(), loadOffers()]);
});
</script>
