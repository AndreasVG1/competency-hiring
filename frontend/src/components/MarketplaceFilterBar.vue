<template>
  <form class="marketplace-filter-bar" @submit.prevent="emitApply">
    <label class="form-field">
      <span>Search</span>
      <input
        :value="query"
        type="search"
        placeholder="Search title or description"
        :disabled="disabled"
        @input="onQueryInput"
      />
    </label>

    <EnumSelect
      label="Occupation"
      :model-value="occupationKey"
      :options="occupationOptionsWithDefault"
      :disabled="disabled"
      @update:model-value="onOccupationChange"
    />

    <EnumSelect
      label="Application status"
      :model-value="appliedState"
      :options="appliedOptions"
      :disabled="disabled"
      @update:model-value="onAppliedStateChange"
    />

    <div class="table-actions">
      <button class="button-primary" type="submit" :disabled="disabled">Apply filters</button>
      <button class="button-secondary" type="button" :disabled="disabled" @click="emitClear">
        Clear
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { CatalogItem } from "../types/domain";
import EnumSelect from "./EnumSelect.vue";

interface Props {
  query: string;
  occupationKey: string;
  appliedState: string;
  occupationOptions: CatalogItem[];
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});

const emit = defineEmits<{
  "update:query": [value: string];
  "update:occupationKey": [value: string];
  "update:appliedState": [value: string];
  apply: [];
  clear: [];
}>();

const occupationOptionsWithDefault = computed(() => {
  return [
    { value: "", label: "All occupations" },
    ...props.occupationOptions.map((item) => ({
      value: item.key,
      label: item.label,
    })),
  ];
});

const appliedOptions = [
  { value: "", label: "All offers" },
  { value: "applied", label: "Applied" },
  { value: "not_applied", label: "Not applied" },
];

function onQueryInput(event: Event): void {
  const target = event.target as HTMLInputElement;
  emit("update:query", target.value);
}

function onOccupationChange(value: string): void {
  emit("update:occupationKey", value);
}

function onAppliedStateChange(value: string): void {
  emit("update:appliedState", value);
}

function emitApply(): void {
  emit("apply");
}

function emitClear(): void {
  emit("clear");
}
</script>
