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
        <h3 :id="titleId">Tegevusnäitajad</h3>
        <button type="button" class="btn btn-outline-secondary btn-sm" @click="emitClose">
          Sulge
        </button>
      </header>

      <p class="indicator-overlay-subtitle text-break">
        {{ resolveLabel(competencyKey) }}
      </p>

      <p v-if="loading" class="text-body-secondary mb-0">Tegevusnäitajad laaditakse...</p>
      <p v-else-if="indicators.length === 0" class="text-body-secondary mb-0">Tegevusnäitajaid ei leitud.</p>
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
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  labelResolver: undefined,
  loading: false,
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
