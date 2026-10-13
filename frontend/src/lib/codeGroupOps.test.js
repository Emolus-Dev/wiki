import assert from 'node:assert/strict';
import test from 'node:test';

import { Schema } from 'prosemirror-model';
import { EditorState } from 'prosemirror-state';
import { moveGroupTab } from './codeGroupOps.js';

const schema = new Schema({
	nodes: {
		doc: { content: 'block+' },
		paragraph: { group: 'block', content: 'text*' },
		codeGroup: { group: 'block', content: 'codeBlock+' },
		codeBlock: { content: 'text*', attrs: { label: { default: '' } } },
		text: {},
	},
});

function build(labels) {
	const blocks = labels.map((l) =>
		schema.nodes.codeBlock.create({ label: l }, schema.text(l.toUpperCase())),
	);
	return EditorState.create({
		schema,
		doc: schema.node('doc', null, [
			schema.node('paragraph', null, schema.text('before')),
			schema.nodes.codeGroup.create(null, blocks),
		]),
	});
}

const labelsOf = (tr) => {
	const group = tr.doc.child(1);
	const out = [];
	group.forEach((c) => out.push(c.attrs.label));
	return out;
};

const GROUP_POS = 8; // "before" paragraph: 6 chars + 2

test('moves a tab later and earlier', () => {
	let tr = build(['a', 'b', 'c']).tr;
	assert.ok(moveGroupTab(tr, GROUP_POS, 0, 1));
	assert.deepEqual(labelsOf(tr), ['b', 'a', 'c']);

	tr = build(['a', 'b', 'c']).tr;
	assert.ok(moveGroupTab(tr, GROUP_POS, 2, 0));
	assert.deepEqual(labelsOf(tr), ['c', 'a', 'b']);

	tr = build(['a', 'b', 'c']).tr;
	assert.ok(moveGroupTab(tr, GROUP_POS, 0, 2));
	assert.deepEqual(labelsOf(tr), ['b', 'c', 'a']);
});

test('keeps each tab\'s text with its label', () => {
	const tr = build(['a', 'b']).tr;
	moveGroupTab(tr, GROUP_POS, 1, 0);
	const first = tr.doc.child(1).child(0);
	assert.equal(first.attrs.label, 'b');
	assert.equal(first.textContent, 'B');
});

test('out of range or same index does nothing', () => {
	const tr = build(['a', 'b']).tr;
	assert.equal(moveGroupTab(tr, GROUP_POS, 0, 0), false);
	assert.equal(moveGroupTab(tr, GROUP_POS, 0, 5), false);
	assert.equal(moveGroupTab(tr, GROUP_POS, -1, 0), false);
	assert.equal(moveGroupTab(tr, 1, 0, 1), false);
});
