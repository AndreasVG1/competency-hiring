import { defineStore } from "pinia";
import { reactive } from "vue";

import { catalogClient } from "../api";
import type { ActivityIndicatorCatalogItem, CompetencyCatalogDetail } from "../types/domain";

type LoadState = "idle" | "loading" | "ready" | "error";

interface CompetencyMeta {
  key: string;
  label: string;
  activityIndicatorCount: number;
  loadedAt: number;
}

const RESOLVE_CHUNK_SIZE = 200;
const RESOLVE_MAX_CONCURRENT_CHUNKS = 3;

function normalizeKey(rawKey: string): string {
  return rawKey.trim();
}

function uniquePreserveOrder(rawKeys: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();

  for (const rawKey of rawKeys) {
    const key = normalizeKey(rawKey);
    if (!key) {
      continue;
    }
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(key);
  }

  return result;
}

function chunkKeys(keys: string[], chunkSize: number): string[][] {
  const chunks: string[][] = [];
  for (let index = 0; index < keys.length; index += chunkSize) {
    chunks.push(keys.slice(index, index + chunkSize));
  }
  return chunks;
}

async function runTasksWithConcurrency(tasks: Array<() => Promise<void>>, maxConcurrent: number): Promise<void> {
  const inFlight = new Set<Promise<void>>();

  for (const task of tasks) {
    let promise: Promise<void>;
    promise = task().finally(() => {
      inFlight.delete(promise);
    });

    inFlight.add(promise);

    if (inFlight.size >= maxConcurrent) {
      await Promise.race(inFlight);
    }
  }

  await Promise.all(inFlight);
}

export const useCatalogCacheStore = defineStore("catalogCache", () => {
  const metaByKey = reactive(new Map<string, CompetencyMeta>());
  const detailByKey = reactive(new Map<string, CompetencyCatalogDetail>());

  const metaLoadingKeys = reactive(new Set<string>());
  const metaFailedKeys = reactive(new Set<string>());
  const detailLoadingKeys = reactive(new Set<string>());
  const detailFailedKeys = reactive(new Set<string>());

  const metaInflightByKey = new Map<string, Promise<void>>();
  const detailInflightByKey = new Map<string, Promise<void>>();

  function getMetaState(key: string): LoadState {
    if (metaByKey.has(key)) {
      return "ready";
    }
    if (metaLoadingKeys.has(key)) {
      return "loading";
    }
    if (metaFailedKeys.has(key)) {
      return "error";
    }
    return "idle";
  }

  function getDetailState(key: string): LoadState {
    if (detailByKey.has(key)) {
      return "ready";
    }
    if (detailLoadingKeys.has(key)) {
      return "loading";
    }
    if (detailFailedKeys.has(key)) {
      return "error";
    }
    return "idle";
  }

  function setMeta(meta: CompetencyMeta): void {
    metaByKey.set(meta.key, meta);
    metaFailedKeys.delete(meta.key);
    metaLoadingKeys.delete(meta.key);
  }

  function setDetail(key: string, detail: CompetencyCatalogDetail): void {
    detailByKey.set(key, detail);
    detailFailedKeys.delete(key);
    detailLoadingKeys.delete(key);

    setMeta({
      key,
      label: detail.label,
      activityIndicatorCount: detail.activity_indicators?.length ?? 0,
      loadedAt: Date.now(),
    });
  }

  function getLabel(key: string): string | undefined {
    return metaByKey.get(key)?.label;
  }

  function getActivityIndicatorCount(key: string): number | undefined {
    return metaByKey.get(key)?.activityIndicatorCount;
  }

  function getActivityIndicators(key: string): ActivityIndicatorCatalogItem[] | undefined {
    return detailByKey.get(key)?.activity_indicators;
  }

  async function ensureCompetencyMeta(keys: string[]): Promise<void> {
    const normalizedKeys = uniquePreserveOrder(keys);
    if (!normalizedKeys.length) {
      return;
    }

    const awaitExisting: Promise<void>[] = [];
    const fetchKeys: string[] = [];

    for (const key of normalizedKeys) {
      if (metaByKey.has(key)) {
        continue;
      }

      const inflight = metaInflightByKey.get(key);
      if (inflight) {
        awaitExisting.push(inflight);
        continue;
      }

      fetchKeys.push(key);
    }

    const chunks = chunkKeys(fetchKeys, RESOLVE_CHUNK_SIZE).filter((chunk) => chunk.length > 0);
    const tasks = chunks.map((chunk) => async () => {
      const request = (async () => {
        for (const key of chunk) {
          metaLoadingKeys.add(key);
          metaFailedKeys.delete(key);
        }

        try {
          const response = await catalogClient.resolveCompetencies(chunk);
          const now = Date.now();
          const resolvedKeys = new Set<string>();
          const missingKeys = new Set<string>();

          for (const item of response.items ?? []) {
            const resolvedKey = normalizeKey(item.key);
            if (!resolvedKey) {
              continue;
            }
            resolvedKeys.add(resolvedKey);

            setMeta({
              key: resolvedKey,
              label: item.label,
              activityIndicatorCount: item.activity_indicator_count,
              loadedAt: now,
            });
          }

          for (const missingKey of response.missing_keys ?? []) {
            const resolvedMissingKey = normalizeKey(missingKey);
            if (!resolvedMissingKey) {
              continue;
            }
            missingKeys.add(resolvedMissingKey);
            metaFailedKeys.add(resolvedMissingKey);
          }

          for (const key of chunk) {
            if (metaByKey.has(key) || resolvedKeys.has(key) || missingKeys.has(key)) {
              continue;
            }
            metaFailedKeys.add(key);
          }
        } catch (_error) {
          for (const key of chunk) {
            metaFailedKeys.add(key);
          }
        } finally {
          for (const key of chunk) {
            metaLoadingKeys.delete(key);
            metaInflightByKey.delete(key);
          }
        }
      })();

      for (const key of chunk) {
        metaInflightByKey.set(key, request);
      }
      await request;
    });

    const pending: Promise<void>[] = [];
    if (tasks.length > 0) {
      pending.push(runTasksWithConcurrency(tasks, RESOLVE_MAX_CONCURRENT_CHUNKS));
    }
    if (awaitExisting.length > 0) {
      pending.push(Promise.all(awaitExisting).then(() => undefined));
    }

    if (pending.length > 0) {
      await Promise.all(pending);
    }
  }

  async function ensureCompetencyDetail(competencyKey: string): Promise<void> {
    const key = normalizeKey(competencyKey);
    if (!key || detailByKey.has(key)) {
      return;
    }

    const inflight = detailInflightByKey.get(key);
    if (inflight) {
      return inflight;
    }

    const request = (async () => {
      detailLoadingKeys.add(key);
      detailFailedKeys.delete(key);

      try {
        const detail = await catalogClient.getCompetency(key);
        setDetail(key, detail);
      } catch (_error) {
        detailFailedKeys.add(key);
      } finally {
        detailLoadingKeys.delete(key);
        detailInflightByKey.delete(key);
      }
    })();

    detailInflightByKey.set(key, request);
    return request;
  }

  return {
    metaByKey,
    detailByKey,
    getMetaState,
    getDetailState,
    setMeta,
    setDetail,
    getLabel,
    getActivityIndicatorCount,
    getActivityIndicators,
    ensureCompetencyMeta,
    ensureCompetencyDetail,
  };
});
