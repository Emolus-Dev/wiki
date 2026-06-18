<template>
  <draggable
    class="nested-draggable-area space-y-0.5"
    :class="{ 'min-h-[28px]': level > 0 }"
    tag="div"
    :list="localItems"
    :group="{ name: 'wiki-tree' }"
    item-key="doc_key"
    ghost-class="dragging-ghost"
    drag-class="dragging-item"
    handle=".drag-handle"
    :animation="150"
    @start="onDragStart"
    @end="onDragEnd"
    @change="handleChange"
  >
    <template #item="{ element }">
      <div class="draggable-item">
        <div
          class="group relative flex items-center gap-1 pl-1 pr-1.5 py-1 min-h-[32px] rounded-md transition-colors duration-150"
          :class="getRowClasses(element)"
          @click="handleRowClick(element)"
        >
          <span
            v-if="isSelectedElement(element)"
            class="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-full bg-ink-gray-7"
          />

          <button
            class="drag-handle shrink-0 grid place-items-center size-5 rounded cursor-grab active:cursor-grabbing transition-opacity duration-150 hover:bg-surface-gray-3"
            :class="
              isRowActionVisible(element)
                ? 'opacity-70'
                : 'opacity-0 group-hover:opacity-60 hover:!opacity-100'
            "
            :title="__('Drag to reorder')"
            @click.stop
          >
            <LucideGripVertical class="size-3.5 text-ink-gray-4" />
          </button>

          <button
            v-if="element.is_group"
            class="shrink-0 grid place-items-center size-5 rounded hover:bg-surface-gray-3 transition-colors"
            @click.stop="toggleExpanded(element.doc_key)"
          >
            <LucideChevronRight
              class="size-4 text-ink-gray-5 transition-transform duration-200"
              :class="{ 'rotate-90': isExpanded(element.doc_key) }"
            />
          </button>
          <span v-else class="w-5 shrink-0" />

          <LucideFolder
            v-if="element.is_group"
            class="size-4 text-ink-gray-5 shrink-0"
          />
          <LucideLink
            v-else-if="element.is_external_link"
            class="size-4 text-ink-gray-5 shrink-0"
          />
          <LucideFileText v-else class="size-4 text-ink-gray-5 shrink-0" />

          <span
            class="text-sm truncate min-w-0 flex-1 transition-colors"
            :class="getTitleClass(element)"
          >
            {{ element.title }}
          </span>

          <Badge
            v-if="changeTypeMap.get(element.doc_key) === 'added'"
            variant="subtle"
            theme="blue"
            size="sm"
            class="shrink-0"
          >
            {{ __("New") }}
          </Badge>
          <Badge
            v-else-if="changeTypeMap.get(element.doc_key) === 'deleted'"
            variant="subtle"
            theme="red"
            size="sm"
            class="shrink-0"
          >
            {{ __("Deleted") }}
          </Badge>
          <Badge
            v-else-if="changeTypeMap.get(element.doc_key) === 'modified'"
            variant="subtle"
            theme="blue"
            size="sm"
            class="shrink-0"
          >
            {{ __("Modified") }}
          </Badge>
          <Badge
            v-else-if="changeTypeMap.get(element.doc_key) === 'reordered'"
            variant="subtle"
            theme="orange"
            size="sm"
            class="shrink-0"
          >
            {{ __("Reordered") }}
          </Badge>
          <span
            v-else-if="!element.is_group && !element.is_published"
            class="shrink-0 size-1.5 rounded-full bg-ink-orange-3"
            :title="__('Not Published')"
          />

          <Dropdown :options="getDropdownOptions(element)">
            <Button
              variant="ghost"
              size="sm"
              class="shrink-0 !size-6 transition-opacity duration-150"
              :class="
                isRowActionVisible(element)
                  ? 'opacity-100'
                  : 'opacity-0 group-hover:opacity-100'
              "
              @click.stop
            >
              <LucideMoreHorizontal class="size-4" />
            </Button>
          </Dropdown>
        </div>

        <div
          v-if="element.is_group"
          v-show="isExpanded(element.doc_key)"
          class="wiki-tree-children ml-[14px] pl-2.5 border-l border-outline-gray-2"
        >
          <NestedDraggable
            :items="element.children || []"
            :change-type-map="changeTypeMap"
            :level="level + 1"
            :parent-name="element.doc_key"
            :space-id="spaceId"
            :selected-page-id="selectedPageId"
            :selected-draft-key="selectedDraftKey"
            @create="(parent, isGroup) => emit('create', parent, isGroup)"
            @delete="(n) => emit('delete', n)"
            @rename="(n) => emit('rename', n)"
            @external-link="(parent) => emit('external-link', parent)"
            @edit-external-link="(el) => emit('edit-external-link', el)"
            @drag-state-change="handleNestedDragStateChange"
            @update="handleNestedUpdate"
          />
          <!-- Empty group actions -->
          <div
            v-if="!element.children || element.children.length === 0"
            class="flex flex-wrap items-center gap-1 py-1 pl-7 text-ink-gray-5"
          >
            <button
              class="flex items-center gap-1.5 text-xs hover:text-ink-gray-7 hover:bg-surface-gray-2 px-2 py-1 rounded-md transition-colors"
              @click="emit('create', element.doc_key, false)"
            >
              <LucideFilePlus class="size-3.5" />
              <span>{{ __("Add Page") }}</span>
            </button>
            <button
              class="flex items-center gap-1.5 text-xs hover:text-ink-gray-7 hover:bg-surface-gray-2 px-2 py-1 rounded-md transition-colors"
              @click="emit('create', element.doc_key, true)"
            >
              <LucideFolderPlus class="size-3.5" />
              <span>{{ __("Add Group") }}</span>
            </button>
          </div>
        </div>
      </div>
    </template>
  </draggable>
