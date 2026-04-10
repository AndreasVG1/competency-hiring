<template>
  <section class="d-grid gap-2">
    <label class="d-grid gap-1">
      <span class="form-label mb-0">{{ label }}</span>
      <input
        v-model="query"
        type="search"
        class="form-control"
        :placeholder="placeholder"
        :disabled="isDisabled"
      />
    </label>

    <p v-if="isSearching" class="text-body-secondary mb-0">Searching...</p>
    <p v-else-if="searchError" class="text-danger fw-semibold mb-0">Search failed. Try again.</p>
    <p v-else-if="showNoResults" class="text-body-secondary mb-0">{{ noResultsText }}</p>

    <ul v-if="results.length > 0" class="list-group">
      <li v-for="item in results" :key="item.key">
        <button
          class="list-group-item list-group-item-action d-flex gap-2 align-items-start"
          type="button"
          :disabled="isDisabled"
          @click="selectItem(item)"
        >
          <span class="flex-grow-1 min-w-0 text-break fw-semibold">{{ item.label }}</span>
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
  searchFn: (query: string, options?: { signal?: AbortSignal }) => Promise<CatalogItem[]>;
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
let activeSearchController: AbortController | null = null;

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

  if (activeSearchController) {
    activeSearchController.abort();
  }
  activeSearchController = new AbortController();
  const controller = activeSearchController;

  try {
    const items = await props.searchFn(searchQuery, { signal: controller.signal });
    if (requestCounter !== requestId) {
      return;
    }
    results.value = items;
    hasSearched.value = true;
  } catch (error) {
    if (requestCounter !== requestId) {
      return;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
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
  if (activeSearchController) {
    activeSearchController.abort();
    activeSearchController = null;
  }
});
</script>
