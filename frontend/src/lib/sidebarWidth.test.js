import assert from 'node:assert/strict';
import test from 'node:test';
import { clampSidebarWidth } from './sidebarWidth.js';

test('keeps a width inside the limits', () => {
	assert.equal(clampSidebarWidth(320, 1600), 320);
});

test('raises a narrow width to the minimum', () => {
	assert.equal(clampSidebarWidth(100, 1600), 240);
});

test('lowers a wide width to the maximum', () => {
	assert.equal(clampSidebarWidth(900, 2400), 640);
});

test('never takes more than half of the window', () => {
	assert.equal(clampSidebarWidth(600, 800), 400);
});

test('a window too small for half still allows the minimum', () => {
	assert.equal(clampSidebarWidth(500, 300), 240);
});

test('garbage falls back to the minimum', () => {
	assert.equal(clampSidebarWidth(undefined, 1600), 240);
	assert.equal(clampSidebarWidth('abc', 1600), 240);
});
