<template>
  <div
    class="attachment-privacy-selector"
    role="group"
    :aria-label="__('Attachment visibility')"
  >
    <button
      type="button"
      class="attachment-privacy-option"
      :class="{ active: modelValue }"
      :title="__('Files will be uploaded as private')"
      @click="emit('update:modelValue', true)"
    >
      <LucideLock class="size-4" />
      <span class="attachment-privacy-label">{{ __("Private") }}</span>
    </button>
    <button
      type="button"
      class="attachment-privacy-option"
      :class="{ active: !modelValue }"
      :title="__('Files will be uploaded as public')"
      @click="emit('update:modelValue', false)"
    >
      <LucideGlobe class="size-4" />
      <span class="attachment-privacy-label">{{ __("Public") }}</span>
    </button>
  </div>
</template>

<script setup>
import LucideGlobe from "~icons/lucide/globe";
import LucideLock from "~icons/lucide/lock";

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["update:modelValue"]);
</script>

<style scoped>
.attachment-privacy-selector {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem;
  border: 1px solid var(--outline-gray-2, #e5e7eb);
  border-radius: 0.5rem;
  background: var(--surface-gray-1, #f9fafb);
  gap: 0.125rem;
}

.attachment-privacy-option {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  height: 1.9rem;
  padding: 0 0.625rem;
  border: none;
  border-radius: 0.4rem;
  background: transparent;
  color: var(--ink-gray-6, #4b5563);
  cursor: pointer;
  transition: all 0.15s ease;
}

.attachment-privacy-option:hover {
  background: var(--surface-gray-2, #f3f4f6);
  color: var(--ink-gray-8, #1f2937);
}

.attachment-privacy-option.active {
  background: var(--surface-white, #ffffff);
  color: var(--ink-gray-9, #111827);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.attachment-privacy-label {
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
}
</style>
