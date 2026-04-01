import { ref } from "vue";

export type ConfirmTone = "primary" | "danger";

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: ConfirmTone;
}

interface ActiveConfirmRequest {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  tone: ConfirmTone;
}

const isDialogOpen = ref(false);
const activeRequest = ref<ActiveConfirmRequest | null>(null);

let pendingResolver: ((confirmed: boolean) => void) | null = null;
let lastFocusedElement: HTMLElement | null = null;

function resolveDialog(confirmed: boolean): void {
  if (!isDialogOpen.value) {
    return;
  }

  isDialogOpen.value = false;
  activeRequest.value = null;

  const resolver = pendingResolver;
  pendingResolver = null;
  resolver?.(confirmed);

  const elementToFocus = lastFocusedElement;
  lastFocusedElement = null;
  if (elementToFocus) {
    requestAnimationFrame(() => {
      elementToFocus.focus();
    });
  }
}

function normalizeOptions(options: ConfirmOptions): ActiveConfirmRequest {
  return {
    title: options.title ?? "Confirm action",
    message: options.message,
    confirmLabel: options.confirmLabel ?? "Confirm",
    cancelLabel: options.cancelLabel ?? "Cancel",
    tone: options.tone ?? "primary",
  };
}

export function useConfirmDialog() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    if (pendingResolver) {
      pendingResolver(false);
      pendingResolver = null;
    }

    lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    activeRequest.value = normalizeOptions(options);
    isDialogOpen.value = true;

    return new Promise<boolean>((resolve) => {
      pendingResolver = resolve;
    });
  }

  function confirmCurrent(): void {
    resolveDialog(true);
  }

  function cancelCurrent(): void {
    resolveDialog(false);
  }

  return {
    isDialogOpen,
    activeRequest,
    confirm,
    confirmCurrent,
    cancelCurrent,
  };
}
