<template>
  <div class="d-grid gap-4">
    <PageActionsBar>
      <RouterLink class="btn btn-outline-secondary" :to="backToOfferPath">Back to offer</RouterLink>
    </PageActionsBar>

    <header>
      <p class="text-uppercase small text-body-secondary fw-semibold mb-1">Recruiter Area</p>
      <h1 class="h3 mb-1">Offer Applicants</h1>
      <p class="text-body-secondary mb-0">
        Applicants appear only after explicit seeker consent through application.
      </p>
    </header>

    <section class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Offer</h2>
        <p class="text-body-secondary mb-0">Applicant data below is shared as an application-time snapshot.</p>
      </header>

      <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />

      <p v-if="isOfferLoading" class="text-body-secondary mb-0">Loading offer...</p>
      <p v-else-if="isOfferNotFound" class="text-body-secondary mb-0">Job offer not found.</p>
      <template v-else-if="jobOffer">
        <dl class="row mb-0">
          <dt class="col-sm-3 text-body-secondary">Title</dt>
          <dd class="col-sm-9 text-break">{{ jobOffer.title }}</dd>
          <dt class="col-sm-3 text-body-secondary">Status</dt>
          <dd class="col-sm-9"><JobOfferStatusBadge :status="jobOffer.status" /></dd>
          <dt class="col-sm-3 text-body-secondary">Occupation key</dt>
          <dd class="col-sm-9 text-break break-all">{{ jobOffer.occupation_key }}</dd>
        </dl>
      </template>
    </section>

    <section v-if="!isOfferNotFound" class="border rounded-3 bg-white p-3 d-grid gap-3">
      <header>
        <h2 class="h5 mb-1">Applicants</h2>
        <p class="text-body-secondary mb-0">Only candidates who applied to this offer are visible.</p>
      </header>

      <ApiErrorNotice v-if="applicantsLoadError" :error="applicantsLoadError" show-all-messages />

      <p v-if="isApplicantsLoading" class="text-body-secondary mb-0">Loading applicants...</p>
      <p v-else-if="applicants.length === 0" class="text-body-secondary mb-0">No applicants yet.</p>
      <template v-else>
        <div class="row g-3 align-items-end">
          <div class="col-12 col-md-5 col-lg-4">
            <label class="d-grid gap-1">
              <span class="form-label mb-0">Sort by</span>
              <select v-model="applicantSort" class="form-select">
                <option value="score_desc">Score (high to low)</option>
                <option value="applied_desc">Date applied (newest first)</option>
              </select>
            </label>
          </div>
        </div>

        <ul class="list-group">
          <li v-for="applicant in sortedApplicants" :key="applicant.application_id" class="list-group-item">
            <div class="d-flex justify-content-between align-items-start gap-3">
              <div class="min-w-0">
                <div class="d-flex flex-wrap align-items-center gap-2">
                  <h3 class="h6 mb-0 text-break">{{ applicant.shared_profile.full_name }}</h3>
                  <span class="badge text-bg-primary">
                    Score: {{ formatApplicantScore(applicant) }}
                  </span>
                </div>
              </div>
            </div>

            <dl class="row mb-0 mt-2">
              <dt class="col-sm-3 text-body-secondary">Applied at</dt>
              <dd class="col-sm-9 text-break">{{ formatDateTime(applicant.applied_at) }}</dd>
              <dt class="col-sm-3 text-body-secondary">Summary</dt>
              <dd class="col-sm-9 text-break">{{ applicant.shared_profile.summary || "Not provided" }}</dd>
            </dl>

            <button
              type="button"
              class="btn btn-outline-secondary btn-sm mt-2"
              :aria-expanded="isApplicantExpanded(applicant.application_id)"
              :aria-controls="applicantDetailsId(applicant.application_id)"
              @click="toggleApplicantDetails(applicant.application_id)"
            >
              {{ isApplicantExpanded(applicant.application_id) ? "Hide details" : "View details" }}
            </button>

            <div
              v-if="isApplicantExpanded(applicant.application_id)"
              :id="applicantDetailsId(applicant.application_id)"
              class="d-grid gap-3 mt-3"
            >
              <dl class="row mb-0">
                <dt class="col-sm-3 text-body-secondary">Occupation key</dt>
                <dd class="col-sm-9 text-break break-all">{{ applicant.shared_profile.occupation_key || "Not provided" }}</dd>
                <dt class="col-sm-3 text-body-secondary">Location</dt>
                <dd class="col-sm-9 text-break">{{ applicant.shared_profile.location || "Not provided" }}</dd>
              </dl>

              <section class="d-grid gap-2">
                <header>
                  <h3 class="h6 mb-1">Shared competencies</h3>
                  <p class="text-body-secondary mb-0">
                    Competency values shown here come from the stored application snapshot.
                  </p>
                </header>

                <CompetencyLevelTable
                  :rows="toSharedCompetencyRows(applicant)"
                  empty-text="No competencies were shared."
                  :label-resolver="competencyLabel"
                />
              </section>

              <section class="d-grid gap-2">
                <header>
                  <h3 class="h6 mb-1">Shared matching result</h3>
                  <p class="text-body-secondary mb-0">This result was shared at application time as part of consent.</p>
                </header>

                <template v-if="applicant.shared_matching">
                  <dl class="row mb-0">
                    <dt class="col-sm-3 text-body-secondary">Score</dt>
                    <dd class="col-sm-9 text-break">{{ formatScore(applicant.shared_matching.score) }}</dd>
                    <dt class="col-sm-3 text-body-secondary">Algorithm version</dt>
                    <dd class="col-sm-9 text-break break-all">{{ applicant.shared_matching.algorithm_version }}</dd>
                    <dt class="col-sm-3 text-body-secondary">Matching snapshot created at</dt>
                    <dd class="col-sm-9 text-break">{{ formatDateTime(applicant.shared_matching.snapshot_created_at) }}</dd>
                  </dl>

                  <MatchingExplanationPanel
                    v-if="applicant.shared_matching.explanation"
                    summary-title="Shared match explanation"
                    :explanation="applicant.shared_matching.explanation"
                    :competency-label="competencyLabel"
                    :show-roadmap="false"
                  />
                  <p v-else class="text-body-secondary mb-0">
                    Structured explanation is unavailable for this shared matching snapshot.
                  </p>

                  <details class="matching-disclosure">
                    <summary class="matching-disclosure-summary">
                      <span class="matching-disclosure-closed-label">Show matching payload</span>
                      <span class="matching-disclosure-open-label">Hide matching payload</span>
                    </summary>

                    <JsonPayloadViewer
                      title="Snapshot matching payload"
                      :payload="applicant.shared_matching.result_payload"
                    />
                  </details>
                </template>
                <p v-else class="text-body-secondary mb-0">
                  No shared matching snapshot is available for this application.
                </p>
              </section>
            </div>
          </li>
        </ul>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
