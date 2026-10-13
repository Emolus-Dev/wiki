import assert from 'node:assert/strict';
import test from 'node:test';

import { diffLines, diffStats, withContext } from './lineDiff.js';

const summary = (ops) => ops.map((op) => `${op.type[0]}:${op.text}`);

test('identical text is all unchanged', () => {
	const ops = diffLines('a\nb\nc', 'a\nb\nc');
	assert.deepEqual(summary(ops), ['s:a', 's:b', 's:c']);
	assert.deepEqual(diffStats(ops), { added: 0, removed: 0 });
});

test('a replaced line is a removal and an addition', () => {
	const ops = diffLines('a\nb\nc', 'a\nX\nc');
	assert.deepEqual(summary(ops), ['s:a', 'd:b', 'a:X', 's:c']);
	assert.deepEqual(diffStats(ops), { added: 1, removed: 1 });
});

test('inserted and deleted runs are found', () => {
	assert.deepEqual(summary(diffLines('a\nd', 'a\nb\nc\nd')), ['s:a', 'a:b', 'a:c', 's:d']);
	assert.deepEqual(summary(diffLines('a\nb\nc\nd', 'a\nd')), ['s:a', 'd:b', 'd:c', 's:d']);
});

test('moved text shows as removed and added', () => {
	const ops = diffLines('x\nmid\ny', 'y\nmid\nx');
	const { added, removed } = diffStats(ops);
	assert.ok(added > 0 && removed > 0);
});

test('empty sides', () => {
	assert.deepEqual(summary(diffLines('', 'a')), ['a:a']);
	assert.deepEqual(summary(diffLines('a', '')), ['d:a']);
	assert.deepEqual(diffLines('', ''), []);
});

test('line endings do not count as changes', () => {
	assert.deepEqual(diffStats(diffLines('a\r\nb', 'a\nb')), { added: 0, removed: 0 });
});

test('reapplying the ops reproduces the new text', () => {
	const before = Array.from({ length: 60 }, (_, i) => `line ${i}`).join('\n');
	const after = before.replace('line 10', 'ten').replace('line 40\n', '') + '\nnew tail';
	const ops = diffLines(before, after);
	assert.equal(
		ops.filter((op) => op.type !== 'del').map((op) => op.text).join('\n'),
		after,
	);
	assert.equal(
		ops.filter((op) => op.type !== 'add').map((op) => op.text).join('\n'),
		before,
	);
});

test('a huge changed middle is refused instead of hanging', () => {
	const a = Array.from({ length: 3000 }, (_, i) => `a${i}`).join('\n');
	const b = Array.from({ length: 3000 }, (_, i) => `b${i}`).join('\n');
	assert.equal(diffLines(a, b), null);
});

test('context keeps changes and a few neighbours, and counts what it hides', () => {
	const lines = Array.from({ length: 20 }, (_, i) => `l${i}`);
	const ops = diffLines(lines.join('\n'), [...lines.slice(0, 10), 'CHANGED', ...lines.slice(11)].join('\n'));
	const shown = withContext(ops, 2);
	assert.deepEqual(
		shown.map((op) => (op.type === 'gap' ? `gap${op.count}` : `${op.type[0]}:${op.text}`)),
		['gap8', 's:l8', 's:l9', 'd:l10', 'a:CHANGED', 's:l11', 's:l12', 'gap7'],
	);
});

test('no changes means nothing to show', () => {
	assert.deepEqual(withContext(diffLines('a\nb', 'a\nb')), []);
});
