<template>
  <section class="d-grid gap-3">
    <header>
      <h3 class="h5 mb-0">{{ summaryTitle }}</h3>
    </header>

    <section class="card bg-light border-0">
      <div class="card-body">
        <p class="fw-semibold mb-1">
          {{ renderSummaryHeadline() }}
        </p>
        <p v-if="pointsSummary !== null" class="text-body-primary mb-2">
          {{ pointsSummary }}
        </p>
        <p class="text-body-secondary mb-2">{{ renderSummaryStatusLabel() }}</p>
        <p v-if="explanation.summary.must_have_notice" class="mb-2 text-danger fw-semibold">
          {{ renderSummaryMustHaveNotice() }}
        </p>
        <p v-if="explanation.summary.no_requirements_notice" class="mb-2 text-primary-emphasis">
          {{ renderSummaryNoRequirementsNotice() }}
        </p>
        <p class="mb-0 text-success-emphasis">
          {{ renderSummaryDecisionSupportNotice() }}
        </p>
      </div>
    </section>

    <section>
      <header class="mb-2">
        <h3 class="h6 mb-0">Tugevused</h3>
      </header>
      <p v-if="explanation.highlights.length === 0" class="text-body-secondary mb-0">
        Praeguse analüüsi põhjal ei ole ühtegi tugevat külge esile toodud.
      </p>
      <div v-else class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th scope="col">Kompetents</th>
              <th scope="col">Prioriteet</th>
              <th scope="col">Detailid</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in explanation.highlights"
              :key="`highlight-${item.competency_key}-${item.priority}-${index}`"
            >
              <td class="text-break">
                <span class="fw-semibold">{{ competencyLabel(item.competency_key) }}</span>
                <span class="d-block small text-body-secondary break-all">{{ item.competency_key }}</span>
              </td>
              <td>{{ humanizePriority(item.priority) }}</td>
              <td class="text-break">{{ renderHighlightText(item) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <header class="mb-2">
        <h3 class="h6 mb-0">Puudujäägid</h3>
      </header>
      <p v-if="explanation.gaps.length === 0" class="text-body-secondary mb-0">
        Praeguse analüüsi põhjal ei ole ühtegi puudujääki tuvastatud.
      </p>
      <div v-else class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th scope="col">Kompetents</th>
              <th scope="col">Tüüp</th>
              <th scope="col">Prioriteet</th>
              <th scope="col">Selgitus</th>
              <th scope="col">Detailid</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in explanation.gaps"
              :key="`gap-${item.competency_key}-${item.priority}-${index}`"
            >
              <td class="text-break">
                <span class="fw-semibold">{{ competencyLabel(item.competency_key) }}</span>
                <span class="d-block small text-body-secondary break-all">{{ item.competency_key }}</span>
              </td>
              <td>{{ humanizeGapKind(item.kind) }}</td>
              <td>{{ humanizePriority(item.priority) }}</td>
              <td class="text-break">{{ formatGapLevelContext(item) }}</td>
              <td class="text-break">{{ renderGapText(item) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="showRoadmap && explanation.development_roadmap !== null">
      <header class="mb-2">
        <h3 class="h6 mb-0">Soovituslik arengutee</h3>
      </header>
      <p v-if="explanation.development_roadmap.length === 0" class="text-body-secondary mb-0">
        Praeguse analüüsi põhjal ei ole kohe rakendatavaid arengueesmärke soovitatud.
      </p>
      <div v-else class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th scope="col">Kompetents</th>
              <th scope="col">Prioriteet</th>
              <th scope="col">Sihttase</th>
              <th scope="col">Punktitulu</th>
              <th scope="col">Detailid</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in explanation.development_roadmap"
              :key="`roadmap-${item.competency_key}-${item.priority}-${index}`"
            >
              <td class="text-break">
                <span class="fw-semibold">{{ competencyLabel(item.competency_key) }}</span>
                <span class="d-block small text-body-secondary break-all">{{ item.competency_key }}</span>
              </td>
              <td>{{ humanizePriority(item.priority) }}</td>
              <td>{{ humanizeCompetencyLevel(item.target_level) }}</td>
              <td>{{ formatPointGain(item.estimated_point_gain) }}</td>
              <td class="text-break">{{ renderRoadmapText(item) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <header class="mb-2">
        <h3 class="h6 mb-0">Märkused</h3>
      </header>
      <ul class="mb-0">
        <li v-for="(note, index) in renderTransparencyNotes()" :key="`transparency-note-${index}`">
          {{ note }}
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type {
  CompetencyLevel,
  ExplanationGapItem,
  ExplanationGapKind,
  ExplanationHighlightItem,
  ExplanationRoadmapItem,
  MatchingTotals,
  MatchingExplanation,
  RequirementPriority,
} from "../types/domain";

interface Props {
  explanation: MatchingExplanation;
  competencyLabel: (competencyKey: string) => string;
  totals?: MatchingTotals | null;
  showRoadmap?: boolean;
  summaryTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
  totals: null,
  showRoadmap: true,
  summaryTitle: "Analüüsi kokkuvõte",
});

const explanation = computed(() => props.explanation);
const competencyLabel = props.competencyLabel;
const totals = computed(() => props.totals);
const showRoadmap = computed(() => props.showRoadmap);
const summaryTitle = computed(() => props.summaryTitle);

const PRIORITY_ET: Record<RequirementPriority, string> = {
  must_have: "Kohustuslik",
  important: "Oluline",
  nice_to_have: "Soovituslik",
};

const GAP_KIND_ET: Record<ExplanationGapKind, string> = {
  missing: "Puudub",
  insufficient: "Mittevastav",
};

const COMPETENCY_LEVEL_ET: Record<CompetencyLevel, string> = {
  beginner: "Algaja",
  intermediate: "Kesktase",
  advanced: "Edasijõudnu",
};

function humanizeFallbackToken(value: string): string {
  const normalized = value.replace(/_/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function humanizePriority(value: RequirementPriority | string): string {
  return PRIORITY_ET[value as RequirementPriority] ?? humanizeFallbackToken(value);
}

function humanizeGapKind(value: ExplanationGapKind | string): string {
  return GAP_KIND_ET[value as ExplanationGapKind] ?? humanizeFallbackToken(value);
}

function humanizeCompetencyLevel(value: CompetencyLevel | string): string {
  return COMPETENCY_LEVEL_ET[value as CompetencyLevel] ?? humanizeFallbackToken(value);
}

function getParamString(params: Record<string, unknown> | null | undefined, key: string): string | null {
  const value = params?.[key];
  if (value === null || value === undefined) {
    return null;
  }
  return String(value);
}

function getParamNumber(params: Record<string, unknown> | null | undefined, key: string): number | null {
  const value = params?.[key];
  if (value === null || value === undefined) {
    return null;
  }
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function renderSummaryHeadline(): string {
  const code = explanation.value.summary.headline_code;
  if (code === "summary.headline.score_out_of_100") {
    const score = getParamNumber(explanation.value.summary.headline_params, "score");
    if (score !== null) {
      return `Praegune sobivuse skoor: ${score.toFixed(1)}/100.`;
    }
  }
  return explanation.value.summary.headline;
}

const pointsSummary = computed(() => {
  const snapshot = totals.value;
  if (!snapshot) {
    return null;
  }
  if (!Number.isFinite(snapshot.max_points) || snapshot.max_points <= 0) {
    return null;
  }
  return `Punktid: ${snapshot.earned_points.toFixed(1)}/${snapshot.max_points.toFixed(1)}`;
});

function renderSummaryStatusLabel(): string {
  const code = explanation.value.summary.status_code;
  switch (code) {
    case "summary.status.ok":
      return "Praegune profiili sobivus on piisav.";
    case "summary.status.ok_with_must_have_gaps":
      return "Kohustuslikes kompetentsides on puudujääke, mis vajavad tähelepanu.";
    case "summary.status.not_applicable_no_requirements":
      return "Sellele pakkumisele pole nõudeid määratud.";
    default:
      return explanation.value.summary.status_label;
  }
}

function renderSummaryDecisionSupportNotice(): string {
  const code = explanation.value.summary.decision_support_notice_code;
  if (code === "summary.notice.decision_support") {
    return "See analüüs toetab sinu otsust ega tee värbamisotsuseid.";
  }
  return explanation.value.summary.decision_support_notice;
}

function renderSummaryMustHaveNotice(): string {
  const code = explanation.value.summary.must_have_notice_code;
  if (code === "summary.notice.must_have_gap") {
    return "Vähemalt üks kohustuslik kompetents on hetkel puudu.";
  }
  return explanation.value.summary.must_have_notice ?? "";
}

function renderSummaryNoRequirementsNotice(): string {
  const code = explanation.value.summary.no_requirements_notice_code;
  if (code === "summary.notice.no_requirements") {
    return (
      "Sellel tööpakkumisel ei ole kompetentsinõudeid, seega sobivuse skoori arvutamine polnud võimalik."
    );
  }
  return explanation.value.summary.no_requirements_notice ?? "";
}

function renderHighlightText(item: ExplanationHighlightItem): string {
  const code = item.text_code;
  if (code === "highlight.matched_expected_level") {
    const priority = getParamString(item.text_params, "priority") ?? item.priority;
    return `Vastab oodatud tasemele (${humanizePriority(priority)}).`;
  }
  return item.text;
}

function renderGapText(item: ExplanationGapItem): string {
  const code = item.text_code;
  if (code === "gap.missing_competency") {
    const priority = getParamString(item.text_params, "priority") ?? item.priority;
    return `Puudub ${humanizePriority(priority).toLowerCase()} kompetents.`;
  }
  if (code === "gap.level_below_expected") {
    return "Kompetentsi tase on liiga madal.";
  }
  if (code === "gap.generic") {
    return "Tuvastati puudujääk.";
  }
  return item.text;
}

function renderRoadmapText(item: ExplanationRoadmapItem): string {
  const code = item.text_code;
  if (code === "roadmap.improve_to_level_recover_points") {
    const pointGain = getParamNumber(item.text_params, "point_gain") ?? item.estimated_point_gain;
    const targetLevel = getParamString(item.text_params, "target_level") ?? item.target_level;
    return `Kui arendad kompetentsi tasemele ${humanizeCompetencyLevel(targetLevel)}, võid teenida ${formatPointGain(
      pointGain,
    )}.`;
  }
  return item.text;
}

function formatGapLevelContext(item: ExplanationGapItem): string {
  if (item.kind === "missing") {
    return "Kompetents puudub.";
  }

  const currentLevel = item.current_level
    ? humanizeCompetencyLevel(item.current_level)
    : "Tundmatu praegune tase";
  const expectedLevel = item.expected_level
    ? humanizeCompetencyLevel(item.expected_level)
    : "Tundmatu oodatud tase";
  return `${currentLevel} vs oodatud ${expectedLevel}.`;
}

function formatPointGain(value: number): string {
  return `+${value.toFixed(1)} punkti`;
}

function renderTransparencyNotes(): string[] {
  const i18nNotes = explanation.value.transparency_notes_i18n;
  if (!i18nNotes || i18nNotes.length === 0) {
    return explanation.value.transparency_notes;
  }

  return i18nNotes.map((note: { code: string; params?: Record<string, unknown> | null }, index: number) => {
    const fallback = explanation.value.transparency_notes[index] ?? note.code;
    switch (note.code) {
      case "transparency.exact_key_matching_only":
        return "Ainult täpne kompetentsivõtme vastavus.";
      case "transparency.deterministic_priority_weights_and_levels":
        return "Prioriteedikaalud ja oodatud tasemed on deterministlikud.";
      case "transparency.no_semantic_inference":
        return "Semantilist järeldamist ega varjatud skoorimist ei kasutata.";
      case "transparency.unknown_algorithm_version": {
        const version = getParamString(note.params ?? null, "algorithm_version") ?? "tundmatu";
        return `Algoritmi versiooni (${version}) jaoks puuduvad detailsemad selgitusmallid; kuvatakse minimaalne kokkuvõte.`;
      }
      default:
        return fallback;
    }
  });
}
</script>