import CompetencyLevelTable from "../../components/CompetencyLevelTable.vue";
import JobOfferStatusBadge from "../../components/JobOfferStatusBadge.vue";
import JsonPayloadViewer from "../../components/JsonPayloadViewer.vue";
import MatchingExplanationPanel from "../../components/MatchingExplanationPanel.vue";
import PageActionsBar from "../../components/PageActionsBar.vue";
import { useCatalogLabelCache } from "../../composables/useCatalogLabelCache";
import type { JobOfferResponse, RecruiterApplicantListItem } from "../../types/domain";

const route = useRoute();
const labelCache = useCatalogLabelCache();

type ApplicantSort = "score_desc" | "applied_desc";

const jobOffer = ref<JobOfferResponse | null>(null);
const applicants = ref<RecruiterApplicantListItem[]>([]);
const applicantSort = ref<ApplicantSort>("score_desc");
const expandedApplicationId = ref<number | null>(null);

const isOfferLoading = ref(true);
const isApplicantsLoading = ref(false);
const isOfferNotFound = ref(false);

const offerLoadError = ref<unknown | null>(null);
const applicantsLoadError = ref<unknown | null>(null);

const sortedApplicants = computed<RecruiterApplicantListItem[]>(() => {
  const items = [...applicants.value];

  items.sort((left, right) => {
    if (applicantSort.value === "score_desc") {
      const scoreComparison = compareScoreDesc(left, right);
      if (scoreComparison !== 0) {
        return scoreComparison;
      }
    } else {
      const appliedComparison = compareAppliedDateDesc(left, right);
      if (appliedComparison !== 0) {
        return appliedComparison;
      }
    }

    const appliedTieBreaker = compareAppliedDateDesc(left, right);
    if (appliedTieBreaker !== 0) {
      return appliedTieBreaker;
    }

    return right.application_id - left.application_id;
  });

  return items;
});

const backToOfferPath = computed(() => {
  const offerId = parseOfferId();
  if (offerId === null) {
    return "/recruiter";
  }
  return `/recruiter/job-offers/${offerId}`;
});

