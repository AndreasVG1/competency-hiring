import { apiRequest } from "./httpClient";
import type {
  PublicJobOfferDetail,
  PublicJobOfferListItem,
  SeekerCompetencyCreateRequest,
  SeekerCompetencyResponse,
  SeekerCompetencyUpdateRequest,
  SeekerProfileResponse,
  SeekerProfileUpsertRequest,
} from "../types/domain";

const SEEKER_BASE_PATH = "/api/v1/seeker";

interface PublishedJobOffersListParams {
  query?: string;
  occupation_key?: string;
  limit?: number;
  offset?: number;
}

export const seekerClient = {
  getProfile(): Promise<SeekerProfileResponse> {
    return apiRequest<SeekerProfileResponse>(`${SEEKER_BASE_PATH}/profile`);
  },

  upsertProfile(payload: SeekerProfileUpsertRequest): Promise<SeekerProfileResponse> {
    return apiRequest<SeekerProfileResponse>(`${SEEKER_BASE_PATH}/profile`, {
      method: "PUT",
      body: payload,
    });
  },

  deleteProfile(): Promise<void> {
    return apiRequest<void>(`${SEEKER_BASE_PATH}/profile`, {
      method: "DELETE",
    });
  },

  listCompetencies(): Promise<SeekerCompetencyResponse[]> {
    return apiRequest<SeekerCompetencyResponse[]>(`${SEEKER_BASE_PATH}/competencies`);
  },

  createCompetency(payload: SeekerCompetencyCreateRequest): Promise<SeekerCompetencyResponse> {
    return apiRequest<SeekerCompetencyResponse>(`${SEEKER_BASE_PATH}/competencies`, {
      method: "POST",
      body: payload,
    });
  },

  updateCompetency(
    competencyId: number,
    payload: SeekerCompetencyUpdateRequest,
  ): Promise<SeekerCompetencyResponse> {
    return apiRequest<SeekerCompetencyResponse>(
      `${SEEKER_BASE_PATH}/competencies/${competencyId}`,
      {
        method: "PATCH",
        body: payload,
      },
    );
  },

  deleteCompetency(competencyId: number): Promise<void> {
    return apiRequest<void>(`${SEEKER_BASE_PATH}/competencies/${competencyId}`, {
      method: "DELETE",
    });
  },

  listPublishedJobOffers(params: PublishedJobOffersListParams = {}): Promise<PublicJobOfferListItem[]> {
    return apiRequest<PublicJobOfferListItem[]>(`${SEEKER_BASE_PATH}/job-offers`, {
      query: {
        query: params.query,
        occupation_key: params.occupation_key,
        limit: params.limit,
        offset: params.offset,
      },
    });
  },

  getPublishedJobOffer(jobOfferId: number): Promise<PublicJobOfferDetail> {
    return apiRequest<PublicJobOfferDetail>(`${SEEKER_BASE_PATH}/job-offers/${jobOfferId}`);
  },
};
