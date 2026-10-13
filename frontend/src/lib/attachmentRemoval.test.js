import assert from 'node:assert/strict';
import test from 'node:test';

import { Schema } from 'prosemirror-model';
import { EditorState } from 'prosemirror-state';
import { removeAttachment } from './attachmentRemoval.js';

const schema = new Schema({
	nodes: {
		doc: { content: 'block+' },
		paragraph: { group: 'block', content: 'inline*' },
		pdfBlock: { group: 'block', atom: true, attrs: { src: {} } },
		text: { group: 'inline' },
	},
	marks: { link: { attrs: { href: {} } } },
});

const link = (text, href) =>
	schema.text(text, [schema.marks.link.create({ href })]);
const para = (...c) => schema.nodes.paragraph.create(null, c);
const state = (...blocks) =>
	EditorState.create({ schema, doc: schema.node('doc', null, blocks) });

function run(st, url) {
	const tr = st.tr;
	const changed = removeAttachment(tr, url);
	return { changed, json: tr.doc.toJSON().content };
}

test('a paragraph that is only the link is removed', () => {
	const st = state(para(schema.text('keep')), para(link('manual', '/files/a.pdf')));
	const { changed, json } = run(st, '/files/a.pdf');
	assert.equal(changed, 1);
	assert.equal(json.length, 1);
	assert.equal(json[0].content[0].text, 'keep');
});

test('a link inside a sentence keeps its words', () => {
	const st = state(
		para(schema.text('see '), link('the manual', '/files/a.pdf'), schema.text(' now')),
	);
	const { json } = run(st, '/files/a.pdf');
	assert.equal(json.length, 1);
	assert.ok(json[0].content.every((n) => !n.marks));
	assert.equal(json[0].content.map((n) => n.text).join(''), 'see the manual now');
});

test('a PDF embed is removed', () => {
	const st = state(para(schema.text('x')), schema.nodes.pdfBlock.create({ src: '/files/a.pdf' }));
	const { changed, json } = run(st, '/files/a.pdf');
	assert.equal(changed, 1);
	assert.equal(json.length, 1);
});

test('every occurrence goes, other files stay', () => {
	const st = state(
		para(link('one', '/files/a.pdf')),
		para(link('other', '/files/b.pdf')),
		para(link('two', '/files/a.pdf')),
	);
	const { changed, json } = run(st, '/files/a.pdf');
	assert.equal(changed, 2);
	assert.equal(json.length, 1);
	assert.equal(json[0].content[0].text, 'other');
});

test('an unknown file changes nothing', () => {
	const st = state(para(link('x', '/files/a.pdf')));
	assert.equal(run(st, '/files/zzz.pdf').changed, 0);
});
