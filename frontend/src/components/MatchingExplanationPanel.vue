<template>
  <section class="d-grid gap-3">
    <header>
      <h3 class="h5 mb-0">{{ summaryTitle }}</h3>
    </header>

    <section class="card bg-light border-0">
      <div class="card-body">
        <p class="fw-semibold mb-1">{{ explanation.summary.headline }}</p>
        <p class="text-body-secondary mb-2">{{ explanation.summary.status_label }}</p>
        <p v-if="explanation.summary.must_have_notice" class="mb-2 text-danger fw-semibold">
          {{ explanation.summary.must_have_notice }}
        </p>
        <p v-if="explanation.summary.no_requirements_notice" class="mb-2 text-primary-emphasis">
          {{ explanation.summary.no_requirements_notice }}
        </p>
        <p class="mb-0 text-success-emphasis">
          {{ explanation.summary.decision_support_notice }}
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
              <td>{{ humanizeToken(item.priority) }}</td>
              <td class="text-break">{{ item.text }}</td>
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
              <td>{{ humanizeToken(item.kind) }}</td>
              <td>{{ humanizeToken(item.priority) }}</td>
              <td class="text-break">{{ formatGapLevelContext(item) }}</td>
              <td class="text-break">{{ item.text }}</td>
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
              <td>{{ humanizeToken(item.priority) }}</td>
              <td>{{ humanizeToken(item.target_level) }}</td>
              <td>{{ formatPointGain(item.estimated_point_gain) }}</td>
              <td class="text-break">{{ item.text }}</td>
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
        <li v-for="(note, index) in explanation.transparency_notes" :key="`transparency-note-${index}`">
          {{ note }}
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { ExplanationGapItem, MatchingExplanation } from "../types/domain";

interface Props {
  explanation: MatchingExplanation;
  competencyLabel: (competencyKey: string) => string;
  showRoadmap?: boolean;
  summaryTitle?: string;
}

withDefaults(defineProps<Props>(), {
  showRoadmap: true,
  summaryTitle: "Analüüsi kokkuvõte",
});

function humanizeToken(value: string): string {
  const normalized = value.replace(/_/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatGapLevelContext(item: ExplanationGapItem): string {
  if (item.kind === "missing") {
    return "Kompetents puudub profiilis.";
  }

  const currentLevel = item.current_level ? humanizeToken(item.current_level) : "Tundmatu praegune tase";
  const expectedLevel = item.expected_level ? humanizeToken(item.expected_level) : "Tundmatu oodatud tase";
  return `${currentLevel} vs oodatud ${expectedLevel}.`;
}

function formatPointGain(value: number): string {
  return `+${value.toFixed(1)} punkti`;
}
</script>
