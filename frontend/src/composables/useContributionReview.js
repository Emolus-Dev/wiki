import { computed, reactive, ref } from 'vue';
import { createDocumentResource, createResource, toast } from 'frappe-ui';
import { useUserStore } from '@/stores/user';
import { useChangeRequestStore } from '@/stores/changeRequest';
import { useChangeTypeDisplay } from '@/composables/useChangeTypeDisplay';
import { getErrorMessage, handleError } from '@/lib/errors';

export function useContributionReview(changeRequestId) {
	const { getChangeIcon, getChangeIconClass, getChangeTheme, getChangeLabel, getChangeDescription } = useChangeTypeDisplay();
	const userStore = useUserStore();
	const crStore = useChangeRequestStore();

	const showRejectDialog = ref(false);
	const rejectComment = ref('');
	const expandedChanges = reactive(new Set());
	const diffsByDocKey = reactive({});
	const hasConflicts = ref(false);
	const conflicts = ref([]);
	const resolutions = reactive({});
	const expandedConflicts = reactive(new Set());
	const resolvingMerge = ref(false);

	const resolvedCount = computed(() =>
		Object.values(resolutions).filter((value) => value === 'ours' || value === 'theirs').length,
	);
	const allResolved = computed(
		() => conflicts.value.length > 0 && resolvedCount.value === conflicts.value.length,
	);

	const changeRequest = createDocumentResource({
		doctype: 'Wiki Change Request',
		name: changeRequestId,
		auto: true,
	});

	const changes = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.diff_change_request',
		params: { name: changeRequestId, scope: 'summary' },
		auto: true,
	});

	const diffResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.diff_change_request',
	});
	const mergeResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.merge_change_request',
	});
	const conflictsResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.get_merge_conflicts',
	});
	const resolveResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.resolve_merge_conflict',
	});
	const retryResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.retry_merge_after_resolution',
	});
	const rejectResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.review_action',
	});
	const withdrawResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request.archive_change_request',
	});

	const isManager = computed(() => userStore.isWikiManager);
	const isOwner = computed(() => changeRequest.doc?.owner === userStore.data?.name);
	const canReview = computed(
		() => isManager.value && ['In Review', 'Approved'].includes(changeRequest.doc?.status),
	);
	const canWithdraw = computed(
		() => isOwner.value && ['In Review', 'Changes Requested'].includes(changeRequest.doc?.status),
	);

	const reviewNote = computed(() => {
		if (changeRequest.doc?.status !== 'Changes Requested') return null;
		const reviewer = (changeRequest.doc?.reviewers || []).find(
			(row) => row.status === 'Changes Requested' && row.comment,
		);
		if (!reviewer) return null;
		return {
			comment: reviewer.comment,
			reviewer: reviewer.reviewer,
			reviewed_at: reviewer.reviewed_at,
		};
	});

	function setResolution(conflictName, value) {
		if (resolutions[conflictName] === value) {
			delete resolutions[conflictName];
			return;
		}
		resolutions[conflictName] = value;
	}

	function toggleConflict(conflictName) {
		if (expandedConflicts.has(conflictName)) {
			expandedConflicts.delete(conflictName);
			return;
		}
		expandedConflicts.add(conflictName);
	}

	async function reloadSummary() {
		changeRequest.reload();
		await changes.submit({ name: changeRequestId, scope: 'summary' });
	}

	async function fetchConflicts() {
		try {
			const result = await conflictsResource.submit({ name: changeRequestId });
			conflicts.value = result || [];
			for (const key in resolutions) delete resolutions[key];
			for (const conflict of conflicts.value) {
				resolutions[conflict.name] = 'theirs';
			}
			hasConflicts.value = conflicts.value.length > 0;
		} catch (error) {
			handleError({
				error,
				context: 'Error loading conflicts',
				fallback: __('Error loading conflicts'),
				notify: toast.error,
			});
		}
	}

	async function toggleChange(docKey) {
		if (expandedChanges.has(docKey)) {
			expandedChanges.delete(docKey);
			return;
		}
		expandedChanges.add(docKey);
		if (diffsByDocKey[docKey]) {
			return;
		}
		try {
			const result = await diffResource.submit({
				name: changeRequestId,
				scope: 'page',
				doc_key: docKey,
			});
			diffsByDocKey[docKey] = result;
		} catch (error) {
			handleError({
				error,
				context: 'Error loading diff',
				fallback: __('Error loading diff'),
				notify: toast.error,
			});
		}
	}

	async function handleApprove() {
		try {
			await mergeResource.submit({ name: changeRequestId });
			toast.success(__('Change request merged'));
			if (crStore.currentChangeRequest?.name === changeRequestId) {
				crStore.currentChangeRequest = null;
			}
			await reloadSummary();
		} catch (error) {
			const message = getErrorMessage(error, __('Error merging change request'));
			if (error.exc_type === 'ValidationError') {
				await fetchConflicts();
				if (!hasConflicts.value) {
					toast.error(message);
				}
				return;
			}
			handleError({
				error,
				context: 'Error merging change request',
				fallback: __('Error merging change request'),
				notify: toast.error,
			});
		}
	}

	async function handleResolveAndMerge() {
		resolvingMerge.value = true;
		try {
			for (const conflict of conflicts.value) {
				try {
					await resolveResource.submit({
						conflict_name: conflict.name,
						resolution: resolutions[conflict.name],
					});
				} catch (error) {
					const message = getErrorMessage(error, '');
					if (message.includes('already resolved')) {
						continue;
					}
					throw error;
				}
			}
			await retryResource.submit({ name: changeRequestId });
			toast.success(__('Conflicts resolved and change request merged'));
			hasConflicts.value = false;
			conflicts.value = [];
			if (crStore.currentChangeRequest?.name === changeRequestId) {
				crStore.currentChangeRequest = null;
			}
			await reloadSummary();
		} catch (error) {
			handleError({
				error,
				context: 'Error resolving conflicts',
				fallback: __('Error resolving conflicts'),
				notify: toast.error,
			});
		} finally {
			resolvingMerge.value = false;
		}
	}

	async function handleReject(close) {
		if (!rejectComment.value.trim()) {
			toast.warning(__('Please provide feedback'));
			return;
		}
		try {
			await rejectResource.submit({
				name: changeRequestId,
				reviewer: userStore.data?.name,
				status: 'Changes Requested',
				comment: rejectComment.value.trim(),
			});
			toast.success(__('Requested changes'));
			rejectComment.value = '';
			close();
			changeRequest.reload();
		} catch (error) {
			handleError({
				error,
				context: 'Error requesting changes',
				fallback: __('Error requesting changes'),
				notify: toast.error,
			});
		}
	}

	async function handleWithdraw() {
		try {
			await withdrawResource.submit({ name: changeRequestId });
			toast.success(__('Change request archived'));
			changeRequest.reload();
		} catch (error) {
			handleError({
				error,
				context: 'Error archiving change request',
				fallback: __('Error archiving change request'),
				notify: toast.error,
			});
		}
	}

	function getStatusTheme(status) {
		switch (status) {
			case 'Draft': return 'blue';
			case 'In Review': return 'orange';
			case 'Changes Requested': return 'red';
			case 'Approved':
			case 'Merged': return 'green';
			case 'Archived': return 'gray';
			default: return 'gray';
		}
	}

	function getConflictTheme(type) {
		switch (type) {
			case 'content': return 'blue';
			case 'meta': return 'orange';
			case 'tree': return 'red';
			default: return 'gray';
		}
	}

	function formatDate(dateStr) {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	return {
		getChangeIcon,
		getChangeIconClass,
		getChangeTheme,
		getChangeLabel,
		getChangeDescription,
		showRejectDialog,
		rejectComment,
		expandedChanges,
		diffsByDocKey,
		hasConflicts,
		conflicts,
		resolutions,
		expandedConflicts,
		resolvingMerge,
		resolvedCount,
		allResolved,
		changeRequest,
		changes,
		mergeResource,
		rejectResource,
		withdrawResource,
		canReview,
		canWithdraw,
		reviewNote,
		setResolution,
		toggleConflict,
		fetchConflicts,
		toggleChange,
		handleApprove,
		handleResolveAndMerge,
		handleReject,
		handleWithdraw,
		getStatusTheme,
		getConflictTheme,
		formatDate,
	};
}
