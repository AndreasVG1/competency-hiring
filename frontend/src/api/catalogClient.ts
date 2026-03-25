import { apiRequest } from "./httpClient";
import type { CatalogItem, CompetencyCatalogItem, OccupationDetail } from "../types/domain";

const CATALOG_BASE_PATH = "/api/v1/catalog";

interface CatalogSearchParams {
  query?: string;
  limit?: number;
}

export const catalogClient = {
  listCompetencies(params: CatalogSearchParams = {}): Promise<CompetencyCatalogItem[]> {
    return apiRequest<CompetencyCatalogItem[]>(`${CATALOG_BASE_PATH}/competencies`, {
      query: {
        query: params.query,
        limit: params.limit,
      },
    });
  },

  getCompetency(competencyKey: string): Promise<CompetencyCatalogItem> {
    return apiRequest<CompetencyCatalogItem>(
      `${CATALOG_BASE_PATH}/competencies/${encodeURIComponent(competencyKey)}`,
    );
  },

  listOccupations(params: CatalogSearchParams = {}): Promise<CatalogItem[]> {
    return apiRequest<CatalogItem[]>(`${CATALOG_BASE_PATH}/occupations`, {
      query: {
        query: params.query,
        limit: params.limit,
      },
    });
  },

  getOccupation(occupationKey: string): Promise<OccupationDetail> {
    return apiRequest<OccupationDetail>(
      `${CATALOG_BASE_PATH}/occupations/${encodeURIComponent(occupationKey)}`,
    );
  },
};
