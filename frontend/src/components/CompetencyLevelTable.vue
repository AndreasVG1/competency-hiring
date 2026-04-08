<template>
  <p v-if="rows.length === 0" class="table-note">{{ emptyText }}</p>

  <table v-else class="competency-table">
    <thead>
      <tr>
        <th>Competency</th>
        <th v-if="showKey">Key</th>
        <th>Level</th>
        <th v-if="showContextColumn">Context</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.id">
        <td>{{ resolveLabel(row.competency_key) }}</td>
        <td v-if="showKey"><code>{{ row.competency_key }}</code></td>
        <td>{{ formatLevel(row.level) }}</td>
        <td v-if="showContextColumn">
          <button
            v-if="indicatorCount(row.competency_key) > 0"
            type="button"
            class="button-secondary indicator-trigger-button"
            @click="openIndicators(row.competency_key)"
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
    :label-resolver="labelResolver"
    :title-id="overlayTitleId"
    @close="closeIndicators"
  />
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import type { ActivityIndicatorCatalogItem } from "../types/domain";
import ActivityIndicatorsOverlay from "./ActivityIndicatorsOverlay.vue";

interface CompetencyLevelTableRow {
  id: string | number;
  competency_key: string;
  level: string;
}

interface Props {
  rows: CompetencyLevelTableRow[];
  emptyText?: string;
  showKey?: boolean;
  labelResolver?: (competencyKey: string) => string;
  levelFormatter?: (level: string) => string;
  activityIndicatorResolver?: (competencyKey: string) => ActivityIndicatorCatalogItem[] | undefined;
  overlayTitleId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  emptyText: "No competencies available.",
  showKey: false,
  labelResolver: undefined,
  levelFormatter: undefined,
  activityIndicatorResolver: undefined,
  overlayTitleId: "competency-level-table-indicators-title",
});

const overlayCompetencyKey = ref<string | null>(null);

const showContextColumn = computed(() => props.activityIndicatorResolver !== undefined);
const activeIndicators = computed<ActivityIndicatorCatalogItem[]>(() => {
  if (!overlayCompetencyKey.value || !props.activityIndicatorResolver) {
    return [];
  }
  return props.activityIndicatorResolver(overlayCompetencyKey.value) ?? [];
});

function resolveLabel(competencyKey: string): string {
  if (props.labelResolver) {
    return props.labelResolver(competencyKey);
  }
  return competencyKey;
}

function formatLevel(level: string): string {
  if (props.levelFormatter) {
    return props.levelFormatter(level);
  }
  return level;
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
