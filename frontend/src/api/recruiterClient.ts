import { apiRequest } from "./httpClient";
import type {
  JobOfferCreateRequest,
  JobOfferRequirementCreateRequest,
  JobOfferRequirementResponse,
  JobOfferRequirementUpdateRequest,
  JobOfferResponse,
  JobOfferUpdateRequest,
  RecruiterProfileResponse,
  RecruiterProfileUpsertRequest,
} from "../types/domain";

const RECRUITER_BASE_PATH = "/api/v1/recruiter";

export const recruiterClient = {
  getProfile(): Promise<RecruiterProfileResponse> {
    return apiRequest<RecruiterProfileResponse>(`${RECRUITER_BASE_PATH}/profile`);
  },

  upsertProfile(payload: RecruiterProfileUpsertRequest): Promise<RecruiterProfileResponse> {
    return apiRequest<RecruiterProfileResponse>(`${RECRUITER_BASE_PATH}/profile`, {
      method: "PUT",
      body: payload,
    });
  },

  listJobOffers(): Promise<JobOfferResponse[]> {
    return apiRequest<JobOfferResponse[]>(`${RECRUITER_BASE_PATH}/job-offers`);
  },

  createJobOffer(payload: JobOfferCreateRequest): Promise<JobOfferResponse> {
    return apiRequest<JobOfferResponse>(`${RECRUITER_BASE_PATH}/job-offers`, {
      method: "POST",
      body: payload,
    });
  },

  getJobOffer(jobOfferId: number): Promise<JobOfferResponse> {
    return apiRequest<JobOfferResponse>(`${RECRUITER_BASE_PATH}/job-offers/${jobOfferId}`);
  },

  updateJobOffer(jobOfferId: number, payload: JobOfferUpdateRequest): Promise<JobOfferResponse> {
    return apiRequest<JobOfferResponse>(`${RECRUITER_BASE_PATH}/job-offers/${jobOfferId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  listRequirements(jobOfferId: number): Promise<JobOfferRequirementResponse[]> {
    return apiRequest<JobOfferRequirementResponse[]>(
      `${RECRUITER_BASE_PATH}/job-offers/${jobOfferId}/requirements`,
    );
  },

  addRequirement(
    jobOfferId: number,
    payload: JobOfferRequirementCreateRequest,
  ): Promise<JobOfferRequirementResponse> {
    return apiRequest<JobOfferRequirementResponse>(
      `${RECRUITER_BASE_PATH}/job-offers/${jobOfferId}/requirements`,
      {
        method: "POST",
        body: payload,
      },
    );
  },

  updateRequirement(
    jobOfferId: number,
    requirementId: number,
    payload: JobOfferRequirementUpdateRequest,
  ): Promise<JobOfferRequirementResponse> {
    return apiRequest<JobOfferRequirementResponse>(
      `${RECRUITER_BASE_PATH}/job-offers/${jobOfferId}/requirements/${requirementId}`,
      {
        method: "PATCH",
        body: payload,
      },
    );
  },

  deleteRequirement(jobOfferId: number, requirementId: number): Promise<void> {
    return apiRequest<void>(
      `${RECRUITER_BASE_PATH}/job-offers/${jobOfferId}/requirements/${requirementId}`,
      {
        method: "DELETE",
      },
    );
  },
};

