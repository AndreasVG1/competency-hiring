<template>
  <p v-if="requirements.length === 0" class="table-note">{{ emptyText }}</p>

  <table v-else class="competency-table">
    <thead>
      <tr>
        <th>Competency</th>
        <th>Key</th>
        <th>Priority</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="item in requirements" :key="item.competency_key">
        <td>{{ resolveLabel(item.competency_key) }}</td>
        <td><code>{{ item.competency_key }}</code></td>
        <td>{{ formatPriority(item.priority) }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import type { PublicJobOfferRequirementItem, RequirementPriority } from "../types/domain";

interface Props {
  requirements: PublicJobOfferRequirementItem[];
  emptyText?: string;
  labelResolver?: (competencyKey: string) => string;
}

const props = withDefaults(defineProps<Props>(), {
  emptyText: "No requirements listed for this offer.",
  labelResolver: undefined,
});

function formatPriority(priority: RequirementPriority): string {
  if (priority === "must_have") {
    return "Must have";
  }
  if (priority === "important") {
    return "Important";
  }
  return "Nice to have";
}

function resolveLabel(competencyKey: string): string {
  if (props.labelResolver) {
    return props.labelResolver(competencyKey);
  }
  return competencyKey;
}
</script>
