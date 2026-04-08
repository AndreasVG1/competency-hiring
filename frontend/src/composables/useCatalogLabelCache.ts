import type { ActivityIndicatorCatalogItem } from "../types/domain";
import { useCatalogCacheStore } from "../stores/catalogCache";

type LabelState = "idle" | "loading" | "ready" | "error";

export function useCatalogLabelCache() {
  const catalogCache = useCatalogCacheStore();

  function setLabel(key: string, label: string): void {
    const normalizedKey = key.trim();
    if (!normalizedKey) {
      return;
    }

    catalogCache.setMeta({
      key: normalizedKey,
      label,
      activityIndicatorCount: catalogCache.getActivityIndicatorCount(normalizedKey) ?? 0,
      loadedAt: Date.now(),
    });
  }

  function getLabel(key: string): string | undefined {
    return catalogCache.getLabel(key);
  }

  function getActivityIndicators(key: string): ActivityIndicatorCatalogItem[] | undefined {
    return catalogCache.getActivityIndicators(key);
  }

  function getLabelState(key: string): LabelState {
    return catalogCache.getMetaState(key);
  }

  async function ensureLabel(key: string): Promise<void> {
    return catalogCache.ensureCompetencyMeta([key]);
  }

  async function hydrateKeys(keys: string[]): Promise<void> {
    await catalogCache.ensureCompetencyMeta(keys);
  }

  function getActivityIndicatorCount(key: string): number {
    return catalogCache.getActivityIndicatorCount(key) ?? 0;
  }

  async function ensureActivityIndicators(key: string): Promise<void> {
    await catalogCache.ensureCompetencyDetail(key);
  }

  return {
    setLabel,
    getLabel,
    getActivityIndicators,
    getActivityIndicatorCount,
    getLabelState,
    ensureLabel,
    ensureActivityIndicators,
    hydrateKeys,
  };
}
