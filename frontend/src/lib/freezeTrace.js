// A small, always-on activity log for finding what freezes the editor.
//
// A frozen tab cannot be inspected: the console will not open and nothing it
// prints can be read. So each heavy step writes a line to localStorage *before*
// it runs and another when it ends. After a freeze, the last `:start` with no
// `:end` after it is the step that never finished. localStorage is shared by
// every tab of the site, so the log can be read from another tab (DevTools >
// Application > Local storage > `wiki:trace`).
//
// Off by default. Turn it on from DevTools on any tab of the site with
// `localStorage.setItem('wiki:debug', '1')` (and off by removing it). Two rare,
// important events are always logged because they mean something already went
// wrong: a content-ready loop being stopped and a page re-saved before submit.
//
// Cheap when on: a ring of 80 short entries, written only around steps that are
// already expensive (parsing, saving, loading a page).

const KEY = 'wiki:trace';
const FLAG = 'wiki:debug';
const LIMIT = 80;
const ALWAYS = new Set([
	'editor:contentReady:loop-stopped',
	'draft:verify:resave',
]);

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
		if (!ALWAYS.has(event) && store.getItem(FLAG) !== '1') return;
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

/** Length plus a short hash: enough to tell two long strings apart in a log. */
export function fingerprint(text) {
	const value = text ?? '';
	let hash = 5381;
	for (let i = 0; i < value.length; i++) {
		hash = ((hash << 5) + hash + value.charCodeAt(i)) | 0;
	}
	return `${value.length}:${(hash >>> 0).toString(16)}`;
}

/** Where two strings first differ, with a little context from each. */
export function firstDifference(a, b, context = 40) {
	const left = a ?? '';
	const right = b ?? '';
	const limit = Math.min(left.length, right.length);
	let at = 0;
	while (at < limit && left[at] === right[at]) at++;
	if (at === limit && left.length === right.length) return null;
	const from = Math.max(at - context, 0);
	return {
		at,
		a: left.slice(from, at + context),
		b: right.slice(from, at + context),
		lengths: [left.length, right.length],
	};
}

/**
 * Allow at most `max` calls per `windowMs`. For work that should happen once
 * or twice but can be re-triggered by its own result: past the limit it is
 * a loop, and the caller stops feeding it.
 */
export function createBurstLimiter({ windowMs, max, now = Date.now }) {
	let windowStart = 0;
	let count = 0;
	return function allow() {
		const time = now();
		if (time - windowStart > windowMs) {
			windowStart = time;
			count = 0;
		}
		count += 1;
		return count <= max;
	};
}
