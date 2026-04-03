<template>
  <section class="explanation-panel">
    <header class="subsection-header">
      <h3>{{ summaryTitle }}</h3>
    </header>

    <section class="explanation-summary-card">
      <p class="explanation-headline">{{ explanation.summary.headline }}</p>
      <p class="explanation-status">{{ explanation.summary.status_label }}</p>
      <p v-if="explanation.summary.must_have_notice" class="explanation-notice explanation-notice-warning">
        {{ explanation.summary.must_have_notice }}
      </p>
      <p v-if="explanation.summary.no_requirements_notice" class="explanation-notice explanation-notice-info">
        {{ explanation.summary.no_requirements_notice }}
      </p>
      <p class="explanation-notice explanation-notice-decision">
        {{ explanation.summary.decision_support_notice }}
      </p>
    </section>

    <section>
      <header class="subsection-header">
        <h3>Strengths</h3>
      </header>
      <p v-if="explanation.highlights.length === 0" class="section-note">
        No strengths are currently highlighted in this analysis.
      </p>
      <table v-else class="explanation-table">
        <thead>
          <tr>
            <th>Competency</th>
            <th>Priority</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, index) in explanation.highlights"
            :key="`highlight-${item.competency_key}-${item.priority}-${index}`"
          >
            <td>
              <span class="competency-cell-main">{{ competencyLabel(item.competency_key) }}</span>
              <span class="competency-cell-key">{{ item.competency_key }}</span>
            </td>
            <td>{{ humanizeToken(item.priority) }}</td>
            <td>{{ item.text }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <header class="subsection-header">
        <h3>Gaps</h3>
      </header>
      <p v-if="explanation.gaps.length === 0" class="section-note">
        No competency gaps are currently identified.
      </p>
      <table v-else class="explanation-table">
        <thead>
          <tr>
            <th>Competency</th>
            <th>Gap Type</th>
            <th>Priority</th>
            <th>Level Context</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, index) in explanation.gaps" :key="`gap-${item.competency_key}-${item.priority}-${index}`">
            <td>
              <span class="competency-cell-main">{{ competencyLabel(item.competency_key) }}</span>
              <span class="competency-cell-key">{{ item.competency_key }}</span>
            </td>
            <td>{{ humanizeToken(item.kind) }}</td>
            <td>{{ humanizeToken(item.priority) }}</td>
            <td>{{ formatGapLevelContext(item) }}</td>
            <td>{{ item.text }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="showRoadmap && explanation.development_roadmap !== null">
      <header class="subsection-header">
        <h3>Development Roadmap</h3>
      </header>
      <p v-if="explanation.development_roadmap.length === 0" class="section-note">
        No immediate roadmap targets are suggested from this analysis.
      </p>
      <table v-else class="explanation-table">
        <thead>
          <tr>
            <th>Competency</th>
            <th>Priority</th>
            <th>Target Level</th>
            <th>Estimated Point Gain</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, index) in explanation.development_roadmap"
            :key="`roadmap-${item.competency_key}-${item.priority}-${index}`"
          >
            <td>
              <span class="competency-cell-main">{{ competencyLabel(item.competency_key) }}</span>
              <span class="competency-cell-key">{{ item.competency_key }}</span>
            </td>
            <td>{{ humanizeToken(item.priority) }}</td>
            <td>{{ humanizeToken(item.target_level) }}</td>
            <td>{{ formatPointGain(item.estimated_point_gain) }}</td>
            <td>{{ item.text }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <header class="subsection-header">
        <h3>Transparency Notes</h3>
      </header>
      <ul class="explanation-list">
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
  summaryTitle: "Explanation Summary",
});

function humanizeToken(value: string): string {
  const normalized = value.replace(/_/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatGapLevelContext(item: ExplanationGapItem): string {
  if (item.kind === "missing") {
    return "Competency is not present in the profile.";
  }

  const currentLevel = item.current_level ? humanizeToken(item.current_level) : "Unknown current level";
  const expectedLevel = item.expected_level ? humanizeToken(item.expected_level) : "Unknown expected level";
  return `${currentLevel} vs expected ${expectedLevel}.`;
}

function formatPointGain(value: number): string {
  return `+${value.toFixed(1)} points`;
}
</script>
