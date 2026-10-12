// A small, always-on activity log for finding what freezes the editor.
//
// A frozen tab cannot be inspected: the console will not open and nothing it
// prints can be read. So each heavy step writes a line to localStorage *before*
// it runs and another when it ends. After a freeze, the last `:start` with no
// `:end` after it is the step that never finished. localStorage is shared by
// every tab of the site, so the log can be read from another tab (DevTools >
// Application > Local storage > `wiki:trace`).
//
// Cheap on purpose: a ring of 80 short entries, written only around steps that
// are already expensive (parsing, saving, loading a page).

const KEY = 'wiki:trace';
const LIMIT = 80;

function storage() {
	try {
		return typeof localStorage === 'undefined' ? null : localStorage;
	} catch {
		return null;
	}
}

export function trace(event, detail) {
	const store = storage();
	if (!store) return;
	try {
		const log = JSON.parse(store.getItem(KEY) || '[]');
		log.push({
			t: new Date().toISOString().slice(11, 23),
			e: event,
			...(detail ? { d: detail } : {}),
		});
		store.setItem(KEY, JSON.stringify(log.slice(-LIMIT)));
	} catch {
		// Tracing must never break the app.
	}
}

/** Run `fn`, logging when it starts and how long it took. */
export function timed(event, fn, detail) {
	trace(`${event}:start`, detail);
	const started = Date.now();
	try {
		return fn();
	} finally {
		trace(`${event}:end`, { ms: Date.now() - started });
	}
}

/** Same for an async step; the end is logged when the promise settles. */
export async function timedAsync(event, fn, detail) {
	trace(`${event}:start`, detail);
	const started = Date.now();
	try {
		return await fn();
	} finally {
		trace(`${event}:end`, { ms: Date.now() - started });
	}
}

/** Log any task that blocks the page for over half a second, once it ends. */
export function watchLongTasks() {
	try {
		new PerformanceObserver((list) => {
			for (const entry of list.getEntries()) {
				if (entry.duration >= 500) {
					trace('longtask', { ms: Math.round(entry.duration) });
				}
			}
		}).observe({ entryTypes: ['longtask'] });
	} catch {
		// Not supported in this browser.
	}
}

export function readTrace() {
	try {
		return JSON.parse(storage()?.getItem(KEY) || '[]');
	} catch {
		return [];
	}
}
