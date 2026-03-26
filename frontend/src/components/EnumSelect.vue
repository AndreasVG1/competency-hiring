<template>
  <label class="form-field">
    <span v-if="label">{{ label }}</span>
    <select
      class="enum-select"
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
