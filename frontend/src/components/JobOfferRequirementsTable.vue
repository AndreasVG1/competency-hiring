<template>
  <p v-if="requirements.length === 0" class="table-note">{{ emptyText }}</p>

	<table v-else class="competency-table">
	    <thead>
	      <tr>
	        <th>Competency</th>
	        <th>Priority</th>
	        <th v-if="showIndicatorsColumn">Context</th>
	      </tr>
	    </thead>
	    <tbody>
	      <tr v-for="item in requirements" :key="item.competency_key">
	        <td>{{ resolveLabel(item.competency_key) }}</td>
	        <td>{{ formatPriority(item.priority) }}</td>
	        <td v-if="showIndicatorsColumn">
	          <button
	            v-if="indicatorCount(item.competency_key) > 0"
            type="button"
            class="button-secondary indicator-trigger-button"
            @click="openIndicators(item.competency_key)"
          >
            View indicators
          </button>
        </td>
      </tr>
    </tbody>
  </table>

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
  emptyText: "No requirements listed for this offer.",
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
    return "Must have";
  }
  if (priority === "important") {
    return "Important";
  }
  return "Nice to have";
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
