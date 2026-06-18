<template>
  <NodeViewWrapper
    class="wiki-image-wrapper"
    :class="[`align-${align}`, { 'is-selected': selected }]"
  >
    <div class="wiki-image-container" :style="containerStyle">
      <div
        v-if="editor.isEditable && selected"
        class="wiki-image-toolbar"
        contenteditable="false"
        @mousedown.prevent
        @click.stop
      >
        <div class="wiki-image-toolbar-group">
          <button
            type="button"
            class="wiki-image-tool"
            :class="{ 'is-active': align === 'left' }"
            :title="__('Align left')"
            @click="setAlign('left')"
          >
            <LucideAlignLeft class="size-4" />
          </button>
          <button
            type="button"
            class="wiki-image-tool"
            :class="{ 'is-active': align === 'center' }"
            :title="__('Align center')"
            @click="setAlign('center')"
          >
            <LucideAlignCenter class="size-4" />
          </button>
          <button
            type="button"
            class="wiki-image-tool"
            :class="{ 'is-active': align === 'right' }"
            :title="__('Align right')"
            @click="setAlign('right')"
          >
            <LucideAlignRight class="size-4" />
          </button>
        </div>

        <span class="wiki-image-toolbar-divider" />

        <div class="wiki-image-toolbar-group">
          <button
            v-for="preset in sizePresets"
            :key="preset.value"
            type="button"
            class="wiki-image-tool is-text"
            :class="{ 'is-active': isPresetActive(preset.value) }"
            :title="preset.title"
            @click="applyPreset(preset.value)"
          >
            {{ preset.label }}
          </button>
          <button
            type="button"
            class="wiki-image-tool"
            :class="{ 'is-active': align === 'full' }"
            :title="__('Full width')"
            @click="toggleFullWidth"
          >
            <LucideStretchHorizontal class="size-4" />
          </button>
        </div>
      </div>

      <div class="wiki-image-frame">
        <img
          ref="imageElement"
          :src="node.attrs.src"
          :alt="node.attrs.alt || ''"
          :title="node.attrs.title || ''"
          :width="displayWidth || undefined"
          :height="node.attrs.height || undefined"
          class="wiki-image"
          :style="imageStyle"
          @load="handleImageLoad"
          @click="selectNode"
        />
        <template v-if="editor.isEditable && selected && align !== 'full'">
          <button
            type="button"
            class="wiki-image-resize-handle is-right"
            :title="__('Drag to resize')"
            @mousedown.prevent="startResize($event, 'right')"
          />
          <button
            type="button"
            class="wiki-image-resize-handle is-left"
            :title="__('Drag to resize')"
            @mousedown.prevent="startResize($event, 'left')"
          />
        </template>
        <span v-if="resizeState" class="wiki-image-size-badge">
          {{ displayWidth }}px
        </span>
      </div>

      <input
        v-if="editor.isEditable || node.attrs.caption"
        ref="captionInput"
        v-model="caption"
        type="text"
        class="wiki-image-caption-input"
        :class="{ 'has-caption': !!caption }"
        :placeholder="__('Add caption...')"
        :disabled="!editor.isEditable"
        @input="updateCaption"
        @keydown="handleKeydown"
      />
    </div>
  </NodeViewWrapper>
</template>

<script setup>
import { NodeViewWrapper } from '@tiptap/vue-3';
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import LucideAlignCenter from '~icons/lucide/align-center';
import LucideAlignLeft from '~icons/lucide/align-left';
import LucideAlignRight from '~icons/lucide/align-right';
import LucideStretchHorizontal from '~icons/lucide/stretch-horizontal';

const props = defineProps({
	node: {
		type: Object,
		required: true,
	},
	updateAttributes: {
		type: Function,
		required: true,
	},
	selected: {
		type: Boolean,
		default: false,
	},
	editor: {
		type: Object,
		required: true,
	},
	getPos: {
		type: Function,
		required: true,
	},
});

const captionInput = ref(null);
const caption = ref(props.node.attrs.caption || '');
const imageElement = ref(null);
const naturalWidth = ref(null);
const liveWidth = ref(props.node.attrs.width || null);
const resizeState = ref(null);

const minWidth = 120;

const align = computed(() => props.node.attrs.align || 'left');

const sizePresets = [
	{ value: 0.25, label: 'S', title: __('Small (25%)') },
	{ value: 0.5, label: 'M', title: __('Medium (50%)') },
	{ value: 0.75, label: 'L', title: __('Large (75%)') },
	{ value: 1, label: 'XL', title: __('Original (100%)') },
];

const displayWidth = computed(
	() => liveWidth.value || props.node.attrs.width || null,
);

