/**
 * Run `run` once typing pauses for `delay` ms, and at least every `maxWait`
 * ms while it continues. `flush` runs a pending call now; callers flush before
 * anything reads the result (blur, save, unmount).
 */
export function createTrailingScheduler({ delay, maxWait, run }) {
	let timer = null;
	let firstScheduledAt = null;

	function cancel() {
		clearTimeout(timer);
		timer = null;
		firstScheduledAt = null;
	}

	function flush() {
		if (timer === null) return;
		cancel();
		run();
	}

	function schedule() {
		const now = Date.now();
		firstScheduledAt ??= now;
		const untilMaxWait = firstScheduledAt + maxWait - now;
		clearTimeout(timer);
		timer = setTimeout(flush, Math.max(0, Math.min(delay, untilMaxWait)));
	}

	return {
		schedule,
		flush,
		cancel,
		get pending() {
			return timer !== null;
		},
	};
}

/**
 * Cache `fn` for its most recent argument, compared by identity. ProseMirror
 * docs are immutable and prop strings are replaced, not mutated, so identity
 * is enough to know the input has not changed.
 */
export function memoizeLast(fn) {
	let hasValue = false;
	let lastArg;
	let lastValue;
	return (arg) => {
		if (!hasValue || arg !== lastArg) {
			lastValue = fn(arg);
			lastArg = arg;
			hasValue = true;
		}
		return lastValue;
	};
}

const flushRequests = new EventTarget();

/**
 * Ask a mounted editor to report its pending edit now. Submit and merge read
 * the draft store directly, and a button click does not always blur the
 * editor first (Safari does not focus buttons), so they request a flush.
 */
export function requestEditorFlush() {
	flushRequests.dispatchEvent(new Event('flush'));
}

export function onEditorFlushRequest(handler) {
	flushRequests.addEventListener('flush', handler);
	return () => flushRequests.removeEventListener('flush', handler);
}

/**
 * The saved text to compare the editor's snapshot against.
 *
 * The store keeps the exact text it last sent (or received), and the editor's
 * snapshot is that text after one normalizing pass. When the saved text is
 * already the snapshot, it IS the baseline: normalizing it again is wrong for a
 * page where normalizing twice does not give the same result, because the extra
 * pass makes a page the server holds verbatim read as changed. That page then
 * stays "unsaved" however often it is saved, blocks Submit and Merge, and keeps
 * the editor re-reporting. Anything else is normalized, as before, so text the
 * server stored in its own shape still compares equal.
 *
 * `normalize` is only called when needed: it parses the whole page.
 */
export function savedBaseline(current, rawSaved, normalize) {
	return rawSaved === current ? current : normalize(rawSaved);
}
