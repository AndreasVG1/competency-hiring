import { apiRequest } from "./httpClient";
import type {
  CatalogItem,
  CompetencyResolveResponse,
  CompetencyCatalogDetail,
  CompetencyCatalogItem,
  OccupationDetail,
} from "../types/domain";

const CATALOG_BASE_PATH = "/api/v1/catalog";

interface CatalogSearchParams {
  query?: string;
  limit?: number;
}

interface RequestControlOptions {
  signal?: AbortSignal;
}

export const catalogClient = {
  listCompetencies(
    params: CatalogSearchParams = {},
    options: RequestControlOptions = {},
  ): Promise<CompetencyCatalogItem[]> {
    return apiRequest<CompetencyCatalogItem[]>(`${CATALOG_BASE_PATH}/competencies`, {
      query: {
        query: params.query,
        limit: params.limit,
      },
      signal: options.signal,
    });
  },

  getCompetency(competencyKey: string): Promise<CompetencyCatalogDetail> {
    return apiRequest<CompetencyCatalogDetail>(
      `${CATALOG_BASE_PATH}/competencies/${encodeURIComponent(competencyKey)}`,
    );
  },

  resolveCompetencies(keys: string[]): Promise<CompetencyResolveResponse> {
    return apiRequest<CompetencyResolveResponse>(`${CATALOG_BASE_PATH}/competencies/resolve`, {
      method: "POST",
      body: { keys },
    });
  },

  listOccupations(params: CatalogSearchParams = {}, options: RequestControlOptions = {}): Promise<CatalogItem[]> {
    return apiRequest<CatalogItem[]>(`${CATALOG_BASE_PATH}/occupations`, {
      query: {
        query: params.query,
        limit: params.limit,
      },
      signal: options.signal,
    });
  },

  getOccupation(occupationKey: string): Promise<OccupationDetail> {
    return apiRequest<OccupationDetail>(
      `${CATALOG_BASE_PATH}/occupations/${encodeURIComponent(occupationKey)}`,
    );
  },
};
