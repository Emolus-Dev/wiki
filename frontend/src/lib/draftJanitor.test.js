import assert from 'node:assert/strict';
import test from 'node:test';

import {
	crNameFromKey,
	draftCrNames,
	finishedCrNames,
} from './draftJanitor.js';

test('the change request is the first segment after the cr: prefix', () => {
	assert.equal(crNameFromKey('cr:abc123:tmp_9'), 'abc123');
	assert.equal(crNameFromKey('cr:abc123:doc:with:colons'), 'abc123');
	assert.equal(crNameFromKey('tree:user:space'), null);
	assert.equal(crNameFromKey(42), null);
	assert.equal(crNameFromKey('cr:'), null);
});

test('names are de-duplicated and tree snapshots ignored', () => {
	const keys = ['cr:a:1', 'cr:a:2', 'cr:b:1', 'tree:u:s'];
	assert.deepEqual(draftCrNames(keys), ['a', 'b']);
});

test('merged, rejected, archived and deleted requests are finished', () => {
	const rows = [
		{ name: 'a', status: 'Merged' },
		{ name: 'b', status: 'Rejected' },
		{ name: 'c', status: 'Archived' },
		{ name: 'd', status: 'Draft' },
		{ name: 'e', status: 'In Review' },
		{ name: 'f', status: 'Changes Requested' },
		{ name: 'g', status: 'Approved' },
	];
	assert.deepEqual(
		finishedCrNames(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'gone'], rows),
		['a', 'b', 'c', 'gone'],
	);
});

test('a failed lookup deletes nothing', () => {
	assert.deepEqual(finishedCrNames(['a', 'b'], null), []);
	assert.deepEqual(finishedCrNames(['a', 'b'], undefined), []);
});
