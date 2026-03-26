<template>
  <section class="catalog-search-picker">
    <label class="form-field">
      <span>{{ label }}</span>
      <input
        v-model="query"
        type="search"
        :placeholder="placeholder"
        :disabled="isDisabled"
      />
    </label>

    <p v-if="isSearching" class="picker-meta">Searching...</p>
    <p v-else-if="searchError" class="picker-error">Search failed. Try again.</p>
    <p v-else-if="showNoResults" class="picker-meta">{{ noResultsText }}</p>

    <ul v-if="results.length > 0" class="picker-results">
      <li v-for="item in results" :key="item.key">
        <button
          class="picker-result-button"
          type="button"
          :disabled="isDisabled"
          @click="selectItem(item)"
        >
          <span class="picker-result-label">{{ item.label }}</span>
          <span class="picker-result-key">{{ item.key }}</span>
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import type { CatalogItem } from "../types/domain";

interface Props {
  label: string;
  placeholder?: string;
  noResultsText?: string;
  minQueryLength?: number;
  debounceMs?: number;
  disabled?: boolean;
  busy?: boolean;
  searchFn: (query: string) => Promise<CatalogItem[]>;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: "Search...",
  noResultsText: "No matching items.",
  minQueryLength: 2,
  debounceMs: 300,
  disabled: false,
  busy: false,
});

const emit = defineEmits<{
  select: [item: CatalogItem];
}>();

const query = ref("");
const results = ref<CatalogItem[]>([]);
const isSearching = ref(false);
const hasSearched = ref(false);
const searchError = ref<unknown | null>(null);

let requestCounter = 0;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

const isDisabled = computed(() => props.disabled || props.busy);
const normalizedQuery = computed(() => query.value.trim());

const showNoResults = computed(() => {
  return (
    !isSearching.value &&
    !searchError.value &&
    hasSearched.value &&
    normalizedQuery.value.length >= props.minQueryLength &&
    results.value.length === 0
  );
});

function clearDebounce(): void {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

async function runSearch(searchQuery: string): Promise<void> {
  const requestId = requestCounter + 1;
  requestCounter = requestId;

  isSearching.value = true;
  searchError.value = null;

  try {
    const items = await props.searchFn(searchQuery);
    if (requestCounter !== requestId) {
      return;
    }
    results.value = items;
    hasSearched.value = true;
  } catch (error) {
    if (requestCounter !== requestId) {
      return;
    }
    results.value = [];
    hasSearched.value = true;
    searchError.value = error;
  } finally {
    if (requestCounter === requestId) {
      isSearching.value = false;
    }
  }
}

function selectItem(item: CatalogItem): void {
  emit("select", item);
  query.value = item.label;
  results.value = [];
}

watch(
  normalizedQuery,
  (currentQuery) => {
    clearDebounce();
    searchError.value = null;

    if (currentQuery.length < props.minQueryLength) {
      results.value = [];
      hasSearched.value = false;
      isSearching.value = false;
      return;
    }

    debounceTimer = setTimeout(() => {
      void runSearch(currentQuery);
    }, props.debounceMs);
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  clearDebounce();
});
</script>
