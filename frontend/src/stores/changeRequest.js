import { useUserStore } from '@/stores/user';
import { createResource } from 'frappe-ui';
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export const useChangeRequestStore = defineStore('changeRequest', () => {
	const currentChangeRequest = ref(null);
	const isLoadingChangeRequest = ref(false);
	let initChangeRequestPromise = null;

	const isChangeRequestMode = computed(
		() => useUserStore().shouldUseChangeRequestMode,
	);
	const hasActiveChangeRequest = computed(() => !!currentChangeRequest.value);

	const changeRequestResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.get_change_request',
		onSuccess(data) {
			currentChangeRequest.value = data;
		},
	});

	const draftChangeRequestResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.get_or_create_draft_change_request',
		onSuccess(data) {
			currentChangeRequest.value = data;
			isLoadingChangeRequest.value = false;
		},
		onError(error) {
			console.error('Failed to get/create change request:', error);
			isLoadingChangeRequest.value = false;
		},
	});

	const changesResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.diff_change_request',
	});

	const submitReviewResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.request_review',
		onSuccess() {
			refreshChangeRequest();
		},
	});

	const archiveChangeRequestResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.archive_change_request',
		onSuccess() {
			currentChangeRequest.value = null;
		},
	});

	const mergeChangeRequestResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.merge_change_request',
	});

	const createPageResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.create_cr_page',
	});

	const updatePageResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.update_cr_page',
	});

	const deletePageResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.delete_cr_page',
	});

	const movePageResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.move_cr_page',
	});

	const reorderChildrenResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.reorder_cr_children',
	});

	async function refreshChangeRequest() {
		if (!currentChangeRequest.value) return null;
		await changeRequestResource.submit({
			name: currentChangeRequest.value.name,
		});
		return currentChangeRequest.value;
	}

	async function initChangeRequest(spaceId) {
		if (!isChangeRequestMode.value || !spaceId) return null;

		if (isLoadingChangeRequest.value && initChangeRequestPromise) {
			await initChangeRequestPromise;
			return currentChangeRequest.value;
		}

		isLoadingChangeRequest.value = true;
		initChangeRequestPromise = draftChangeRequestResource.submit({
			wiki_space: spaceId,
		});
		try {
			await initChangeRequestPromise;
		} finally {
			initChangeRequestPromise = null;
		}
		return currentChangeRequest.value;
	}

	async function loadChanges() {
		if (!currentChangeRequest.value) return [];
		await changesResource.submit({
			name: currentChangeRequest.value.name,
			scope: 'summary',
		});
		return changesResource.data || [];
	}

	async function submitForReview(reviewers = []) {
		if (!currentChangeRequest.value) return null;
		await submitReviewResource.submit({
			name: currentChangeRequest.value.name,
			reviewers,
		});
		return currentChangeRequest.value;
	}

	async function archiveChangeRequest() {
		if (!currentChangeRequest.value) return null;
		await archiveChangeRequestResource.submit({
			name: currentChangeRequest.value.name,
		});
		return currentChangeRequest.value;
	}

	async function mergeChangeRequest() {
		if (!currentChangeRequest.value) return null;
		await mergeChangeRequestResource.submit({
			name: currentChangeRequest.value.name,
		});
		return currentChangeRequest.value;
	}

	const changeCount = computed(() => changesResource.data?.length || 0);

	const canSubmit = computed(() => {
		return (
			['Draft', 'Changes Requested'].includes(
				currentChangeRequest.value?.status,
			) && changeCount.value > 0
		);
	});

	const canWithdraw = computed(() => {
		return ['In Review', 'Changes Requested'].includes(
			currentChangeRequest.value?.status,
		);
	});

	async function createPage(
		changeRequestName,
		parentKey,
		title,
		content,
		isGroup = false,
		isExternalLink = false,
		externalUrl = null,
	) {
		return await createPageResource.submit({
			name: changeRequestName,
			parent_key: parentKey,
			title,
			content,
			is_group: isGroup,
			is_published: true,
			is_external_link: isExternalLink,
			external_url: externalUrl,
		});
	}

	async function updatePage(changeRequestName, docKey, fields) {
		return await updatePageResource.submit({
			name: changeRequestName,
			doc_key: docKey,
			fields,
		});
	}

	async function deletePage(changeRequestName, docKey) {
		return await deletePageResource.submit({
			name: changeRequestName,
			doc_key: docKey,
		});
	}

	async function movePage(
		changeRequestName,
		docKey,
		newParentKey,
		newOrderIndex,
	) {
		return await movePageResource.submit({
			name: changeRequestName,
			doc_key: docKey,
			new_parent_key: newParentKey,
			new_order_index: newOrderIndex,
		});
	}

	async function reorderChildren(changeRequestName, parentKey, orderedDocKeys) {
		return await reorderChildrenResource.submit({
			name: changeRequestName,
			parent_key: parentKey,
			ordered_doc_keys: orderedDocKeys,
		});
	}

	return {
		currentChangeRequest,
		isLoadingChangeRequest,
		isChangeRequestMode,
		hasActiveChangeRequest,
		changeCount,
		canSubmit,
		canWithdraw,
		changeRequestResource,
		draftChangeRequestResource,
		changesResource,
		submitReviewResource,
		archiveChangeRequestResource,
		mergeChangeRequestResource,
		createPageResource,
		updatePageResource,
		deletePageResource,
		movePageResource,
		reorderChildrenResource,
		refreshChangeRequest,
		initChangeRequest,
		loadChanges,
		submitForReview,
		archiveChangeRequest,
		mergeChangeRequest,
		createPage,
		updatePage,
		deletePage,
		movePage,
		reorderChildren,
	};
});
