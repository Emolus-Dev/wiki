<template>
	<!-- The files this page links to, as the reader will list them. Read from
	     the document itself, so it can never disagree with the content. -->
	<section
		v-if="files.length || !readonly"
		class="mt-10 border-t border-outline-gray-2 pt-6"
		data-testid="editor-attachments"
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
			<li v-for="file in files" :key="file.url">
				<a
					:href="file.url"
					download
					class="group flex items-center gap-3 rounded-6 border border-outline-gray-2 bg-surface-base p-3 hover:bg-surface-gray-1"
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
						class="lucide-download size-4 shrink-0 text-ink-gray-5 group-hover:text-ink-gray-8"
						aria-hidden="true"
					/>
				</a>
			</li>
		</ul>
	</section>
</template>

<script setup>
import { collectAttachments } from '@/lib/attachments';
import { watchDebounced } from '@vueuse/core';
import { Button, createResource } from 'frappe-ui';
import { computed, onBeforeUnmount, ref, watch } from 'vue';

const props = defineProps({
	editor: { type: Object, default: null },
	readonly: { type: Boolean, default: false },
});
const emit = defineEmits(['attach']);

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
