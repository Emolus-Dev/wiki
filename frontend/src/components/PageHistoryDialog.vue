<template>
	<Dialog v-model:open="open" size="4xl" :title="__('Page history')">
		<template #default>
			<div class="flex min-h-[24rem] gap-4" data-testid="page-history">
				<!-- Versions: the merges that changed this page -->
				<div class="w-60 shrink-0 overflow-y-auto border-r border-outline-gray-2 pr-3">
					<p v-if="history.loading" class="text-sm text-ink-gray-5">{{ __('Loading…') }}</p>
					<p v-else-if="!versions.length" class="text-sm text-ink-gray-5">
						{{ __('No earlier versions yet. A page gets one each time a change request that touches it is merged.') }}
					</p>
					<button
						v-for="version in versions"
						:key="version.revision"
						type="button"
						class="mb-1 flex w-full flex-col rounded-5 px-2.5 py-2 text-left hover:bg-surface-gray-2"
						:class="selected?.revision === version.revision ? 'bg-surface-gray-2' : ''"
						data-testid="page-history-version"
						@click="select(version)"
					>
						<span class="text-sm-medium text-ink-gray-8">{{ dayjsLocal(version.created_at).format('D MMM YYYY, HH:mm') }}</span>
						<span class="truncate text-xs text-ink-gray-5">{{ version.full_name }}</span>
					</button>
				</div>

				<!-- What changed between that version and the page as it is now -->
				<div class="min-w-0 flex-1">
					<p v-if="!selected" class="text-sm text-ink-gray-5">{{ __('Pick a version to compare it with the page as it is now.') }}</p>
					<template v-else>
						<div class="mb-3 flex items-center justify-between gap-3">
							<p class="text-sm text-ink-gray-6">
								<span class="text-ink-green-7">+{{ stats.added }}</span>
								<span class="mx-1.5 text-ink-red-7">-{{ stats.removed }}</span>
								{{ __('compared with now') }}
							</p>
							<Button
								v-if="canRestore"
								variant="solid"
								size="sm"
								:loading="detail.loading"
								data-testid="page-history-restore"
								@click="restore"
							>
								{{ __('Restore this version') }}
							</Button>
						</div>
						<p v-if="detail.loading" class="text-sm text-ink-gray-5">{{ __('Loading…') }}</p>
						<p v-else-if="rows === null" class="text-sm text-ink-gray-5">
							{{ __('The two versions differ too much to compare line by line.') }}
						</p>
						<p v-else-if="!rows.length" class="text-sm text-ink-gray-5">
							{{ __('This version is the same as the page now.') }}
						</p>
						<div v-else class="max-h-[26rem] overflow-auto rounded-5 border border-outline-gray-2 font-mono text-xs leading-5">
							<template v-for="(row, index) in rows" :key="index">
								<div v-if="row.type === 'gap'" class="bg-surface-gray-1 px-3 py-0.5 text-ink-gray-4">
									… {{ __('{0} unchanged lines', [row.count]) }}
								</div>
								<div
									v-else
									class="whitespace-pre-wrap break-words px-3"
									:class="{
										'bg-surface-green-1 text-ink-green-8': row.type === 'add',
										'bg-surface-red-1 text-ink-red-8': row.type === 'del',
									}"
								>
									<span class="mr-2 select-none opacity-60">{{ row.type === 'add' ? '+' : row.type === 'del' ? '-' : ' ' }}</span>{{ row.text }}
								</div>
							</template>
						</div>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
// A "-" line is in the old version and not on the page now; a "+" line is on the
// page now and not in the old version. Restoring puts the old text in the editor
// as an ordinary edit, so it can be undone and still goes through review.
import { diffLines, diffStats, withContext } from '@/lib/lineDiff';
import { Button, Dialog, createResource, dayjsLocal } from 'frappe-ui';
import { computed, ref, watch } from 'vue';

const props = defineProps({
	space: { type: String, required: true },
	docKey: { type: String, default: null },
	currentContent: { type: String, default: '' },
	canRestore: { type: Boolean, default: false },
});
const emit = defineEmits(['restore']);

const open = defineModel('open', { type: Boolean, default: false });
const versions = ref([]);
const selected = ref(null);
const versionText = ref('');

const history = createResource({
	url: 'wiki.api.page_history.get_page_history',
	onSuccess(data) {
		versions.value = data || [];
	},
});
const detail = createResource({
	url: 'wiki.api.page_history.get_page_version',
	onSuccess(data) {
		versionText.value = data?.content || '';
	},
});

watch(open, (isOpen) => {
	if (!isOpen) return;
	versions.value = [];
	selected.value = null;
	versionText.value = '';
	if (props.space && props.docKey) {
		history.submit({ space: props.space, doc_key: props.docKey });
	}
});

function select(version) {
	selected.value = version;
	versionText.value = '';
	detail.submit({
		space: props.space,
		doc_key: props.docKey,
		revision: version.revision,
	});
}

const ops = computed(() =>
	selected.value && !detail.loading
		? diffLines(versionText.value, props.currentContent)
		: [],
);
const rows = computed(() => (ops.value === null ? null : withContext(ops.value)));
const stats = computed(() => diffStats(ops.value || []));

function restore() {
	emit('restore', versionText.value);
	open.value = false;
}
</script>
