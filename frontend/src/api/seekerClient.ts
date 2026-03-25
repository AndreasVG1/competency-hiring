import { apiRequest } from "./httpClient";
import type {
  SeekerCompetencyCreateRequest,
  SeekerCompetencyResponse,
  SeekerCompetencyUpdateRequest,
  SeekerProfileResponse,
  SeekerProfileUpsertRequest,
} from "../types/domain";

const SEEKER_BASE_PATH = "/api/v1/seeker";

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
};

