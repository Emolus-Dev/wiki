<template>
	<!-- Same structure and classes as frappe-ui's code block, so the styles in
	     wiki-editor-content.css apply unchanged. What differs is the cost: a long
	     page can hold hundreds of these, and frappe-ui's view mounts a Combobox,
	     a tooltip and a button per block and listens to every transaction. Here
	     the toolbar is two plain buttons, the language list exists only while it
	     is open, and nothing listens to the editor. -->
	<node-view-wrapper>
		<div class="code-block-container group relative">
			<pre
				class="flex items-start gap-5 !pl-3"
			><span class="flex flex-none select-none flex-col items-end border-outline-gray-2 text-ink-gray-4" aria-hidden="true" contenteditable="false"><span v-for="n in lineCount" :key="n" class="block">{{ n }}</span></span><code class="min-w-0 flex-1 overflow-x-auto"><node-view-content /></code></pre>
			<div
				class="absolute right-0 top-0 pr-2 pt-1.5 flex items-center gap-0.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
				:class="{ 'opacity-100': picking || props.selected }"
				contenteditable="false"
			>
				<select
					v-if="picking"
					ref="selectRef"
					class="h-6 rounded-4 border-0 bg-transparent py-0 pl-1 pr-6 text-xs text-ink-gray-8"
					:value="language"
					@change="choose($event.target.value)"
					@blur="picking = false"
					@keydown.escape.prevent="picking = false"
				>
					<option
						v-for="option in languageOptions()"
						:key="option.value"
						:value="option.value"
					>
						{{ option.label }}
					</option>
				</select>
				<button
					v-else-if="editable"
					type="button"
					class="inline-flex h-6 items-center gap-1 rounded-4 px-1.5 text-xs text-ink-gray-5 hover:bg-surface-gray-3"
					:aria-label="__('Language')"
					@mousedown.prevent
					@click.stop="startPicking"
				>
					{{ language || 'auto' }}
					<span class="lucide-chevron-down size-3" aria-hidden="true" />
				</button>
				<span v-else class="select-none px-1 text-xs text-ink-gray-4">
					{{ language || 'auto' }}
				</span>
				<button
					type="button"
					class="inline-flex size-6 items-center justify-center rounded-4 text-ink-gray-5 hover:bg-surface-gray-3"
					:aria-label="__('Copy code')"
					:title="copied ? __('Copied!') : __('Copy code')"
					@mousedown.prevent
					@click.stop="copyCode"
				>
					<span
						:class="[copied ? 'lucide-check' : 'lucide-copy', 'size-3.5']"
						aria-hidden="true"
					/>
				</button>
			</div>
		</div>
	</node-view-wrapper>
</template>

<script setup>
import { NodeViewContent, NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3';
import { computed, nextTick, onBeforeUnmount, ref, toRaw } from 'vue';

const props = defineProps(nodeViewProps);
const editor = toRaw(props.editor);

// An editor's editability is fixed for its lifetime (a read-only page mounts a
// read-only editor), so it is read once rather than followed. The option, not
// `editor.isEditable`: that reaches through `editor.view`, which does not exist
// yet while the editor is still creating its first node views.
const editable = editor.options.editable !== false;

const language = computed(() => props.node.attrs.language || '');
const lineCount = computed(() => props.node.textContent.split('\n').length);

const picking = ref(false);
const selectRef = ref(null);

// Built on demand: only the block being edited ever needs the list.
function languageOptions() {
	const names = props.extension.options.lowlight.listLanguages();
	const options = [...new Set(names)].map((name) => ({ label: name, value: name }));
	if (!options.some((option) => option.label === 'html')) {
		options.push({ label: 'html', value: 'xml' });
	}
	options.sort((a, b) => a.label.localeCompare(b.label));
	return [{ label: 'auto', value: '' }, ...options];
}

async function startPicking() {
	picking.value = true;
	await nextTick();
	selectRef.value?.focus();
}

function choose(value) {
	props.updateAttributes({ language: value || null });
	picking.value = false;
}

const copied = ref(false);
let resetTimer;

async function copyCode() {
	const text = props.node.textContent;
	try {
		await navigator.clipboard.writeText(text);
	} catch {
		const area = document.createElement('textarea');
		area.value = text;
		area.style.position = 'fixed';
		area.style.opacity = '0';
		document.body.appendChild(area);
		area.select();
		document.execCommand('copy');
		document.body.removeChild(area);
	}
	copied.value = true;
	clearTimeout(resetTimer);
	resetTimer = setTimeout(() => {
		copied.value = false;
	}, 2000);
}

onBeforeUnmount(() => clearTimeout(resetTimer));
</script>
