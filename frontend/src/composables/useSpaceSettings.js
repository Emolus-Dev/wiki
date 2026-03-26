import { toast } from 'frappe-ui';
import { ref, watch } from 'vue';
import { handleError } from '@/lib/errors';

export function useSpaceSettings(space, refreshTree) {
	const showSettingsDialog = ref(false);
	const showUpdateRoutesDialog = ref(false);
	const showCloneSpaceDialog = ref(false);
	const newRoute = ref('');
	const updatingRoutes = ref(false);
	const cloneRoute = ref('');
	const cloningSpace = ref(false);
	const enableFeedbackCollection = ref(false);
	const updatingFeedbackSetting = ref(false);
	const isPublished = ref(true);
	const updatingPublishSetting = ref(false);

	watch(
		() => space.doc,
		(doc) => {
			if (!doc) return;
			enableFeedbackCollection.value = Boolean(doc.enable_feedback_collection);
			isPublished.value = Boolean(doc.is_published);
		},
		{ immediate: true },
	);

	async function updateFeedbackSetting(value) {
		updatingFeedbackSetting.value = true;
		try {
			await space.setValue.submit({
				enable_feedback_collection: value ? 1 : 0,
			});
		} catch (error) {
			enableFeedbackCollection.value = !value;
			handleError({
				error,
				context: 'Failed to update feedback setting',
				fallback: __('Error updating feedback setting'),
				notify: toast.error,
			});
		} finally {
			updatingFeedbackSetting.value = false;
		}
	}

	async function updatePublishSetting(value) {
		updatingPublishSetting.value = true;
		try {
			await space.setValue.submit({
				is_published: value ? 1 : 0,
			});
		} catch (error) {
			isPublished.value = !value;
			handleError({
				error,
				context: 'Failed to update publish setting',
				fallback: __('Error updating publish setting'),
				notify: toast.error,
			});
		} finally {
			updatingPublishSetting.value = false;
		}
	}

	function openUpdateRoutesDialog() {
		newRoute.value = space.doc?.route || '';
		showUpdateRoutesDialog.value = true;
	}

	function openCloneSpaceDialog() {
		cloneRoute.value = space.doc?.route ? `${space.doc.route}-copy` : '';
		showCloneSpaceDialog.value = true;
	}

	async function updateRoutes(close) {
		if (!newRoute.value?.trim()) {
			return;
		}

		updatingRoutes.value = true;
		try {
			await space.updateRoutes.submit({ new_route: newRoute.value.trim() });
			close();
			await space.reload();
			await refreshTree();
		} catch (error) {
			handleError({
				error,
				context: 'Failed to update routes',
				fallback: __('Error updating routes'),
				notify: toast.error,
			});
		} finally {
			updatingRoutes.value = false;
		}
	}

	async function cloneSpace(close) {
		if (!cloneRoute.value?.trim()) {
			return;
		}

		cloningSpace.value = true;
		try {
			await space.cloneWikiSpace.submit({
				new_space_route: cloneRoute.value.trim(),
			});
			toast.success(__('Cloning started in background'));
			close();
		} catch (error) {
			handleError({
				error,
				context: 'Failed to start clone',
				fallback: __('Error starting clone'),
				notify: toast.error,
			});
		} finally {
			cloningSpace.value = false;
		}
	}

	return {
		showSettingsDialog,
		showUpdateRoutesDialog,
		showCloneSpaceDialog,
		newRoute,
		updatingRoutes,
		cloneRoute,
		cloningSpace,
		enableFeedbackCollection,
		updatingFeedbackSetting,
		isPublished,
		updatingPublishSetting,
		updateFeedbackSetting,
		updatePublishSetting,
		openUpdateRoutesDialog,
		openCloneSpaceDialog,
		updateRoutes,
		cloneSpace,
	};
}
