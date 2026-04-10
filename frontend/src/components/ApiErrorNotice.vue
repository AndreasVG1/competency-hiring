<template>
  <div class="alert alert-danger mb-0" role="alert" aria-live="polite">
    <p class="fw-semibold mb-0">{{ messages[0] }}</p>
    <ul v-if="showAllMessages && messages.length > 1" class="mt-2 mb-0 ps-4">
      <li v-for="(message, index) in messages.slice(1)" :key="`${index}-${message}`">
        {{ message }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { ApiClientError } from "../api";

interface Props {
  error: unknown;
  showAllMessages?: boolean;
  fallbackMessage?: string;
}

const props = withDefaults(defineProps<Props>(), {
  showAllMessages: false,
  fallbackMessage: "The request failed.",
});

const messages = computed<string[]>(() => {
  const error = props.error;

  if (!error) {
    return [props.fallbackMessage];
  }

  if (error instanceof ApiClientError) {
    const apiMessages = error.payload.details
      .map((detail) => detail.message)
      .filter((message): message is string => Boolean(message));

    if (apiMessages.length > 0) {
      return apiMessages;
    }

    return [error.payload.error || props.fallbackMessage];
  }

  if (typeof error === "string") {
    return [error];
  }

  if (error instanceof Error && error.message) {
    return [error.message];
  }

  return [props.fallbackMessage];
});
</script>