</template>

<script setup>
import { useChangeRequestStore } from '@/stores/changeRequest';
import { useStorage } from '@vueuse/core';
import { Badge, Button, Dropdown, toast } from 'frappe-ui';
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import draggable from 'vuedraggable';
import LucideChevronRight from '~icons/lucide/chevron-right';
import LucideFilePlus from '~icons/lucide/file-plus';
import LucideFileText from '~icons/lucide/file-text';
import LucideFolder from '~icons/lucide/folder';
import LucideFolderPlus from '~icons/lucide/folder-plus';
import LucideGripVertical from '~icons/lucide/grip-vertical';
import LucideLink from '~icons/lucide/link';
import LucideMoreHorizontal from '~icons/lucide/more-horizontal';

defineOptions({
	name: 'NestedDraggable',
});

const props = defineProps({
	items: {
		type: Array,
		required: true,
	},
	changeTypeMap: {
		type: Map,
		default: () => new Map(),
	},
	level: {
		type: Number,
		default: 0,
	},
	parentName: {
		type: String,
		default: null,
	},
	spaceId: {
		type: String,
		default: null,
	},
	selectedPageId: {
		type: String,
		default: null,
	},
	selectedDraftKey: {
		type: String,
		default: null,
	},
});

const emit = defineEmits([
	'create',
	'delete',
	'update',
	'rename',
	'external-link',
	'edit-external-link',
	'drag-state-change',
]);
const router = useRouter();
const crStore = useChangeRequestStore();

const localItems = ref([...props.items]);
const isDragging = ref(false);
let dragSettleTimer = null;

watch(
	() => props.items,
	(newItems) => {
		if (isDragging.value) return;
		localItems.value = [...newItems];
	},
);

const storageKey = computed(
	() => `wiki-tree-expanded-nodes-${props.spaceId || 'default'}`,
);
const expandedNodes = useStorage(storageKey, {});

function isExpanded(name) {
	return expandedNodes.value[name] === true;
}

function toggleExpanded(name) {
	expandedNodes.value[name] = !expandedNodes.value[name];
}

function handleRowClick(element) {
	if (props.changeTypeMap.get(element.doc_key) === 'deleted') {
		return;
	}

	if (element.is_group) {
		toggleExpanded(element.doc_key);
		return;
	}

	// External links open edit dialog instead of navigating
	if (element.is_external_link) {
		emit('edit-external-link', element);
		return;
	}

	if (element.document_name) {
		router.push({
			name: 'SpacePage',
			params: { spaceId: props.spaceId, pageId: element.document_name },
		});
		return;
	}

	router.push({
		name: 'DraftChangeRequest',
		params: { spaceId: props.spaceId, docKey: element.doc_key },
	});
}

function isSelectedElement(element) {
	const isSelectedPage =
		!element.is_group && element.document_name === props.selectedPageId;
	const isSelectedDraft =
		!element.document_name && element.doc_key === props.selectedDraftKey;

	return isSelectedPage || isSelectedDraft;
}

function isRowActionVisible(element) {
	return isSelectedElement(element);
}

