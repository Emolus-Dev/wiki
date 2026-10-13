import { useDocumentVisibility, useIntervalFn } from '@vueuse/core';
import { createResource } from 'frappe-ui';
import { onBeforeUnmount, ref, toValue, watch } from 'vue';

const PING_EVERY_MS = 20000;

/**
 * Who else has this page open for editing. Pings while the tab is visible and
 * stops when it is hidden or the editor goes away, so a forgotten tab drops off
 * after the server's timeout. The server keeps pings in the cache only.
 */
export function usePagePresence({ space, page, enabled }) {
	const others = ref([]);
	const visibility = useDocumentVisibility();

	const ping = createResource({
		url: 'wiki.api.presence.heartbeat',
		onSuccess(data) {
			others.value = data || [];
		},
	});
	const leaveRequest = createResource({ url: 'wiki.api.presence.leave' });

	function active() {
		return Boolean(
			toValue(enabled) &&
				toValue(space) &&
				toValue(page) &&
				visibility.value === 'visible',
		);
	}

	function send() {
		if (!active()) return;
		ping.submit({ space: toValue(space), page: toValue(page) });
	}

	const timer = useIntervalFn(send, PING_EVERY_MS, { immediateCallback: false });

	let lastKey = null;
	function leave() {
		if (lastKey) leaveRequest.submit(lastKey);
		lastKey = null;
		others.value = [];
	}

	watch(
		[() => toValue(space), () => toValue(page), () => toValue(enabled), visibility],
		() => {
			const key = active() ? { space: toValue(space), page: toValue(page) } : null;
			if (lastKey && (!key || key.space !== lastKey.space || key.page !== lastKey.page)) {
				leave();
			}
			if (key) {
				lastKey = key;
				send();
				timer.resume();
			} else {
				timer.pause();
			}
		},
		{ immediate: true },
	);

	onBeforeUnmount(() => {
		timer.pause();
		leave();
	});

	return { others };
}
