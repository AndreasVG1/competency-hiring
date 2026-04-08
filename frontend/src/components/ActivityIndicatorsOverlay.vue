<template>
  <div v-if="competencyKey !== null" class="indicator-overlay-backdrop" @click="emitClose">
    <section
      class="indicator-overlay-panel"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.stop
    >
      <header class="indicator-overlay-header">
        <h3 :id="titleId">Activity indicators</h3>
        <button type="button" class="button-secondary indicator-overlay-close" @click="emitClose">
          Close
        </button>
      </header>

      <p class="indicator-overlay-subtitle">
        {{ resolveLabel(competencyKey) }}
        <small>({{ competencyKey }})</small>
      </p>

      <p v-if="indicators.length === 0" class="table-note">No indicators available.</p>
      <ol v-else class="indicator-overlay-list">
        <li v-for="indicator in indicators" :key="indicator.key" class="indicator-overlay-item">
          {{ indicator.text }}
        </li>
      </ol>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { ActivityIndicatorCatalogItem } from "../types/domain";

interface Props {
  competencyKey: string | null;
  indicators: ActivityIndicatorCatalogItem[];
  titleId: string;
  labelResolver?: (competencyKey: string) => string;
}

const props = withDefaults(defineProps<Props>(), {
  labelResolver: undefined,
});

const emit = defineEmits<{
  close: [];
}>();

function resolveLabel(competencyKey: string): string {
  if (props.labelResolver) {
    return props.labelResolver(competencyKey);
  }
  return competencyKey;
}

function emitClose(): void {
  emit("close");
}
</script>
