<template>
	<!-- Static (not dismissible): a stray click outside must not throw away a
	     review half done. It closes through "Back to editor" or a decision. -->
	<Dialog
		:open="Boolean(crStore.reviewDialogName)"
		size="7xl"
		bare
		:dismissible="false"
		@update:open="(open) => !open && crActions.onReviewClosed()"
	>
		<ContributionReview
			v-if="crStore.reviewDialogName"
			:key="crStore.reviewDialogName"
			:change-request-id="crStore.reviewDialogName"
			in-dialog
			:data-change-request="crStore.reviewDialogName"
			data-testid="review-dialog"
			@merged="crActions.onReviewMerged"
			@close="crActions.onReviewClosed"
		/>
	</Dialog>
</template>

<script setup>
import { Dialog } from 'frappe-ui';
import { useChangeRequestActions } from '../composables/useChangeRequestActions';
import ContributionReview from '../pages/ContributionReview.vue';
import { useChangeRequestStore } from '../stores/changeRequest';

const crStore = useChangeRequestStore();
const crActions = useChangeRequestActions();
</script>
