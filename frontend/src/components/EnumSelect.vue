<template>
  <label class="d-grid gap-1">
    <span v-if="label" class="form-label mb-0">{{ label }}</span>
    <select
      class="form-select"
      :value="modelValue"
      :disabled="disabled"
      @change="onChange"
    >
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
      >
        {{ option.label }}
      </option>
    </select>
  </label>
</template>

<script setup lang="ts">
interface EnumOption {
  value: string;
  label: string;
}

interface Props {
  modelValue: string;
  label?: string;
  options: EnumOption[];
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  disabled: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

function onChange(event: Event): void {
  const target = event.target as HTMLSelectElement;
  emit("update:modelValue", target.value);
}
</script>
