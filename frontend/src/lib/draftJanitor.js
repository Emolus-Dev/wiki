// Local editor drafts are keyed by change request. Once a change request is
// merged, rejected or archived its drafts can never be restored again, so they
// only take space. This decides which ones are safe to drop.

const FINISHED_STATUSES = new Set(['Merged', 'Rejected', 'Archived']);

/** `cr:<name>:<docKey>` -> `<name>`; anything else (tree snapshots) -> null. */
export function crNameFromKey(key) {
	if (typeof key !== 'string' || !key.startsWith('cr:')) return null;
	const name = key.slice(3).split(':')[0];
	return name || null;
}

export function draftCrNames(keys) {
	return [...new Set(keys.map(crNameFromKey).filter(Boolean))];
}

/**
 * Change requests whose drafts may be deleted. `rows` is the server's answer
 * for exactly `names`: a row in a finished status, or no row at all (the
 * request was deleted). A failed lookup must pass `rows = null`, which deletes
 * nothing -- a draft is never dropped on a guess.
 */
export function finishedCrNames(names, rows) {
	if (!Array.isArray(rows)) return [];
	const status = new Map(rows.map((row) => [row.name, row.status]));
	return names.filter((name) => {
		if (!status.has(name)) return true;
		return FINISHED_STATUSES.has(status.get(name));
	});
}
