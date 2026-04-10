<template>
  <section class="d-grid gap-2">
    <header v-if="title">
      <h3 class="h6 mb-0">{{ title }}</h3>
    </header>

    <p v-if="payload === null" class="text-body-secondary mb-0">{{ emptyText }}</p>
    <pre
      v-else
      class="bg-light border rounded-3 p-3 mb-0 overflow-auto font-monospace small"
    ><code>{{ formattedPayload }}</code></pre>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface Props {
  payload: unknown | null;
  title?: string;
  emptyText?: string;
}

const props = withDefaults(defineProps<Props>(), {
  title: "",
  emptyText: "No data available.",
});

const formattedPayload = computed(() => {
  if (props.payload === null) {
    return "";
  }
  return JSON.stringify(props.payload, null, 2);
});
</script>
