<template>
  <section class="json-payload-viewer">
    <header v-if="title" class="subsection-header">
      <h3>{{ title }}</h3>
    </header>

    <p v-if="payload === null" class="section-note">{{ emptyText }}</p>
    <pre v-else class="json-payload-block"><code>{{ formattedPayload }}</code></pre>
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
