import assert from 'node:assert/strict';
import test from 'node:test';
import { countDeletion } from './treeCounts.js';

const page = (extra = {}) => ({ is_group: 0, children: [], ...extra });
const group = (children, extra = {}) => ({ is_group: 1, children, ...extra });

test('a group with no children takes nothing with it', () => {
	assert.deepEqual(countDeletion(group([])), { pages: 0, groups: 0 });
});

test('pages and sub-groups are counted at every depth', () => {
	const tree = group([page(), group([page(), page(), group([page()])])]);
	assert.deepEqual(countDeletion(tree), { pages: 4, groups: 2 });
});

test('what the draft already deleted is not counted, nor what is under it', () => {
	const tree = group([page({ is_deleted: 1 }), group([page()], { is_deleted: 1 }), page()]);
	assert.deepEqual(countDeletion(tree), { pages: 1, groups: 0 });
});

test('a missing node counts as nothing', () => {
	assert.deepEqual(countDeletion(null), { pages: 0, groups: 0 });
});
