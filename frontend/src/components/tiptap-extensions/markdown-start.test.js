import assert from 'node:assert/strict';
import test from 'node:test';

import { OrderedList } from '@tiptap/extension-list';
import { MarkdownManager } from '@tiptap/markdown';

import { boundedListTokenize, startInParagraph } from './markdown-start.js';
import { PreserveBlankLines } from './preserve-blank-lines.js';
import { wikiStarterKit } from './wiki-starterkit.js';

test('startInParagraph only looks as far as the next blank line', () => {
	const find = (text) => text.indexOf('::');
	assert.equal(startInParagraph('a\nb ::x\n\nc', find), 4);
	assert.equal(startInParagraph('a\nb\n\nc ::x', find), -1);
	assert.equal(startInParagraph('no blank ::', find), 9);
});

// The unwrapped tokenizer, kept to prove the bounded one returns the same token.
const original = OrderedList.config.markdownTokenizer.tokenize.original;

function ordered(items, { nested = false, tail = '' } = {}) {
	let out = '';
	for (let i = 1; i <= items; i++) {
		out += `${i}. item ${i} with some words\n`;
		if (nested && i % 3 === 0) out += `   - nested ${i}\n`;
	}
	return out + tail;
}

const lexer = {
	inlineTokens: (text) => [{ type: 'text', raw: text, text }],
	blockTokens: (text) => [{ type: 'paragraph', raw: text, text, tokens: [] }],
};

for (const [name, src] of Object.entries({
	'a short list': ordered(3, { tail: '\nafter\n' }),
	'a list longer than the first window': ordered(400, {
		tail: '\nafter para\n',
	}),
	'a nested list across windows': ordered(600, {
		nested: true,
		tail: '\n# H\n',
	}),
	'a list that ends the document': ordered(500),
	'a paragraph that is not a list': 'Just words, 1. not at the start\n\nmore',
	'a line like (216) 555-1234': '(216) 555-1234 call me\n\n1. real item\n',
})) {
	test(`bounded tokenizer matches the original for ${name}`, () => {
		const bounded = boundedListTokenize(original);
		const a = original(src, [], lexer);
		const b = bounded(src, [], lexer);
		assert.equal(JSON.stringify(b), JSON.stringify(a));
	});
}

test('a long page parses to the same document either way', () => {
	let md = '';
	for (let i = 0; i < 40; i++) {
		md += `## S${i}\n\n${ordered(5)}\n- bullet\n\n`;
	}
	const sk = wikiStarterKit();
	const extensions = [
		...sk.config.addExtensions.call({
			options: sk.options,
			name: 'starterKit',
		}),
		PreserveBlankLines,
	];
	const bounded = new MarkdownManager({ extensions }).parse(md);

	OrderedList.config.markdownTokenizer.tokenize = original;
	try {
		const plain = new MarkdownManager({ extensions }).parse(md);
		assert.equal(JSON.stringify(bounded), JSON.stringify(plain));
	} finally {
		OrderedList.config.markdownTokenizer.tokenize =
			boundedListTokenize(original);
	}
});

test('parsing a very long page does not scale with its square', () => {
	// ~380 KB parsed in 13 s before the tokenizers were bounded, 0.2 s after.
	// The limit is loose enough for a slow machine and far below the old time.
	let md = '';
	for (let i = 0; i < 960; i++) {
		md += `## S${i}\n\n- **Dias:** lunes \`code_${i}\`, tambien se saltan.\n\n1. \`a.search\` por **dato** (no ID).\n2. Si existe y \`ok: false\`.\n\n> Ejemplos adicionales \`ERROR\`.\n\n---\n\n`;
	}
	const sk = wikiStarterKit();
	const manager = new MarkdownManager({
		extensions: [
			...sk.config.addExtensions.call({
				options: sk.options,
				name: 'starterKit',
			}),
			PreserveBlankLines,
		],
	});

	const started = performance.now();
	manager.parse(md);
	assert.ok(
		performance.now() - started < 4000,
		'parsing a 380 KB page took over 4 s',
	);
});
