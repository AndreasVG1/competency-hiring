export type CompetencyLevel = "beginner" | "intermediate" | "advanced";
export type RequirementPriority = "must_have" | "important" | "nice_to_have";
export type JobOfferStatus = "draft" | "published" | "archived";

export interface ApiErrorDetail {
  field?: string;
  message: string;
}

export interface ApiErrorResponse {
  error: string;
  details: ApiErrorDetail[];
}

export interface CatalogItem {
  key: string;
  label: string;
}

export interface CompetencyCatalogItem extends CatalogItem {
  code: string;
  ekr_level: number | null;
}

export interface OccupationDetail extends CatalogItem {
  required_competencies: CatalogItem[];
}

export interface SeekerProfileUpsertRequest {
  full_name: string;
  summary?: string | null;
  location?: string | null;
  occupation_key?: string | null;
}

export interface SeekerProfileResponse {
  user_id: number;
  full_name: string;
  summary: string | null;
  location: string | null;
  occupation_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface SeekerCompetencyCreateRequest {
  competency_key: string;
  level: CompetencyLevel;
}

export interface SeekerCompetencyUpdateRequest {
  level: CompetencyLevel;
}

export interface SeekerCompetencyResponse {
  id: number;
  competency_key: string;
  level: CompetencyLevel;
}

export interface RecruiterProfileUpsertRequest {
  company_name: string;
  contact_name: string;
}

export interface RecruiterProfileResponse {
  user_id: number;
  company_name: string;
  contact_name: string;
}

export interface JobOfferCreateRequest {
  occupation_key: string;
  description: string;
}

export interface JobOfferUpdateRequest {
  occupation_key?: string | null;
  description?: string | null;
}

export interface JobOfferResponse {
  id: number;
  recruiter_user_id: number;
  title: string;
  occupation_key: string;
  description: string;
  status: JobOfferStatus;
  created_at: string;
  updated_at: string;
}

export interface JobOfferRequirementCreateRequest {
  competency_key: string;
  priority: RequirementPriority;
}

export interface JobOfferRequirementUpdateRequest {
  priority: RequirementPriority;
}

export interface JobOfferRequirementResponse {
  id: number;
  job_offer_id: number;
  competency_key: string;
  priority: RequirementPriority;
}

export interface PublicJobOfferRequirementItem {
  competency_key: string;
  priority: RequirementPriority;
}

export interface PublicJobOfferListItem {
  id: number;
  title: string;
  occupation_key: string;
  occupation_label: string;
  short_description: string;
  company_name: string;
  published_at: string;
}

export interface PublicJobOfferDetail {
  id: number;
  title: string;
  occupation_key: string;
  occupation_label: string;
  description: string;
  company_name: string;
  published_at: string;
  requirements: PublicJobOfferRequirementItem[];
}

export interface ApplicationCreateResponse {
  id: number;
  job_offer_id: number;
  seeker_user_id: number;
  consent_given_at: string;
  created_at: string;
}

export type MatchingResultStatus = "ok" | "ok_with_must_have_gaps" | "not_applicable_no_requirements";
export type MatchingBreakdownStatus = "matched" | "insufficient" | "missing";
export type MatchingReasonCode =
  | "missing_competency"
  | "level_below_expected"
  | "meets_expected_level";

export interface MatchingTotals {
  earned_points: number;
  max_points: number;
  requirements_count: number;
  matched_count: number;
  insufficient_count: number;
  missing_count: number;
}

export interface MatchingWeightsUsed {
  priority_weights: Record<RequirementPriority, number>;
  expected_level_by_priority: Record<RequirementPriority, CompetencyLevel>;
}

export interface MustHaveCoverage {
  total_count: number;
  matched_count: number;
  insufficient_count: number;
  missing_count: number;
  coverage_ratio: number;
}

export interface MatchingBreakdownItem {
  competency_key: string;
  priority: RequirementPriority;
  expected_level: CompetencyLevel;
  seeker_level: CompetencyLevel | null;
  status: MatchingBreakdownStatus;
  earned_points: number;
  max_points: number;
  point_loss: number;
  reason_code: MatchingReasonCode;
}

export interface MissingCompetencyItem {
  competency_key: string;
  priority: RequirementPriority;
  reason_code: MatchingReasonCode;
}

export interface InsufficientCompetencyItem {
  competency_key: string;
  priority: RequirementPriority;
  expected_level: CompetencyLevel;
  seeker_level: CompetencyLevel;
  reason_code: MatchingReasonCode;
}

export interface DevelopmentTargetItem {
  competency_key: string;
  priority: RequirementPriority;
  suggested_target_level: CompetencyLevel;
  point_gain_if_reached: number;
}

export interface PrivateMatchingAnalysisResponse {
  algorithm_version: string;
  scope: string;
  job_offer_id: number;
  seeker_user_id: number;
  score: number;
  status: MatchingResultStatus;
  critical_gap_present: boolean;
  must_have_coverage: MustHaveCoverage;
  totals: MatchingTotals;
  weights_used: MatchingWeightsUsed;
  breakdown: MatchingBreakdownItem[];
  missing_competencies: MissingCompetencyItem[];
  insufficient_competencies: InsufficientCompetencyItem[];
  development_targets: DevelopmentTargetItem[];
}

export interface RecruiterApplicantSnapshotCompetency {
  competency_key: string;
  level: CompetencyLevel;
}

export interface RecruiterApplicantSharedProfile {
  full_name: string;
  summary: string | null;
  location: string | null;
  occupation_key: string | null;
  competencies: RecruiterApplicantSnapshotCompetency[];
}

export interface RecruiterApplicantListItem {
  application_id: number;
  job_offer_id: number;
  seeker_user_id: number;
  consent_given_at: string;
  applied_at: string;
  shared_profile: RecruiterApplicantSharedProfile;
  audit_metadata: Record<string, string> | null;
  snapshot_created_at: string;
  shared_matching: RecruiterApplicantSharedMatching | null;
}

export interface RecruiterApplicantSharedMatching {
  algorithm_version: string;
  score: number;
  snapshot_created_at: string;
  result_payload: Record<string, unknown>;
}