const containerStyle = computed(() => {
	if (align.value === 'full') {
		return { width: '100%', maxWidth: '100%', margin: '0' };
	}

	const style = {
		width: displayWidth.value ? `${displayWidth.value}px` : 'fit-content',
		maxWidth: '100%',
	};

	if (align.value === 'center') {
		style.marginLeft = 'auto';
		style.marginRight = 'auto';
	} else if (align.value === 'right') {
		style.marginLeft = 'auto';
		style.marginRight = '0';
	} else {
		style.marginLeft = '0';
		style.marginRight = 'auto';
	}

	return style;
});

const imageStyle = computed(() => {
	if (align.value === 'full') {
		return { width: '100%', maxWidth: '100%' };
	}
	return {
		width: displayWidth.value ? `${displayWidth.value}px` : 'auto',
		maxWidth: '100%',
	};
});

watch(
	() => props.node.attrs.caption,
	(newCaption) => {
		if (newCaption !== caption.value) {
			caption.value = newCaption || '';
		}
	},
);

watch(
	() => props.node.attrs.width,
	(newWidth) => {
		liveWidth.value = newWidth || null;
	},
);

function updateCaption() {
	props.updateAttributes({ caption: caption.value });
}

function setAlign(value) {
	// Toggling left (the default) clears the attribute to keep markdown clean.
	const next = value === 'left' ? null : value;
	// Leaving full-width mode restores a sensible explicit width.
	if (props.node.attrs.align === 'full' && value !== 'full') {
		const restored = clampWidth(
			naturalWidth.value || displayWidth.value || minWidth,
		);
		liveWidth.value = restored;
		props.updateAttributes({ align: next, width: restored });
		return;
	}
	props.updateAttributes({ align: next });
}

function toggleFullWidth() {
	if (align.value === 'full') {
		setAlign('center');
	} else {
		props.updateAttributes({ align: 'full' });
	}
}

function applyPreset(fraction) {
	const base = naturalWidth.value || imageElement.value?.naturalWidth;
	if (!base) return;
	const width = clampWidth(Math.round(base * fraction));
	liveWidth.value = width;
	const patch = { width };
	if (props.node.attrs.align === 'full') patch.align = null;
	props.updateAttributes(patch);
}

function isPresetActive(fraction) {
	const base = naturalWidth.value;
	if (!base || align.value === 'full' || !displayWidth.value) return false;
	return Math.abs(displayWidth.value - Math.round(base * fraction)) <= 2;
}

function clampWidth(nextWidth) {
	const imageWidth =
		naturalWidth.value || imageElement.value?.naturalWidth || null;
	const maxWidth = imageWidth
		? Math.max(minWidth, imageWidth)
		: Number.POSITIVE_INFINITY;
	return Math.max(minWidth, Math.min(Math.round(nextWidth), maxWidth));
}

function handleImageLoad(event) {
	const target = event.target;
	naturalWidth.value = target.naturalWidth || null;
	if (!props.node.attrs.width && target.clientWidth) {
		liveWidth.value = Math.round(target.clientWidth);
	}
}

function startResize(event, edge) {
	if (!props.editor.isEditable) return;

	const currentWidth =
		imageElement.value?.getBoundingClientRect().width ||
		displayWidth.value ||
		props.node.attrs.width ||
		imageElement.value?.naturalWidth ||
		minWidth;

	resizeState.value = {
		startX: event.clientX,
		startWidth: currentWidth,
		edge: edge || 'right',
	};

	window.addEventListener('mousemove', onResizeMove);
	window.addEventListener('mouseup', stopResize);
}

function onResizeMove(event) {
	if (!resizeState.value) return;
	const { startX, startWidth, edge } = resizeState.value;
	const delta = event.clientX - startX;
	// Dragging the left handle inward/outward mirrors the delta.
	const signed = edge === 'left' ? -delta : delta;
	liveWidth.value = clampWidth(startWidth + signed);
}

function stopResize() {
	if (!resizeState.value) return;
	const width = clampWidth(liveWidth.value || resizeState.value.startWidth);
	liveWidth.value = width;
	props.updateAttributes({ width });
	resizeState.value = null;
	window.removeEventListener('mousemove', onResizeMove);
	window.removeEventListener('mouseup', stopResize);
}

function selectNode() {
	const pos = props.getPos();
	if (typeof pos === 'number') {
		props.editor.commands.setNodeSelection(pos);
	}
}