function parseOfferId(): number | null {
  const offerId = Number(route.params.id);
  if (!Number.isInteger(offerId) || offerId <= 0) {
    return null;
  }
  return offerId;
}

function competencyLabel(competencyKey: string): string {
  const label = labelCache.getLabel(competencyKey);
  if (label) {
    return label;
  }

  const state = labelCache.getLabelState(competencyKey);
  if (state === "error") {
    return "Label unavailable";
  }

  return competencyKey;
}

function formatDateTime(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(parsed));
}

function formatScore(value: number): string {
  return value.toFixed(1);
}

function formatApplicantScore(applicant: RecruiterApplicantListItem): string {
  if (applicant.shared_matching === null) {
    return "No score available";
  }
  return formatScore(applicant.shared_matching.score);
}

function isApplicantExpanded(applicationId: number): boolean {
  return expandedApplicationId.value === applicationId;
}

function applicantDetailsId(applicationId: number): string {
  return `applicant-details-${applicationId}`;
}

function toggleApplicantDetails(applicationId: number): void {
  if (expandedApplicationId.value === applicationId) {
    expandedApplicationId.value = null;
    return;
  }
  expandedApplicationId.value = applicationId;
}

function parseTimestampForSort(value: string): number {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return Number.NEGATIVE_INFINITY;
  }
  return parsed;
}

function compareAppliedDateDesc(
  left: RecruiterApplicantListItem,
  right: RecruiterApplicantListItem,
): number {
  return parseTimestampForSort(right.applied_at) - parseTimestampForSort(left.applied_at);
}

function compareScoreDesc(
  left: RecruiterApplicantListItem,
  right: RecruiterApplicantListItem,
): number {
  const leftScore = left.shared_matching?.score ?? null;
  const rightScore = right.shared_matching?.score ?? null;

  if (leftScore === null && rightScore === null) {
    return 0;
  }
  if (leftScore === null) {
    return 1;
  }
  if (rightScore === null) {
    return -1;
  }

  return rightScore - leftScore;
}

function collectApplicantCompetencyKeys(loadedApplicants: RecruiterApplicantListItem[]): string[] {
  const keys = new Set<string>();

  for (const applicant of loadedApplicants) {
    for (const competency of applicant.shared_profile.competencies) {
      keys.add(competency.competency_key);
    }

    const explanation = applicant.shared_matching?.explanation;
    if (!explanation) {
      continue;
    }

    for (const item of explanation.highlights) {
      keys.add(item.competency_key);
    }

    for (const item of explanation.gaps) {
      keys.add(item.competency_key);
    }

    for (const item of explanation.development_roadmap ?? []) {
      keys.add(item.competency_key);
    }
  }

  return [...keys];
}

function toSharedCompetencyRows(applicant: RecruiterApplicantListItem) {
  return applicant.shared_profile.competencies.map((competency, index) => ({
    id: `${applicant.application_id}-${competency.competency_key}-${index}`,
    competency_key: competency.competency_key,
    level: competency.level,
  }));
}

async function loadApplicants(): Promise<void> {
  const offerId = parseOfferId();
  if (offerId === null) {
    isOfferNotFound.value = true;
    offerLoadError.value = "Invalid job offer id.";
    isOfferLoading.value = false;
    return;
  }

  isOfferLoading.value = true;
  isApplicantsLoading.value = false;
  isOfferNotFound.value = false;
  offerLoadError.value = null;
  applicantsLoadError.value = null;
  jobOffer.value = null;
  applicants.value = [];
  expandedApplicationId.value = null;

  try {
    jobOffer.value = await recruiterClient.getJobOffer(offerId);
  } catch (error) {
    if (error instanceof ApiClientError && error.statusCode === 404) {
      isOfferNotFound.value = true;
      return;
    }
    offerLoadError.value = error;
    return;
  } finally {
    isOfferLoading.value = false;
  }

  isApplicantsLoading.value = true;
  try {
    const loadedApplicants = await recruiterClient.listApplicants(offerId);
    applicants.value = loadedApplicants;
    const competencyKeys = collectApplicantCompetencyKeys(loadedApplicants);
    if (competencyKeys.length > 0) {
      void labelCache.hydrateKeys(competencyKeys);
    }
  } catch (error) {
    applicantsLoadError.value = error;
  } finally {
    isApplicantsLoading.value = false;
  }
}

onMounted(async () => {
  await loadApplicants();
});
</script>
