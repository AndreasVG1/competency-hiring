<template>
  <form class="row g-3 align-items-end" @submit.prevent="emitApply">
    <label class="col-12 col-lg-5">
      <span class="form-label mb-0">Otsi</span>
      <input
        :value="query"
        type="search"
        class="form-control"
        placeholder="Otsi pealkirja või kirjelduse järgi"
        :disabled="disabled"
        @input="onQueryInput"
      />
    </label>

    <EnumSelect
      class="col-12 col-lg-3"
      label="Ametikoht"
      :model-value="occupationKey"
      :options="occupationOptionsWithDefault"
      :disabled="disabled"
      @update:model-value="onOccupationChange"
    />

    <EnumSelect
      class="col-12 col-lg-2"
      label="Kandideerimise staatus"
      :model-value="appliedState"
      :options="appliedOptions"
      :disabled="disabled"
      @update:model-value="onAppliedStateChange"
    />

    <div class="col-12 col-lg-3 d-flex gap-2 flex-wrap">
      <button class="btn btn-primary" type="submit" :disabled="disabled">Rakenda</button>
      <button class="btn btn-outline-secondary" type="button" :disabled="disabled" @click="emitClear">
        Tühjenda
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
    { value: "", label: "Kõik ametikohad" },
    ...props.occupationOptions.map((item) => ({
      value: item.key,
      label: item.label,
    })),
  ];
});

const appliedOptions = [
  { value: "", label: "Kõik pakkumised" },
  { value: "applied", label: "Kandideeritud" },
  { value: "not_applied", label: "Kandideerimata" },
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
