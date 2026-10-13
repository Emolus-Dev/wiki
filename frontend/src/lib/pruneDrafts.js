import { pruneFinishedDrafts } from '@/stores/draftPersistence';
import { createResource } from 'frappe-ui';

// Runs once per page load, after the app has settled, so it never competes with
// the editor for the main thread.
export function schedulePruneFinishedDrafts() {
	const run = () => {
		pruneFinishedDrafts(async (names) => {
			const rows = await createResource({
				url: 'frappe.client.get_list',
				params: {
					doctype: 'Wiki Change Request',
					fields: ['name', 'status'],
					filters: [['name', 'in', names]],
					limit_page_length: names.length,
				},
			}).fetch();
			return rows;
		});
	};
	if (typeof requestIdleCallback === 'function') {
		setTimeout(() => requestIdleCallback(run, { timeout: 10000 }), 5000);
	} else {
		setTimeout(run, 8000);
	}
}
