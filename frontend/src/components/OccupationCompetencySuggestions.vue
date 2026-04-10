<template>
  <section class="d-grid gap-2">
    <p class="fw-semibold mb-0">{{ label }}</p>

    <p v-if="!occupationKey" class="text-body-secondary mb-0">{{ waitingText }}</p>
    <p v-else-if="isLoading" class="text-body-secondary mb-0">Loading related competencies...</p>
    <ApiErrorNotice v-else-if="loadError" :error="loadError" />
    <p v-else-if="suggestedCompetencies.length === 0" class="text-body-secondary mb-0">{{ emptyText }}</p>

    <ul v-else class="list-group">
      <li v-for="item in suggestedCompetencies" :key="item.key">
        <button
          class="list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-3"
          type="button"
          :disabled="isDisabled || isSelected(item.key)"
          @click="selectSuggestion(item)"
        >
          <span class="flex-grow-1 min-w-0 text-break fw-semibold">{{ item.label }}</span>
          <span class="small text-body-secondary fw-semibold">
            {{ isSelected(item.key) ? alreadyAddedText : addText }}
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { catalogClient } from "../api";
import type { CatalogItem } from "../types/domain";
import ApiErrorNotice from "./ApiErrorNotice.vue";

interface Props {
  occupationKey: string | null;
  selectedKeys: string[];
  disabled?: boolean;
  busy?: boolean;
  label?: string;
  waitingText?: string;
  emptyText?: string;
  addText?: string;
  alreadyAddedText?: string;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  busy: false,
  label: "Related competencies",
  waitingText: "Select an occupation to see related competencies.",
  emptyText: "No related competencies found for this occupation.",
  addText: "Add",
  alreadyAddedText: "Already added",
});

const emit = defineEmits<{
  select: [item: CatalogItem];
}>();

const suggestedCompetencies = ref<CatalogItem[]>([]);
const isLoading = ref(false);
const loadError = ref<unknown | null>(null);

const isDisabled = computed(() => props.disabled || props.busy);
const selectedKeySet = computed(() => new Set(props.selectedKeys));
let requestCounter = 0;

function isSelected(key: string): boolean {
  return selectedKeySet.value.has(key);
}

function selectSuggestion(item: CatalogItem): void {
  if (isDisabled.value || isSelected(item.key)) {
    return;
  }
  emit("select", item);
}

watch(
  () => props.occupationKey,
  async (occupationKey) => {
    requestCounter += 1;
    const requestId = requestCounter;

    loadError.value = null;

    if (!occupationKey) {
      suggestedCompetencies.value = [];
      isLoading.value = false;
      return;
    }

    isLoading.value = true;

    try {
      const occupation = await catalogClient.getOccupation(occupationKey);
      if (requestId !== requestCounter) {
        return;
      }

      const seenKeys = new Set<string>();
      const deduplicated = occupation.required_competencies.filter((item) => {
        if (seenKeys.has(item.key)) {
          return false;
        }
        seenKeys.add(item.key);
        return true;
      });
      suggestedCompetencies.value = deduplicated;
    } catch (error) {
      if (requestId !== requestCounter) {
        return;
      }
      suggestedCompetencies.value = [];
      loadError.value = error;
    } finally {
      if (requestId === requestCounter) {
        isLoading.value = false;
      }
    }
  },
  { immediate: true },
);
</script>
