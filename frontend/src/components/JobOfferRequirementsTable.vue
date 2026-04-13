<template>
  <p v-if="requirements.length === 0" class="text-body-secondary mb-0">{{ emptyText }}</p>

  <div v-else class="table-responsive">
    <table class="table table-sm align-middle mb-0">
      <thead>
        <tr>
          <th scope="col">Kompetents</th>
          <th scope="col">Prioriteet</th>
          <th v-if="showIndicatorsColumn" scope="col">Tegevusnäitajad</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in requirements" :key="item.competency_key">
          <td class="text-break">{{ resolveLabel(item.competency_key) }}</td>
          <td>{{ formatPriority(item.priority) }}</td>
          <td v-if="showIndicatorsColumn">
            <button
              v-if="indicatorCount(item.competency_key) > 0"
              type="button"
              class="btn btn-outline-secondary btn-sm"
              @click="openIndicators(item.competency_key)"
            >
              Kuva näitajad
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <ActivityIndicatorsOverlay
    :competency-key="overlayCompetencyKey"
    :indicators="activeIndicators"
    :loading="isOverlayLoading"
    :label-resolver="resolveLabel"
    title-id="job-offer-requirements-indicators-title"
    @close="closeIndicators"
  />
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import type {
  ActivityIndicatorCatalogItem,
  PublicJobOfferRequirementItem,
  RequirementPriority,
} from "../types/domain";
import ActivityIndicatorsOverlay from "./ActivityIndicatorsOverlay.vue";

interface Props {
  requirements: PublicJobOfferRequirementItem[];
  emptyText?: string;
  labelResolver?: (competencyKey: string) => string;
  activityIndicatorResolver?: (competencyKey: string) => ActivityIndicatorCatalogItem[] | undefined;
  activityIndicatorCountResolver?: (competencyKey: string) => number;
  activityIndicatorLoader?: (competencyKey: string) => Promise<void>;
}

const props = withDefaults(defineProps<Props>(), {
  emptyText: "Nõuded puuduvad.",
  labelResolver: undefined,
  activityIndicatorResolver: undefined,
  activityIndicatorCountResolver: undefined,
  activityIndicatorLoader: undefined,
});

const overlayCompetencyKey = ref<string | null>(null);
const isOverlayLoading = ref(false);

const showIndicatorsColumn = computed(
  () => props.activityIndicatorResolver !== undefined || props.activityIndicatorCountResolver !== undefined,
);
const activeIndicators = computed<ActivityIndicatorCatalogItem[]>(() => {
  if (overlayCompetencyKey.value === null || !props.activityIndicatorResolver) {
    return [];
  }
  return props.activityIndicatorResolver(overlayCompetencyKey.value) ?? [];
});

function formatPriority(priority: RequirementPriority): string {
  if (priority === "must_have") {
    return "Kohustuslik";
  }
  if (priority === "important") {
    return "Oluline";
  }
  return "Soovituslik";
}

function resolveLabel(competencyKey: string): string {
  if (props.labelResolver) {
    return props.labelResolver(competencyKey);
  }
  return competencyKey;
}

function indicatorCount(competencyKey: string): number {
  if (props.activityIndicatorCountResolver) {
    return props.activityIndicatorCountResolver(competencyKey);
  }
  if (props.activityIndicatorResolver) {
    return (props.activityIndicatorResolver(competencyKey) ?? []).length;
  }
  return 0;
}

function openIndicators(competencyKey: string): void {
  overlayCompetencyKey.value = competencyKey;
  isOverlayLoading.value = props.activityIndicatorLoader !== undefined;

  if (!props.activityIndicatorLoader) {
    return;
  }

  const activeKey = competencyKey;
  void (async () => {
    try {
      await props.activityIndicatorLoader?.(competencyKey);
    } finally {
      if (overlayCompetencyKey.value === activeKey) {
        isOverlayLoading.value = false;
      }
    }
  })();
}

function closeIndicators(): void {
  overlayCompetencyKey.value = null;
  isOverlayLoading.value = false;
}
</script>
