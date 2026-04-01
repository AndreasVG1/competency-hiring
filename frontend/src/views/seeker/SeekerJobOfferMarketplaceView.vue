<template>
  <main class="seeker-page">
    <section class="panel seeker-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" to="/seeker">Back to seeker overview</RouterLink>
        <button class="button-danger" type="button" :disabled="isLoggingOut" @click="logout">
          {{ isLoggingOut ? "Signing out..." : "Log out" }}
        </button>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Seeker Marketplace</p>
        <h1>Published Job Offers</h1>
        <p class="content">
          Browse currently published offers. No suitability score is shown in this phase.
        </p>
        <JobOfferStatusBadge status="published" />
      </header>

      <ApiErrorNotice v-if="logoutError" :error="logoutError" />
      <ApiErrorNotice v-if="occupationsLoadError" :error="occupationsLoadError" show-all-messages />

      <section class="seeker-section">
        <header class="section-header">
          <h2>Filters</h2>
          <p>Apply explicit filters to narrow the list.</p>
        </header>

        <MarketplaceFilterBar
          :query="draftQuery"
          :occupation-key="draftOccupationKey"
          :occupation-options="occupationOptions"
          :disabled="isOffersLoading || isOccupationsLoading"
          @update:query="draftQuery = $event"
          @update:occupation-key="draftOccupationKey = $event"
          @apply="applyFilters"
          @clear="clearFilters"
        />

        <label class="form-field marketplace-page-size">
          <span>Page size</span>
          <select v-model.number="limit" :disabled="isOffersLoading" @change="applyFilters">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </label>
      </section>

      <section class="seeker-section">
        <header class="section-header">
          <h2>Results</h2>
          <p v-if="offers.length > 0">Showing {{ pageStart }}-{{ pageEnd }} published offers.</p>
        </header>

        <ApiErrorNotice v-if="offersLoadError" :error="offersLoadError" show-all-messages />

        <p v-if="isOffersLoading" class="section-note">Loading published offers...</p>
        <p v-else-if="offers.length === 0" class="section-note">No published offers match these filters.</p>

        <ul v-else class="marketplace-offer-list">
          <li v-for="offer in offers" :key="offer.id" class="marketplace-offer-card">
            <div class="marketplace-offer-header">
              <h3>{{ offer.title }}</h3>
              <JobOfferStatusBadge status="published" />
            </div>
            <p class="marketplace-offer-meta">
              {{ offer.company_name || "Company not provided" }} | {{ offer.occupation_label }}
            </p>
            <p class="marketplace-offer-summary">{{ offer.short_description }}</p>
            <p class="marketplace-offer-meta">Published {{ formatDateTime(offer.published_at) }}</p>
            <RouterLink class="button-secondary" :to="`/seeker/job-offers/${offer.id}`">
              View details
            </RouterLink>
          </li>
        </ul>

        <div class="table-actions">
          <button class="button-secondary" type="button" :disabled="!canGoPrevious" @click="goPreviousPage">
            Previous
          </button>
          <button class="button-secondary" type="button" :disabled="!canGoNext" @click="goNextPage">
            Next
          </button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { catalogClient, seekerClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import MarketplaceFilterBar from "../../components/MarketplaceFilterBar.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useLogout } from "../../composables/useLogout";
import type { CatalogItem, PublicJobOfferListItem } from "../../types/domain";

const DEFAULT_LIMIT = 10;
const OCCUPATION_FILTER_LIMIT = 100;

const { isLoggingOut, logoutError, logout } = useLogout();

const occupationOptions = ref<CatalogItem[]>([]);
const offers = ref<PublicJobOfferListItem[]>([]);

const draftQuery = ref("");
const draftOccupationKey = ref("");
const appliedQuery = ref("");
const appliedOccupationKey = ref("");

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
  offset.value = 0;
  await loadOffers();
}

async function clearFilters(): Promise<void> {
  draftQuery.value = "";
  draftOccupationKey.value = "";
  appliedQuery.value = "";
  appliedOccupationKey.value = "";
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
