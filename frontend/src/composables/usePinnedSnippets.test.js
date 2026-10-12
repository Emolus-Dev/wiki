import assert from 'node:assert/strict';
import test from 'node:test';

await import('@vueuse/core');
globalThis.document = { cookie: 'user_id=alice@example.com' };
globalThis.localStorage = {
	store: new Map(),
	getItem(key) {
		return this.store.has(key) ? this.store.get(key) : null;
	},
	setItem(key, value) {
		this.store.set(key, String(value));
	},
	removeItem(key) {
		this.store.delete(key);
	},
};

const { SNIPPET_LIMIT, withSnippet, withoutSnippet } = await import(
	'./usePinnedSnippets.js'
);

test('a new snippet goes first and keeps its code verbatim', () => {
	const list = withSnippet(
		[],
		{ title: 'Restart', code: 'bench restart' },
		'a',
	);
	const next = withSnippet(
		list,
		{ title: 'Migrate', code: 'bench migrate' },
		'b',
	);
	assert.deepEqual(
		next.map((s) => s.id),
		['b', 'a'],
	);
	assert.equal(next[0].code, 'bench migrate');
});

test('trailing whitespace is trimmed but inner newlines survive', () => {
	const [snippet] = withSnippet([], { title: 't', code: 'a\n  b\n\n' }, 'a');
	assert.equal(snippet.code, 'a\n  b');
});

test('an empty body is refused and returns the same list', () => {
	const list = [];
	assert.equal(withSnippet(list, { title: 'x', code: '  \n ' }), list);
});

test('a missing title falls back to the first line of the code', () => {
	const [snippet] = withSnippet(
		[],
		{ code: '\nbench --site x migrate\nmore' },
		'a',
	);
	assert.equal(snippet.title, 'bench --site x migrate');
});

test('the list is capped, dropping the oldest', () => {
	let list = [];
	for (let i = 0; i < SNIPPET_LIMIT + 3; i++) {
		list = withSnippet(list, { title: `s${i}`, code: `c${i}` }, `id${i}`);
	}
	assert.equal(list.length, SNIPPET_LIMIT);
	assert.equal(list[0].id, `id${SNIPPET_LIMIT + 2}`);
	assert.ok(!list.some((s) => s.id === 'id0'));
});

test('removing drops only the matching snippet', () => {
	const list = [{ id: 'a' }, { id: 'b' }];
	assert.deepEqual(withoutSnippet(list, 'a'), [{ id: 'b' }]);
	assert.deepEqual(withoutSnippet(list, 'zzz'), list);
});
