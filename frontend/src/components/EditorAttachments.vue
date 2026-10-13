<template>
	<!-- The files this page links to, as the reader will list them. Read from
	     the document itself, so it can never disagree with the content. -->
	<section
		v-if="files.length || !readonly"
		class="mt-10 rounded-6 border-t border-outline-gray-2 pt-6 transition-colors"
		:class="dragging ? 'bg-surface-gray-1 ring-2 ring-outline-gray-3' : ''"
		data-testid="editor-attachments"
		@dragover="onDragOver"
		@dragleave="dragging = false"
		@drop="onDrop"
	>
		<div class="flex items-center justify-between gap-3">
			<h2 class="flex items-center gap-2 text-lg-semibold text-ink-gray-9">
				<span class="lucide-paperclip size-4 text-ink-gray-5" aria-hidden="true" />
				{{ __('Attachments') }}
				<span
					v-if="files.length"
					class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6"
				>
					{{ files.length }}
				</span>
			</h2>
			<Button
				v-if="!readonly"
				variant="ghost"
				size="sm"
				:label="__('Attach file')"
				data-testid="editor-attach-file"
				@click="emit('attach')"
			>
				<template #prefix>
					<span class="lucide-plus size-4" aria-hidden="true" />
				</template>
			</Button>
		</div>

		<p v-if="!files.length" class="mt-3 text-sm text-ink-gray-5">
			{{ __('Files you attach appear here and on the published page.') }}
		</p>
		<ul v-else class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
			<li v-for="file in files" :key="file.url" class="relative">
				<a
					:href="file.url"
					download
					class="group flex items-center gap-3 rounded-6 border border-outline-gray-2 bg-surface-base p-3 hover:bg-surface-gray-1"
					:class="actionCount(file) ? (actionCount(file) > 1 ? 'pr-[4.75rem]' : 'pr-11') : ''"
					data-testid="editor-attachment"
				>
					<span class="attachment-chip" :data-kind="file.kind">
						{{ (file.extension || 'file').slice(0, 4).toUpperCase() }}
					</span>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm-medium text-ink-gray-8">
							{{ file.name }}
						</span>
						<span v-if="sizes[file.url]" class="block text-xs text-ink-gray-5">
							{{ sizes[file.url] }}
						</span>
					</span>
					<span
						v-if="!actionCount(file)"
						class="lucide-download size-4 shrink-0 text-ink-gray-5 group-hover:text-ink-gray-8"
						aria-hidden="true"
					/>
				</a>
				<div class="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
					<button
						v-if="file.extension === 'pdf'"
						type="button"
						class="attachment-action"
						:title="__('Preview')"
						:aria-label="__('Preview')"
						data-testid="editor-attachment-preview"
						@click="preview = file"
					>
						<span class="lucide-eye size-4" aria-hidden="true" />
					</button>
					<button
						v-if="!readonly"
						type="button"
						class="attachment-action"
						:title="__('Remove attachment')"
						:aria-label="__('Remove attachment')"
						data-testid="editor-attachment-remove"
						@click="remove(file)"
					>
						<span class="lucide-trash-2 size-4" aria-hidden="true" />
					</button>
				</div>
			</li>
		</ul>
		<PdfViewerModal
			v-if="preview"
			:src="preview.url"
			:filename="preview.name"
			@close="preview = null"
		/>
	</section>
</template>

<script setup>
import { collectAttachments } from '@/lib/attachments';
import { removeAttachment } from '@/lib/attachmentRemoval';
import { watchDebounced } from '@vueuse/core';
import { Button, createResource } from 'frappe-ui';
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue';

// PDF.js is heavy; load it only when someone previews a file.
const PdfViewerModal = defineAsyncComponent(
	() => import('./tiptap-extensions/PdfViewerModal.vue'),
);

const props = defineProps({
	editor: { type: Object, default: null },
	readonly: { type: Boolean, default: false },
});
const emit = defineEmits(['attach', 'attach-files']);

const preview = ref(null);
const dragging = ref(false);

function actionCount(file) {
	return (file.extension === 'pdf' ? 1 : 0) + (props.readonly ? 0 : 1);
}

function remove(file) {
	const { editor } = props;
	if (!editor) return;
	const tr = editor.state.tr;
	if (removeAttachment(tr, file.url)) editor.view.dispatch(tr);
}

function hasFiles(event) {
	return [...(event.dataTransfer?.types || [])].includes('Files');
}

function onDragOver(event) {
	if (props.readonly || !hasFiles(event)) return;
	event.preventDefault();
	dragging.value = true;
}

function onDrop(event) {
	dragging.value = false;
	if (props.readonly || !hasFiles(event)) return;
	event.preventDefault();
	event.stopPropagation();
	emit('attach-files', [...event.dataTransfer.files]);
}

// Bumped on every document change; the list is recomputed from the doc.
const version = ref(0);
let boundEditor = null;
const bump = () => {
	version.value += 1;
};

watch(
	() => props.editor,
	(editor) => {
		boundEditor?.off('update', bump);
		boundEditor = editor || null;
		boundEditor?.on('update', bump);
		bump();
	},
	{ immediate: true },
);
onBeforeUnmount(() => boundEditor?.off('update', bump));

const files = computed(() => {
	version.value;
	return props.editor ? collectAttachments(props.editor.getJSON()) : [];
});

// Sizes live on the File record; they land a beat after the cards do.
const sizes = ref({});
const sizeLookup = createResource({
	url: 'wiki.api.get_file_sizes',
	onSuccess(data) {
		sizes.value = { ...sizes.value, ...data };
	},
});
watchDebounced(
	() => files.value.map((file) => file.url).join('\n'),
	(joined) => {
		const missing = joined
			.split('\n')
			.filter((url) => url && !(url in sizes.value));
		if (missing.length) sizeLookup.submit({ urls: missing });
	},
	{ debounce: 400, immediate: true },
);
</script>

<style scoped>
.attachment-action {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 1.75rem;
	height: 1.75rem;
	border-radius: 0.5rem;
	color: var(--ink-gray-5);
}
.attachment-action:hover {
	background: var(--surface-gray-3);
	color: var(--ink-gray-8);
}
.attachment-chip {
	display: inline-flex;
	flex: none;
	align-items: center;
	justify-content: center;
	min-width: 2.5rem;
	height: 2.25rem;
	padding: 0 0.375rem;
	border-radius: 0.5rem;
	font-size: 0.6875rem;
	font-weight: 600;
	letter-spacing: 0.02em;
	background: var(--surface-gray-2);
	color: var(--ink-gray-7);
}
.attachment-chip[data-kind='red'] {
	background: var(--surface-red-2);
	color: var(--ink-red-7);
}
.attachment-chip[data-kind='blue'] {
	background: var(--surface-blue-2);
	color: var(--ink-blue-7);
}
.attachment-chip[data-kind='green'] {
	background: var(--surface-green-2);
	color: var(--ink-green-7);
}
.attachment-chip[data-kind='amber'] {
	background: var(--surface-amber-2);
	color: var(--ink-amber-7);
}
</style>