function getRowClasses(element) {
	const classes = [];

	if (isSelectedElement(element)) {
		classes.push('bg-surface-gray-3');
	} else {
		classes.push('bg-transparent', 'hover:bg-surface-gray-2');
	}

	if (props.changeTypeMap.get(element.doc_key) === 'deleted') {
		classes.push('cursor-not-allowed', 'opacity-60');
	} else {
		classes.push('cursor-pointer');
	}

	return classes;
}

function getTitleClass(element) {
	if (props.changeTypeMap.get(element.doc_key) === 'deleted') {
		return 'text-ink-gray-4 line-through';
	}
	if (isSelectedElement(element)) {
		return 'text-ink-gray-9 font-medium';
	}
	if (element.is_group && isExpanded(element.doc_key)) {
		return 'text-ink-gray-9 font-medium';
	}
	if (element.is_published || element.is_group) {
		return 'text-ink-gray-8';
	}
	return 'text-ink-gray-5';
}

function onDragStart() {
	isDragging.value = true;
	emit('drag-state-change', true);
	if (dragSettleTimer) {
		clearTimeout(dragSettleTimer);
		dragSettleTimer = null;
	}
}

function onDragEnd() {
	if (dragSettleTimer) clearTimeout(dragSettleTimer);
	dragSettleTimer = setTimeout(() => {
		isDragging.value = false;
		emit('drag-state-change', false);
		dragSettleTimer = null;
	}, 1000);
}

function handleChange(evt) {
	if (evt.added || evt.moved) {
		const item = evt.added?.element || evt.moved?.element;
		const newIndex = evt.added?.newIndex ?? evt.moved?.newIndex;

		emit('update', {
			item,
			newParent: props.parentName,
			newIndex,
			siblings: localItems.value,
			type: evt.added ? 'added' : 'moved',
		});
	}
}

function handleNestedUpdate(payload) {
	emit('update', payload);
}

function handleNestedDragStateChange(state) {
	emit('drag-state-change', state);
}

async function togglePublish(element) {
	if (!crStore.currentChangeRequest) {
		toast.error(__('No active change request'));
		return;
	}
	const newStatus = element.is_published ? 0 : 1;
	try {
		await crStore.updatePage(
			crStore.currentChangeRequest.name,
			element.doc_key,
			{
				is_published: newStatus,
			},
		);
		const action = element.is_published ? __('unpublished') : __('published');
		toast.success(__('Page {0}', [action]));
		emit('update', { type: 'refresh' });
	} catch (error) {
		toast.error(error.messages?.[0] || __('Error updating publish status'));
	}
}

function getDropdownOptions(element) {
	const options = [];

	if (element.is_group) {
		options.push(
			...[
				{
					label: __('Add Page'),
					icon: 'file-plus',
					onClick: () => emit('create', element.doc_key, false),
				},
				{
					label: __('Add Group'),
					icon: 'folder-plus',
					onClick: () => emit('create', element.doc_key, true),
				},
				{
					label: __('Add External Link'),
					icon: 'link',
					onClick: () => emit('external-link', element.doc_key),
				},
				{
					label: __('Rename'),
					icon: 'edit-2',
					onClick: () => emit('rename', element),
				},
			],
		);
	}

	if (!element.is_group) {
		options.push({
			label: __('Change Title'),
			icon: 'edit-2',
			onClick: () => emit('rename', element),
		});
		options.push({
			label: element.is_published ? __('Unpublish') : __('Publish'),
			icon: element.is_published ? 'eye-off' : 'eye',
			onClick: () => togglePublish(element),
		});
	}

	const hasChildren = element.is_group && element.children?.length > 0;
	if (!hasChildren) {
		options.push({
			group: __('Danger'),
			items: [
				{
					label: __('Delete'),
					icon: 'trash-2',
					theme: 'red',
					onClick: () => emit('delete', element),
				},
			],
		});
	}

	return options;
}

onBeforeUnmount(() => {
	if (dragSettleTimer) {
		clearTimeout(dragSettleTimer);
		dragSettleTimer = null;
	}
	emit('drag-state-change', false);
});
</script>

<style scoped>
.nested-draggable-area {
  min-height: 8px;
}

.draggable-item {
  position: relative;
}

.dragging-ghost {
  opacity: 0.5;
  background-color: var(--surface-blue-1, #e0f2fe);
  border-radius: 12px;
}

.dragging-item {
  opacity: 0.8;
  background-color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 12px;
}

.drag-handle:active {
  cursor: grabbing;
}
</style>
