import { createResource, toast } from 'frappe-ui';
import { computed, ref, watch } from 'vue';
import { useChangeRequestStore } from '@/stores/changeRequest';
import { handleError } from '@/lib/errors';

function findNodeByDocKey(nodes, docKey) {
	if (!nodes) return null;
	for (const node of nodes) {
		if (node.doc_key === docKey) return node;
		const found = findNodeByDocKey(node.children, docKey);
		if (found) return found;
	}
	return null;
}

export function useSpaceChangeRequestFlow({ props, route, router, space }) {
	const crStore = useChangeRequestStore();
	const isTreeReordering = ref(false);

	const currentPageId = computed(() => route.params.pageId || null);
	const currentDraftKey = computed(() => route.params.docKey || null);

	const crTree = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.get_cr_tree',
		makeParams() {
			if (!crStore.currentChangeRequest?.name) {
				return null;
			}
			return { name: crStore.currentChangeRequest.name };
		},
		auto: false,
	});

	const treeData = computed(() => crTree.data);
	const changeTypeMap = computed(() => {
		const map = new Map();
		for (const change of crStore.changes) {
			map.set(change.doc_key, change.change_type);
		}
		return map;
	});

	watch(
		[() => space.doc, () => crStore.isChangeRequestMode, () => crStore.currentChangeRequest?.name],
		async ([doc, isMode, crName], oldValues) => {
			if (!doc || !isMode) return;

			const [oldDoc, , oldCrName] = oldValues || [];
			if (doc !== oldDoc) {
				crStore.currentChangeRequest = null;
			}

			if (!crStore.currentChangeRequest) {
				await crStore.initChangeRequest(props.spaceId);
				return;
			}

			if (crName && crName !== oldCrName) {
				await crStore.loadChanges();
				await crTree.reload();
			}
		},
		{ immediate: true },
	);

	async function refreshTree() {
		if (!crStore.currentChangeRequest?.name) {
			return;
		}
		await crTree.reload();
		await crStore.loadChanges();
	}

	function handleReorderStateChange(isReordering) {
		isTreeReordering.value = Boolean(isReordering);
	}

	async function handleSubmitChangeRequest() {
		try {
			const result = await crStore.submitForReview();
			toast.success(__('Change request submitted for review'));
			if (result?.name) {
				router.push({
					name: 'ChangeRequestReview',
					params: { changeRequestId: result.name },
				});
			}
		} catch (error) {
			handleError({
				error,
				context: 'Error submitting change request',
				fallback: __('Error submitting for review'),
				notify: toast.error,
			});
		}
	}

	async function handleArchiveChangeRequest() {
		try {
			await crStore.archiveChangeRequest();
			toast.success(__('Change request archived'));
			crStore.currentChangeRequest = null;
			await crStore.initChangeRequest(props.spaceId);
			await refreshTree();
		} catch (error) {
			handleError({
				error,
				context: 'Error archiving change request',
				fallback: __('Error archiving change request'),
				notify: toast.error,
			});
		}
	}

	async function handleMergeChangeRequest() {
		const docKey = currentDraftKey.value;
		try {
			await crStore.mergeChangeRequest();
			toast.success(__('Change request merged'));
			crStore.currentChangeRequest = null;
			await crStore.initChangeRequest(props.spaceId);
			await refreshTree();

			if (docKey) {
				const node = findNodeByDocKey(treeData.value?.children, docKey);
				if (node?.document_name) {
					router.push({
						name: 'SpacePage',
						params: { spaceId: props.spaceId, pageId: node.document_name },
					});
				}
			}
		} catch (error) {
			handleError({
				error,
				context: 'Error merging change request',
				fallback: __('Error merging change request'),
				notify: toast.error,
			});
		}
	}

	return {
		crStore,
		isTreeReordering,
		currentPageId,
		currentDraftKey,
		treeData,
		changeTypeMap,
		refreshTree,
		handleReorderStateChange,
		handleSubmitChangeRequest,
		handleArchiveChangeRequest,
		handleMergeChangeRequest,
	};
}
