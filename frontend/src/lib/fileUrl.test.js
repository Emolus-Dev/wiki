import assert from 'node:assert/strict';
import test from 'node:test';

import { markdownSafeUrl } from './fileUrl.js';

test('spaces become %20 and nothing else changes', () => {
	assert.equal(
		markdownSafeUrl('/files/Manual de usuario (v2).pdf'),
		'/files/Manual%20de%20usuario%20(v2).pdf',
	);
});

test('an already safe url is untouched', () => {
	assert.equal(markdownSafeUrl('/files/a%20b.pdf'), '/files/a%20b.pdf');
});

test('non-strings pass through', () => {
	assert.equal(markdownSafeUrl(undefined), undefined);
});
