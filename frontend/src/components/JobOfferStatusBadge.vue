<template>
  <span :class="badgeClass">{{ statusLabel }}</span>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { JobOfferStatus } from "../types/domain";

interface Props {
  status: JobOfferStatus;
}

const props = defineProps<Props>();

const statusLabel = computed(() => {
  if (props.status === "published") {
    return "Published";
  }
  if (props.status === "archived") {
    return "Archived";
  }
  return "Draft";
});

const badgeClass = computed(() => {
  if (props.status === "published") {
    return "badge text-bg-success";
  }
  if (props.status === "archived") {
    return "badge text-bg-danger";
  }
  return "badge text-bg-secondary";
});
</script>
