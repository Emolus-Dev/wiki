import assert from 'node:assert/strict';
import test from 'node:test';

import { collectAttachments } from './attachments.js';

const link = (text, href) => ({
	type: 'text',
	text,
	marks: [{ type: 'link', attrs: { href } }],
});
const doc = (...blocks) => ({ type: 'doc', content: blocks });
const para = (...content) => ({ type: 'paragraph', content });

test('lists links to uploaded files in order', () => {
	const files = collectAttachments(
		doc(
			para(link('the manual', '/files/manual.pdf')),
			para(link('data', '/files/data%20set.json')),
		),
	);
	assert.deepEqual(
		files.map((f) => [f.name, f.filename, f.extension, f.kind]),
		[
			['the manual', 'manual.pdf', 'pdf', 'red'],
			['data', 'data set.json', 'json', 'gray'],
		],
	);
});

test('a PDF embed counts, images and video do not', () => {
	const files = collectAttachments(
		doc(
			{
				type: 'pdfBlock',
				attrs: { src: '/files/guide.pdf', filename: 'guide.pdf' },
			},
			para(link('shot', '/files/shot.png')),
			para(link('clip', '/files/clip.mp4')),
		),
	);
	assert.deepEqual(
		files.map((f) => f.filename),
		['guide.pdf'],
	);
});

test('external links are ignored and a file is listed once', () => {
	const files = collectAttachments(
		doc(
			para(link('other', 'https://example.com/files/a.pdf')),
			para(link('a', '/files/a.zip'), link('again', '/files/a.zip?x=1')),
			para(link('private', '/private/files/p.xlsx')),
		),
	);
	assert.deepEqual(
		files.map((f) => f.url),
		['/files/a.zip', '/private/files/p.xlsx'],
	);
});

test('a link with no text falls back to the file name', () => {
	assert.equal(
		collectAttachments(doc(para(link('', '/files/notes.txt'))))[0].name,
		'notes.txt',
	);
});
