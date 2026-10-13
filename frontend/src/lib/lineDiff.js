// A line diff for comparing two versions of a page. Strips the shared head and
// tail first (most edits touch a small middle), then an LCS over what is left.

const MAX_CELLS = 4_000_000;

/**
 * Operations turning `before` into `after`: `{ type: 'same' | 'add' | 'del', text }`.
 * Returns null when the changed middle is too large to diff cheaply.
 */
export function diffLines(before, after) {
	const a = splitLines(before);
	const b = splitLines(after);

	let head = 0;
	while (head < a.length && head < b.length && a[head] === b[head]) head++;
	let tail = 0;
	while (
		tail < a.length - head &&
		tail < b.length - head &&
		a[a.length - 1 - tail] === b[b.length - 1 - tail]
	) {
		tail++;
	}

	const midA = a.slice(head, a.length - tail);
	const midB = b.slice(head, b.length - tail);
	if ((midA.length + 1) * (midB.length + 1) > MAX_CELLS) return null;

	return [
		...a.slice(0, head).map((text) => ({ type: 'same', text })),
		...lcsDiff(midA, midB),
		...a.slice(a.length - tail).map((text) => ({ type: 'same', text })),
	];
}

function splitLines(text) {
	return text ? text.replace(/\r\n/g, '\n').split('\n') : [];
}

function lcsDiff(a, b) {
	const rows = a.length + 1;
	const cols = b.length + 1;
	const table = new Uint32Array(rows * cols);
	for (let i = a.length - 1; i >= 0; i--) {
		for (let j = b.length - 1; j >= 0; j--) {
			table[i * cols + j] =
				a[i] === b[j]
					? table[(i + 1) * cols + j + 1] + 1
					: Math.max(table[(i + 1) * cols + j], table[i * cols + j + 1]);
		}
	}

	const ops = [];
	let i = 0;
	let j = 0;
	while (i < a.length && j < b.length) {
		if (a[i] === b[j]) {
			ops.push({ type: 'same', text: a[i] });
			i++;
			j++;
		} else if (table[(i + 1) * cols + j] >= table[i * cols + j + 1]) {
			ops.push({ type: 'del', text: a[i++] });
		} else {
			ops.push({ type: 'add', text: b[j++] });
		}
	}
	while (i < a.length) ops.push({ type: 'del', text: a[i++] });
	while (j < b.length) ops.push({ type: 'add', text: b[j++] });
	return ops;
}

/**
 * Collapse unchanged runs to `context` lines around each change, so a long page
 * shows its edits, not itself. Skipped runs become `{ type: 'gap', count }`.
 */
export function withContext(ops, context = 2) {
	const keep = new Array(ops.length).fill(false);
	ops.forEach((op, index) => {
		if (op.type === 'same') return;
		for (
			let near = Math.max(index - context, 0);
			near <= Math.min(index + context, ops.length - 1);
			near++
		) {
			keep[near] = true;
		}
	});

	const out = [];
	let skipped = 0;
	ops.forEach((op, index) => {
		if (keep[index]) {
			if (skipped) out.push({ type: 'gap', count: skipped });
			skipped = 0;
			out.push(op);
		} else {
			skipped++;
		}
	});
	if (skipped && out.length) out.push({ type: 'gap', count: skipped });
	return out;
}

export function diffStats(ops) {
	let added = 0;
	let removed = 0;
	for (const op of ops) {
		if (op.type === 'add') added++;
		else if (op.type === 'del') removed++;
	}
	return { added, removed };
}
