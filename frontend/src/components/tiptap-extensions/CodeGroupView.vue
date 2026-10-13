<template>
	<node-view-wrapper class="wiki-code-group" :data-active="active">
		<div class="wiki-code-group__tabs" contenteditable="false" role="tablist">
			<div
				v-for="tab in tabs"
				:key="tab.pos"
				class="wiki-code-group__tab"
				:class="{ 'is-active': tab.index === active }"
			>
				<input
					v-if="renaming === tab.index"
					ref="renameInput"
					v-model="draft"
					class="wiki-code-group__rename"
					:placeholder="tab.language"
					@keydown.enter.prevent="commitRename(tab)"
					@keydown.escape.prevent="renaming = null"
					@blur="commitRename(tab)"
				/>
				<button
					v-else
					type="button"
					role="tab"
					:aria-selected="tab.index === active"
					:title="isEditable ? __('Double-click to rename') : undefined"
					@mousedown.prevent
					@click="active = tab.index"
					@dblclick="startRename(tab)"
				>
					{{ tab.title }}
				</button>
				<template v-if="isEditable && tabs.length > 1 && tab.index === active">
					<button
						v-if="tab.index > 0"
						type="button"
						class="wiki-code-group__icon"
						:aria-label="__('Move tab left')"
						@mousedown.prevent
						@click="moveTab(tab, -1)"
					>
						<span class="lucide-chevron-left size-3" aria-hidden="true" />
					</button>
					<button
						v-if="tab.index < tabs.length - 1"
						type="button"
						class="wiki-code-group__icon"
						:aria-label="__('Move tab right')"
						@mousedown.prevent
						@click="moveTab(tab, 1)"
					>
						<span class="lucide-chevron-right size-3" aria-hidden="true" />
					</button>
				</template>
				<button
					v-if="isEditable && tabs.length > 1 && tab.index === active"
					type="button"
					class="wiki-code-group__icon"
					:aria-label="__('Remove tab')"
					@mousedown.prevent
					@click="removeTab(tab)"
				>
					<span class="lucide-x size-3" aria-hidden="true" />
				</button>
			</div>
			<button
				v-if="isEditable"
				type="button"
				class="wiki-code-group__icon"
				:aria-label="__('Add tab')"
				@mousedown.prevent
				@click="addTab"
			>
				<span class="lucide-plus size-3.5" aria-hidden="true" />
			</button>
		</div>
		<node-view-content class="wiki-code-group__body" />
	</node-view-wrapper>
</template>

<script setup>
import { NodeViewContent, NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3';
import { computed, nextTick, ref, toRaw, watch } from 'vue';
import { useNodeViewEditable } from '../../composables/useNodeViewEditable';
import { moveGroupTab } from '../../lib/codeGroupOps';

const props = defineProps(nodeViewProps);
const editor = toRaw(props.editor);
const isEditable = useNodeViewEditable(editor);

const active = ref(0);
const renaming = ref(null);
const draft = ref('');
const renameInput = ref(null);

const tabs = computed(() => {
	const list = [];
	let pos = props.getPos() + 1;
	props.node.forEach((child, _offset, index) => {
		const language = child.attrs.language || 'auto';
		list.push({
			index,
			pos,
			language,
			label: child.attrs.label || '',
			title: child.attrs.label || language,
		});
		pos += child.nodeSize;
	});
	return list;
});

// Removing the last tab, or loading a shorter group, must not leave a tab that
// does not exist selected.
watch(
	() => props.node.childCount,
	(count) => {
		if (active.value >= count) active.value = Math.max(count - 1, 0);
	},
);

function addTab() {
	const end = props.getPos() + props.node.nodeSize - 1;
	editor
		.chain()
		.insertContentAt(end, { type: 'codeBlock', attrs: { language: null } })
		.run();
	active.value = props.node.childCount;
}

function moveTab(tab, step) {
	const { state, view } = editor;
	const tr = state.tr;
	if (!moveGroupTab(tr, props.getPos(), tab.index, tab.index + step)) return;
	view.dispatch(tr);
	active.value = tab.index + step;
}

function removeTab(tab) {
	const child = props.node.child(tab.index);
	editor
		.chain()
		.deleteRange({ from: tab.pos, to: tab.pos + child.nodeSize })
		.run();
}

async function startRename(tab) {
	if (!isEditable.value) return;
	renaming.value = tab.index;
	draft.value = tab.label;
	await nextTick();
	renameInput.value?.[0]?.focus();
}

function commitRename(tab) {
	if (renaming.value !== tab.index) return;
	renaming.value = null;
	const label = draft.value.trim();
	if (label === tab.label) return;

	const { state, view } = editor;
	const child = state.doc.nodeAt(tab.pos);
	if (!child) return;
	view.dispatch(state.tr.setNodeMarkup(tab.pos, undefined, { ...child.attrs, label }));
}
</script>
