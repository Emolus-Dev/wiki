/**
 * Markdown for code blocks with a label, and for code groups.
 *
 * Kept free of node view imports so `node --test` can load it, like
 * callout-markdown.js.
 *
 *   :::code-group
 *   ```bash
 *   bench restart
 *   ```
 *   ```json site_config.json
 *   {}
 *   ```
 *   :::
 *
 * Words after the language on a fence are the block's label, shown as its tab
 * title. The reader (wiki/wiki/markdown.py) reads the same syntax.
 */

import { startInParagraph } from './markdown-start.js';

/** `json site_config.json` -> language `json`, label `site_config.json`. */
export function splitFenceInfo(info) {
	const text = (info || '').trim();
	const gap = text.search(/\s/);
	if (gap === -1) return { language: text, label: '' };
	return { language: text.slice(0, gap), label: text.slice(gap).trim() };
}

// TipTap's own code block hooks, plus the label. Everything else about the
// block is unchanged, so a fence with no label round-trips as it always did.
export function parseCodeBlockMarkdown(token, helpers) {
	if (
		token.raw?.startsWith('```') === false &&
		token.raw?.startsWith('~~~') === false &&
		token.codeBlockStyle !== 'indented'
	) {
		return [];
	}
	const { language, label } = splitFenceInfo(token.lang);
	return helpers.createNode(
		'codeBlock',
		{ language: language || null, label },
		token.text ? [helpers.createTextNode(token.text)] : [],
	);
}

export function renderCodeBlockMarkdown(node, h) {
	const label = node.attrs?.label || '';
	// A label needs a language word in front of it; `text` is highlight.js's
	// "no highlighting".
	const language = node.attrs?.language || (label ? 'text' : '');
	const info = label ? `${language} ${label}` : language;

	if (!node.content) return `\`\`\`${info}\n\n\`\`\``;
	return [`\`\`\`${info}`, h.renderChildren(node.content), '```'].join('\n');
}

export const codeGroupMarkdownTokenizer = {
	name: 'codeGroup',
	level: 'block',

	start(src) {
		return startInParagraph(src, (text) => text.indexOf(':::code-group'));
	},

	tokenize(src, _tokens, lexer) {
		const match = /^:::code-group[ \t]*\n([\s\S]*?)\n:::[ \t]*(?:\n+|$)/.exec(
			src,
		);
		if (!match) return undefined;

		const body = (match[1] || '').trim();
		return {
			type: 'codeGroup',
			raw: match[0],
			text: body,
			tokens: lexer ? lexer.blockTokens(body) : [],
		};
	},
};

export function parseCodeGroupMarkdown(token, h) {
	// Only fences make a tab; anything else between them has no place in a group.
	const blocks = h
		.parseChildren(token.tokens || [])
		.filter((node) => node.type === 'codeBlock');

	return {
		type: 'codeGroup',
		content: blocks.length ? blocks : [{ type: 'codeBlock' }],
	};
}

// No trailing separator, for the reason callout-markdown.js gives.
export function renderCodeGroupMarkdown(node, h) {
	const body = h.renderChildren(node.content || [], '\n\n').trim();
	return `:::code-group\n${body}\n:::`;
}
