<template>
  <main class="recruiter-page">
    <section class="panel recruiter-panel">
      <PageActionsBar>
        <RouterLink class="button-secondary" :to="backToOfferPath">Back to offer</RouterLink>
      </PageActionsBar>

      <header class="panel-header">
        <p class="eyebrow">Recruiter Area</p>
        <h1>Offer Applicants</h1>
        <p class="content">
          Applicants appear only after explicit seeker consent through application.
        </p>
      </header>

      <section class="recruiter-section">
        <header class="section-header">
          <h2>Offer</h2>
          <p>Applicant data below is shared as an application-time snapshot.</p>
        </header>

        <ApiErrorNotice v-if="offerLoadError" :error="offerLoadError" show-all-messages />

        <p v-if="isOfferLoading" class="section-note">Loading offer...</p>
        <p v-else-if="isOfferNotFound" class="section-note">Job offer not found.</p>
        <template v-else-if="jobOffer">
          <dl class="summary-grid">
            <dt>Title</dt>
            <dd>{{ jobOffer.title }}</dd>
            <dt>Status</dt>
            <dd><JobOfferStatusBadge :status="jobOffer.status" /></dd>
            <dt>Occupation key</dt>
            <dd>{{ jobOffer.occupation_key }}</dd>
          </dl>
        </template>
      </section>

      <section v-if="!isOfferNotFound" class="recruiter-section">
        <header class="section-header">
          <h2>Applicants</h2>
          <p>Only candidates who applied to this offer are visible.</p>
        </header>

        <ApiErrorNotice v-if="applicantsLoadError" :error="applicantsLoadError" show-all-messages />

        <p v-if="isApplicantsLoading" class="section-note">Loading applicants...</p>
        <p v-else-if="applicants.length === 0" class="section-note">No applicants yet.</p>
        <template v-else>
          <div class="applicants-toolbar">
            <label class="form-field applicants-sort">
              <span>Sort by</span>
              <select v-model="applicantSort" class="enum-select">
                <option value="score_desc">Score (high to low)</option>
                <option value="applied_desc">Date applied (newest first)</option>
              </select>
            </label>
          </div>

          <ul class="applicants-list">
            <li
              v-for="applicant in sortedApplicants"
              :key="applicant.application_id"
              class="applicant-card"
            >
              <header class="applicant-card-header">
                <div class="applicant-card-title-row">
                  <h3 class="applicant-card-title">{{ applicant.shared_profile.full_name }}</h3>
                  <p class="applicant-score-pill">
                    Score:
                    <strong>{{ formatApplicantScore(applicant) }}</strong>
                  </p>
                </div>
              </header>

              <dl class="summary-grid">
                <dt>Applied at</dt>
                <dd>{{ formatDateTime(applicant.applied_at) }}</dd>
                <dt>Summary</dt>
                <dd>{{ applicant.shared_profile.summary || "Not provided" }}</dd>
              </dl>

              <button
                type="button"
                class="button-secondary applicant-toggle-button"
                :aria-expanded="isApplicantExpanded(applicant.application_id)"
                :aria-controls="applicantDetailsId(applicant.application_id)"
                @click="toggleApplicantDetails(applicant.application_id)"
              >
                {{ isApplicantExpanded(applicant.application_id) ? "Hide details" : "View details" }}
              </button>

              <div
                v-if="isApplicantExpanded(applicant.application_id)"
                :id="applicantDetailsId(applicant.application_id)"
                class="applicant-expanded-content"
              >
                <dl class="summary-grid">
                  <dt>Occupation key</dt>
                  <dd>{{ applicant.shared_profile.occupation_key || "Not provided" }}</dd>
                  <dt>Location</dt>
                  <dd>{{ applicant.shared_profile.location || "Not provided" }}</dd>
                </dl>

                <section>
                  <header class="subsection-header">
                    <h3>Shared competencies</h3>
                    <p>Competency values shown here come from the stored application snapshot.</p>
                  </header>

                  <p v-if="applicant.shared_profile.competencies.length === 0" class="section-note">
                    No competencies were shared.
                  </p>
                  <table v-else class="competency-table">
                    <thead>
                      <tr>
                        <th>Competency</th>
                        <th>Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(competency, competencyIndex) in applicant.shared_profile.competencies"
                        :key="`${applicant.application_id}-${competency.competency_key}-${competencyIndex}`"
                      >
                        <td>{{ competencyLabel(competency.competency_key) }}</td>
                        <td>{{ competency.level }}</td>
                      </tr>
                    </tbody>
                  </table>
                </section>

                <section>
                  <header class="subsection-header">
                    <h3>Shared matching result</h3>
                    <p>This result was shared at application time as part of consent.</p>
                  </header>

                  <template v-if="applicant.shared_matching">
                    <dl class="summary-grid">
                      <dt>Score</dt>
                      <dd>{{ formatScore(applicant.shared_matching.score) }}</dd>
                      <dt>Algorithm version</dt>
                      <dd>{{ applicant.shared_matching.algorithm_version }}</dd>
                      <dt>Matching snapshot created at</dt>
                      <dd>{{ formatDateTime(applicant.shared_matching.snapshot_created_at) }}</dd>
                    </dl>

                    <MatchingExplanationPanel
                      v-if="applicant.shared_matching.explanation"
                      summary-title="Shared match explanation"
                      :explanation="applicant.shared_matching.explanation"
                      :competency-label="competencyLabel"
                      :show-roadmap="false"
                    />
                    <p v-else class="section-note">
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
                  <p v-else class="section-note">
                    No shared matching snapshot is available for this application.
                  </p>
                </section>
              </div>
            </li>
          </ul>
        </template>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { ApiClientError, recruiterClient } from "../../api";
import ApiErrorNotice from "../../components/ApiErrorNotice.vue";
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
  }

  return [...keys];
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