function handleKeydown(event) {
	const pos = props.getPos();
	if (typeof pos !== 'number') return;

	if (event.key === 'Enter') {
		event.preventDefault();
		// Insert paragraph after image and move cursor there
		const endPos = pos + props.node.nodeSize;
		props.editor
			.chain()
			.focus()
			.insertContentAt(endPos, { type: 'paragraph' })
			.setTextSelection(endPos + 1)
			.run();
	} else if (event.key === 'Escape' || event.key === 'ArrowDown') {
		event.preventDefault();
		// Move cursor after the image
		const endPos = pos + props.node.nodeSize;
		props.editor.chain().focus().setTextSelection(endPos).run();
	} else if (event.key === 'ArrowUp') {
		event.preventDefault();
		// Move cursor before the image
		props.editor.chain().focus().setTextSelection(pos).run();
	}
}

onBeforeUnmount(() => {
	window.removeEventListener('mousemove', onResizeMove);
	window.removeEventListener('mouseup', stopResize);
});
</script>

<style scoped>
.wiki-image-wrapper {
  display: block;
  margin: 1rem 0;
}

.wiki-image-container {
  display: flex;
  flex-direction: column;
  margin: 0;
  position: relative;
}

.wiki-image-frame {
  position: relative;
  display: inline-flex;
  width: 100%;
}

.wiki-image {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 0.5rem;
  cursor: pointer;
  margin: 0;
  transition: outline-color 0.15s ease;
}

.wiki-image-wrapper.is-selected .wiki-image {
  outline: 2px solid var(--outline-gray-4, #9ca3af);
  outline-offset: 2px;
}

/* Caption alignment follows image alignment */
.wiki-image-wrapper.align-center .wiki-image-caption-input {
  text-align: center;
}
.wiki-image-wrapper.align-right .wiki-image-caption-input {
  text-align: right;
}
.wiki-image-wrapper.align-left .wiki-image-caption-input,
.wiki-image-wrapper.align-full .wiki-image-caption-input {
  text-align: left;
}

/* Floating toolbar */
.wiki-image-toolbar {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem;
  border-radius: 0.625rem;
  background: var(--surface-white, #ffffff);
  border: 1px solid var(--outline-gray-2, #e5e7eb);
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.12),
    0 1px 3px rgba(0, 0, 0, 0.08);
  white-space: nowrap;
}

.wiki-image-toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.125rem;
}

.wiki-image-toolbar-divider {
  width: 1px;
  align-self: stretch;
  margin: 0.125rem 0.125rem;
  background: var(--outline-gray-2, #e5e7eb);
}

.wiki-image-tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  height: 1.75rem;
  padding: 0 0.375rem;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--ink-gray-6, #4b5563);
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition:
    background-color 0.12s ease,
    color 0.12s ease;
}

.wiki-image-tool:hover {
  background: var(--surface-gray-2, #f3f4f6);
  color: var(--ink-gray-8, #1f2937);
}

.wiki-image-tool.is-active {
  background: var(--surface-gray-3, #e5e7eb);
  color: var(--ink-gray-9, #111827);
}

/* Resize handles */
.wiki-image-resize-handle {
  position: absolute;
  top: calc(50% - 18px);
  width: 12px;
  height: 36px;
  border: 1px solid var(--outline-gray-3, #d1d5db);
  border-radius: 999px;
  background: var(--surface-white, #ffffff);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
  cursor: ew-resize;
  z-index: 5;
  padding: 0;
}

.wiki-image-resize-handle.is-right {
  right: -6px;
}

.wiki-image-resize-handle.is-left {
  left: -6px;
}

.wiki-image-resize-handle::before {
  content: "";
  display: block;
  width: 2px;
  height: 16px;
  margin: 9px auto;
  border-radius: 999px;
  background: var(--outline-gray-3, #d1d5db);
}

.wiki-image-size-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 6;
  padding: 0.125rem 0.375rem;
  border-radius: 0.375rem;
  background: rgba(17, 24, 39, 0.78);
  color: #ffffff;
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1.2;
  pointer-events: none;
}

.wiki-image-caption-input {
  width: 100%;
  max-width: 100%;
  text-align: center;
  background: transparent;
  border: none;
  font-style: italic;
  font-size: 0.875rem;
  color: var(--ink-gray-6, #4b5563);
  padding: 0 0.25rem;
  margin-top: 0.5rem;
  outline: none;
  box-shadow: none;
}

.wiki-image-caption-input::placeholder {
  color: var(--ink-gray-4, #9ca3af);
}

.wiki-image-caption-input:focus {
  outline: none;
  box-shadow: none;
  border: none;
}

.wiki-image-caption-input:disabled {
  cursor: default;
}

.wiki-image-caption-input:disabled:not(.has-caption) {
  display: none;
}
</style>
