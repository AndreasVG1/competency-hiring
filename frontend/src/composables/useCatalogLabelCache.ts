import { reactive } from "vue";

import { catalogClient } from "../api";

type LabelState = "idle" | "loading" | "ready" | "error";

export function useCatalogLabelCache() {
  const labelsByKey = reactive(new Map<string, string>());
  const loadingKeys = reactive(new Set<string>());
  const failedKeys = reactive(new Set<string>());
  const pendingRequests = new Map<string, Promise<void>>();

  function setLabel(key: string, label: string): void {
    const normalizedKey = key.trim();
    if (!normalizedKey) {
      return;
    }

    labelsByKey.set(normalizedKey, label);
    failedKeys.delete(normalizedKey);
    loadingKeys.delete(normalizedKey);
  }

  function getLabel(key: string): string | undefined {
    return labelsByKey.get(key);
  }

  function getLabelState(key: string): LabelState {
    if (labelsByKey.has(key)) {
      return "ready";
    }

    if (loadingKeys.has(key)) {
      return "loading";
    }

    if (failedKeys.has(key)) {
      return "error";
    }

    return "idle";
  }

  async function ensureLabel(key: string): Promise<void> {
    const normalizedKey = key.trim();

    if (!normalizedKey || labelsByKey.has(normalizedKey)) {
      return;
    }

    const existing = pendingRequests.get(normalizedKey);
    if (existing) {
      return existing;
    }

    const request = (async () => {
      loadingKeys.add(normalizedKey);
      failedKeys.delete(normalizedKey);

      try {
        const detail = await catalogClient.getCompetency(normalizedKey);
        labelsByKey.set(normalizedKey, detail.label);
      } catch (_error) {
        failedKeys.add(normalizedKey);
      } finally {
        loadingKeys.delete(normalizedKey);
        pendingRequests.delete(normalizedKey);
      }
    })();

    pendingRequests.set(normalizedKey, request);
    return request;
  }

  async function hydrateKeys(keys: string[]): Promise<void> {
    await Promise.all(keys.map((key) => ensureLabel(key)));
  }

  return {
    setLabel,
    getLabel,
    getLabelState,
    ensureLabel,
    hydrateKeys,
  };
}
