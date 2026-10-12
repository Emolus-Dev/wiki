import assert from 'node:assert/strict';
import test from 'node:test';

import { Node } from '@tiptap/core';
import { CodeBlock } from '@tiptap/extension-code-block';
import { MarkdownManager } from '@tiptap/markdown';

import {
	codeGroupMarkdownTokenizer,
	parseCodeBlockMarkdown,
	parseCodeGroupMarkdown,
	renderCodeBlockMarkdown,
	renderCodeGroupMarkdown,
	splitFenceInfo,
} from './code-group-markdown.js';
import { PreserveBlankLines } from './preserve-blank-lines.js';
import { wikiStarterKit } from './wiki-starterkit.js';

// Schema-only stand-ins: the real nodes pull in .vue node views that
// `node --test` cannot load. They carry the real markdown hooks.
const LabelledCodeBlock = CodeBlock.extend({
	addAttributes() {
		return { ...this.parent?.(), label: { default: '' } };
	},
	parseMarkdown: parseCodeBlockMarkdown,
	renderMarkdown: renderCodeBlockMarkdown,
});

const CodeGroupSchemaOnly = Node.create({
	name: 'codeGroup',
	group: 'block',
	content: 'codeBlock+',
	defining: true,
	isolating: true,
	renderHTML() {
		return ['div', {}, 0];
	},
	markdownTokenizer: codeGroupMarkdownTokenizer,
	parseMarkdown: parseCodeGroupMarkdown,
	renderMarkdown: renderCodeGroupMarkdown,
});

function buildManager() {
	const starterKit = wikiStarterKit();
	const baseExtensions = starterKit.config.addExtensions.call({
		options: starterKit.options,
		name: 'starterKit',
	});
	return new MarkdownManager({
		extensions: [
			...baseExtensions,
			LabelledCodeBlock,
			PreserveBlankLines,
			CodeGroupSchemaOnly,
		],
		markedOptions: { breaks: true },
	});
}

function roundTrip(manager, source, passes = 3) {
	const outputs = [];
	let current = source;
	for (let i = 0; i < passes; i++) {
		current = manager.serialize(manager.parse(current));
		outputs.push(current);
	}
	return outputs;
}

const CASES = {
	'a two tab group':
		':::code-group\n```bash\nbench restart\n```\n\n```json site_config.json\n{}\n```\n:::',
	'a group between paragraphs':
		'before\n\n:::code-group\n```bash\na\n```\n\n```python\nb\n```\n:::\n\nafter',
	'a labelled fence on its own': '```json site_config.json\n{}\n```',
	'a plain fence': '```js\nconst a = 1;\n```',
};

for (const [label, source] of Object.entries(CASES)) {
	test(`${label} round-trips to a fixed point`, () => {
		const outputs = roundTrip(buildManager(), source);
		assert.deepEqual(
			outputs,
			Array(outputs.length).fill(outputs[0]),
			`markdown kept changing: ${JSON.stringify(outputs)}`,
		);
	});
}

test('splitFenceInfo separates the language from the label', () => {
	assert.deepEqual(splitFenceInfo('json site_config.json'), {
		language: 'json',
		label: 'site_config.json',
	});
	assert.deepEqual(splitFenceInfo('bash'), { language: 'bash', label: '' });
	assert.deepEqual(splitFenceInfo(undefined), { language: '', label: '' });
	assert.deepEqual(splitFenceInfo('js  two words '), {
		language: 'js',
		label: 'two words',
	});
});

test('a group parses into code blocks that keep language and label', () => {
	const group = buildManager().parse(
		':::code-group\n```bash\na\n```\n\n```json site_config.json\n{}\n```\n:::',
	).content[0];

	assert.equal(group.type, 'codeGroup');
	assert.deepEqual(
		group.content.map((block) => [
			block.type,
			block.attrs.language,
			block.attrs.label,
		]),
		[
			['codeBlock', 'bash', ''],
			['codeBlock', 'json', 'site_config.json'],
		],
	);
});

test('a label survives the round-trip and the fence keeps its language first', () => {
	const manager = buildManager();
	const output = manager.serialize(
		manager.parse(':::code-group\n```json site_config.json\n{}\n```\n:::'),
	);
	assert.match(output, /```json site_config\.json\n/);
});

test('a label with no language is written after `text`', () => {
	const rendered = renderCodeBlockMarkdown(
		{ attrs: { language: null, label: 'notes' }, content: [{}] },
		{ renderChildren: () => 'x' },
	);
	assert.match(rendered, /^```text notes\n/);
});

test('an unlabelled fence is written exactly as before', () => {
	const manager = buildManager();
	assert.equal(
		manager.serialize(manager.parse('```js\nconst a = 1;\n```')).trim(),
		'```js\nconst a = 1;\n```',
	);
});

test('an empty group still parses to a body that codeBlock+ accepts', () => {
	const group = buildManager().parse(':::code-group\n\n:::').content[0];
	assert.deepEqual(group.content, [{ type: 'codeBlock' }]);
});

test('renderMarkdown leaves the block separator to the serializer', () => {
	const rendered = renderCodeGroupMarkdown(
		{ content: [{}] },
		{ renderChildren: () => '```bash\na\n```' },
	);
	assert.equal(rendered, ':::code-group\n```bash\na\n```\n:::');
});
