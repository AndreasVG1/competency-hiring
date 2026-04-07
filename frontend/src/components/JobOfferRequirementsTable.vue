<template>
  <p v-if="requirements.length === 0" class="table-note">{{ emptyText }}</p>

  <table v-else class="competency-table">
    <thead>
      <tr>
        <th>Competency</th>
        <th>Key</th>
        <th>Priority</th>
        <th v-if="showIndicatorsColumn">Context</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="item in requirements" :key="item.competency_key">
        <td>{{ resolveLabel(item.competency_key) }}</td>
        <td><code>{{ item.competency_key }}</code></td>
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

  <div
    v-if="overlayCompetencyKey !== null"
    class="indicator-overlay-backdrop"
    @click="closeIndicators"
  >
    <section
      class="indicator-overlay-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="activity-indicators-title"
      @click.stop
    >
      <header class="indicator-overlay-header">
        <h3 id="activity-indicators-title">Activity indicators</h3>
        <button type="button" class="button-secondary indicator-overlay-close" @click="closeIndicators">
          Close
        </button>
      </header>

      <p class="indicator-overlay-subtitle">
        {{ resolveLabel(overlayCompetencyKey) }}
        <small>({{ overlayCompetencyKey }})</small>
      </p>

      <p v-if="activeIndicators.length === 0" class="table-note">No indicators available.</p>
      <ol v-else class="indicator-overlay-list">
        <li
          v-for="indicator in activeIndicators"
          :key="indicator.key"
          class="indicator-overlay-item"
        >
          {{ indicator.text }}
        </li>
      </ol>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import type {
  ActivityIndicatorCatalogItem,
  PublicJobOfferRequirementItem,
  RequirementPriority,
} from "../types/domain";

interface Props {
  requirements: PublicJobOfferRequirementItem[];
  emptyText?: string;
  labelResolver?: (competencyKey: string) => string;
  activityIndicatorResolver?: (competencyKey: string) => ActivityIndicatorCatalogItem[] | undefined;
}

const props = withDefaults(defineProps<Props>(), {
  emptyText: "No requirements listed for this offer.",
  labelResolver: undefined,
  activityIndicatorResolver: undefined,
});

const overlayCompetencyKey = ref<string | null>(null);

const showIndicatorsColumn = computed(() => props.activityIndicatorResolver !== undefined);
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
  if (!props.activityIndicatorResolver) {
    return 0;
  }
  return (props.activityIndicatorResolver(competencyKey) ?? []).length;
}

function openIndicators(competencyKey: string): void {
  overlayCompetencyKey.value = competencyKey;
}

function closeIndicators(): void {
  overlayCompetencyKey.value = null;
}
</script>
