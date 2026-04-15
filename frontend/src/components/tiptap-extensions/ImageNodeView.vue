<template>
  <NodeViewWrapper
    class="wiki-image-wrapper"
    :class="{ 'is-selected': selected }"
  >
    <div class="wiki-image-container" :style="containerStyle">
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
      <button
        v-if="editor.isEditable && selected"
        type="button"
        class="wiki-image-resize-handle"
        title="Resize image"
        @mousedown.prevent="startResize"
      />
      <input
        v-if="editor.isEditable || node.attrs.caption"
        ref="captionInput"
        v-model="caption"
        type="text"
        class="wiki-image-caption-input"
        :class="{ 'has-caption': !!caption }"
        placeholder="Add caption..."
        :disabled="!editor.isEditable"
        @input="updateCaption"
        @keydown="handleKeydown"
      />
    </div>
  </NodeViewWrapper>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { NodeViewWrapper } from "@tiptap/vue-3";

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
const caption = ref(props.node.attrs.caption || "");
const imageElement = ref(null);
const naturalWidth = ref(null);
const liveWidth = ref(props.node.attrs.width || null);
let resizeState = null;

const minWidth = 180;

const displayWidth = computed(
  () => liveWidth.value || props.node.attrs.width || null,
);

const containerStyle = computed(() => ({
  width: displayWidth.value ? `${displayWidth.value}px` : "fit-content",
  maxWidth: "100%",
}));

const imageStyle = computed(() => ({
  width: displayWidth.value ? `${displayWidth.value}px` : "auto",
  maxWidth: "100%",
}));

// Watch for external changes to caption attribute
watch(
  () => props.node.attrs.caption,
  (newCaption) => {
    if (newCaption !== caption.value) {
      caption.value = newCaption || "";
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

function clampWidth(nextWidth) {
  const imageWidth =
    naturalWidth.value || imageElement.value?.naturalWidth || null;
  const maxWidth = imageWidth ? Math.max(minWidth, imageWidth) : Infinity;
  return Math.max(minWidth, Math.min(Math.round(nextWidth), maxWidth));
}

function handleImageLoad(event) {
  const target = event.target;
  naturalWidth.value = target.naturalWidth || null;
  if (!props.node.attrs.width && target.clientWidth) {
    liveWidth.value = Math.round(target.clientWidth);
  }
}

function startResize(event) {
  if (!props.editor.isEditable) return;

  const currentWidth =
    imageElement.value?.getBoundingClientRect().width ||
    displayWidth.value ||
    props.node.attrs.width ||
    imageElement.value?.naturalWidth ||
    minWidth;

  resizeState = {
    startX: event.clientX,
    startWidth: currentWidth,
  };

  window.addEventListener("mousemove", onResizeMove);
  window.addEventListener("mouseup", stopResize);
}

function onResizeMove(event) {
  if (!resizeState) return;
  const delta = event.clientX - resizeState.startX;
  liveWidth.value = clampWidth(resizeState.startWidth + delta);
}

function stopResize() {
  if (!resizeState) return;
  const width = clampWidth(liveWidth.value || resizeState.startWidth);
  liveWidth.value = width;
  props.updateAttributes({ width });
  resizeState = null;
  window.removeEventListener("mousemove", onResizeMove);
  window.removeEventListener("mouseup", stopResize);
}

function selectNode() {
  const pos = props.getPos();
  if (typeof pos === "number") {
    props.editor.commands.setNodeSelection(pos);
  }
}

function handleKeydown(event) {
  const pos = props.getPos();
  if (typeof pos !== "number") return;

  if (event.key === "Enter") {
    event.preventDefault();
    // Insert paragraph after image and move cursor there
    const endPos = pos + props.node.nodeSize;
    props.editor
      .chain()
      .focus()
      .insertContentAt(endPos, { type: "paragraph" })
      .setTextSelection(endPos + 1)
      .run();
  } else if (event.key === "Escape" || event.key === "ArrowDown") {
    event.preventDefault();
    // Move cursor after the image
    const endPos = pos + props.node.nodeSize;
    props.editor.chain().focus().setTextSelection(endPos).run();
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    // Move cursor before the image
    props.editor.chain().focus().setTextSelection(pos).run();
  }
}

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onResizeMove);
  window.removeEventListener("mouseup", stopResize);
});
</script>

<style scoped>
.wiki-image-wrapper {
  display: block;
  margin: 1rem 0;
}

.wiki-image-wrapper.is-selected .wiki-image {
  outline: 2px solid var(--primary, #171717);
  outline-offset: 2px;
}

.wiki-image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0;
  position: relative;
}

.wiki-image {
  max-width: 100%;
  height: auto;
  border-radius: 0.375rem;
  cursor: pointer;
  margin: 0;
}

.wiki-image-resize-handle {
  position: absolute;
  right: -8px;
  top: calc(50% - 16px);
  width: 16px;
  height: 32px;
  border: 1px solid var(--outline-gray-3, #d1d5db);
  border-radius: 999px;
  background: var(--surface-white, #ffffff);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  cursor: ew-resize;
  z-index: 2;
}

.wiki-image-resize-handle::before {
  content: "";
  display: block;
  width: 2px;
  height: 14px;
  margin: 8px auto;
  border-radius: 999px;
  background: var(--outline-gray-3, #d1d5db);
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
  margin-top: 0.25rem;
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
