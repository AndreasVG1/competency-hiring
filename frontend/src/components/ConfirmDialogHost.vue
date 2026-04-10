<template>
  <Teleport to="body">
    <div
      v-if="isDialogOpen && activeRequest"
      class="confirm-dialog-overlay"
      @click.self="cancelCurrent"
    >
      <section
        ref="dialogElement"
        class="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        tabindex="-1"
        @keydown="handleDialogKeydown"
      >
        <h2 id="confirm-dialog-title">{{ activeRequest.title }}</h2>
        <p id="confirm-dialog-message">{{ activeRequest.message }}</p>
        <div class="d-flex justify-content-end flex-wrap gap-2">
          <button class="btn btn-outline-secondary" type="button" @click="cancelCurrent">
            {{ activeRequest.cancelLabel }}
          </button>
          <button
            :class="activeRequest.tone === 'danger' ? 'btn btn-danger' : 'btn btn-primary'"
            type="button"
            @click="confirmCurrent"
          >
            {{ activeRequest.confirmLabel }}
          </button>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import { useConfirmDialog } from "../composables/useConfirmDialog";

const dialogElement = ref<HTMLElement | null>(null);
const { isDialogOpen, activeRequest, confirmCurrent, cancelCurrent } = useConfirmDialog();

function handleDialogKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    event.preventDefault();
    cancelCurrent();
    return;
  }

  if (event.key !== "Enter") {
    return;
  }

  if (event.target instanceof HTMLButtonElement) {
    return;
  }

  event.preventDefault();
  confirmCurrent();
}

watch(isDialogOpen, async (open) => {
  if (!open) {
    return;
  }

  await nextTick();
  dialogElement.value?.focus();
});
</script>
