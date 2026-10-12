import assert from 'node:assert/strict';
import test from 'node:test';

const store = new Map();
globalThis.localStorage = {
	getItem: (k) => (store.has(k) ? store.get(k) : null),
	setItem: (k, v) => store.set(k, String(v)),
};
const { readTrace, timed, timedAsync, trace } = await import(
	'./freezeTrace.js'
);

test('trace appends entries and keeps only the latest 80', () => {
	for (let i = 0; i < 100; i++) trace(`step-${i}`);
	const log = readTrace();
	assert.equal(log.length, 80);
	assert.equal(log.at(-1).e, 'step-99');
	assert.equal(log[0].e, 'step-20');
});

test('timed logs a start before running and an end after, returning the result', () => {
	store.clear();
	let seenAtRun;
	const result = timed('work', () => {
		seenAtRun = readTrace().map((entry) => entry.e);
		return 42;
	});
	assert.equal(result, 42);
	assert.deepEqual(seenAtRun, ['work:start']);
	assert.deepEqual(
		readTrace().map((entry) => entry.e),
		['work:start', 'work:end'],
	);
});

test('a step that never finishes leaves its start as the last entry', () => {
	store.clear();
	trace('other:end');
	trace('hang:start');
	assert.equal(readTrace().at(-1).e, 'hang:start');
});

test('timed still logs the end when the step throws', () => {
	store.clear();
	assert.throws(() =>
		timed('boom', () => {
			throw new Error('x');
		}),
	);
	assert.deepEqual(
		readTrace().map((entry) => entry.e),
		['boom:start', 'boom:end'],
	);
});

test('timedAsync logs the end when the promise settles', async () => {
	store.clear();
	await timedAsync('later', async () => 1);
	assert.deepEqual(
		readTrace().map((entry) => entry.e),
		['later:start', 'later:end'],
	);
});

test('tracing never throws without localStorage', async () => {
	delete globalThis.localStorage;
	assert.doesNotThrow(() => trace('x'));
	assert.deepEqual(readTrace(), []);
});

test('fingerprint tells different strings of the same length apart', async () => {
	const { fingerprint } = await import('./freezeTrace.js');
	assert.notEqual(fingerprint('- a\n- b'), fingerprint('* a\n* b'));
	assert.equal(fingerprint('same'), fingerprint('same'));
	assert.match(fingerprint('abc'), /^3:/);
});

test('firstDifference points at the first changed character', async () => {
	const { firstDifference } = await import('./freezeTrace.js');
	assert.equal(firstDifference('abc', 'abc'), null);
	const diff = firstDifference('hello world', 'hello there', 3);
	assert.equal(diff.at, 6);
	assert.deepEqual(diff.lengths, [11, 11]);
	assert.equal(diff.a, 'lo wor');
	assert.equal(diff.b, 'lo the');
	assert.equal(firstDifference('abc', 'abcd').at, 3);
});

test('a burst limiter lets a few calls through, then refuses until the window passes', async () => {
	const { createBurstLimiter } = await import('./freezeTrace.js');
	let time = 1000;
	const allow = createBurstLimiter({ windowMs: 2000, max: 3, now: () => time });
	assert.deepEqual(
		[allow(), allow(), allow(), allow(), allow()],
		[true, true, true, false, false],
	);
	time += 2500;
	assert.equal(allow(), true);
});
