/**
 * Code group: consecutive code blocks shown as tabs.
 *
 * `WikiCodeBlock` is frappe-ui's code block plus a `label` (the tab title).
 * Markdown hooks live in code-group-markdown.js so they can be unit tested.
 */

import { Node } from '@tiptap/core';
import { VueNodeViewRenderer } from '@tiptap/vue-3';
import { CodeBlock } from 'frappe-ui/editor';
import CodeGroupView from './CodeGroupView.vue';
import {
	codeGroupMarkdownTokenizer,
	parseCodeBlockMarkdown,
	parseCodeGroupMarkdown,
	renderCodeBlockMarkdown,
	renderCodeGroupMarkdown,
} from './code-group-markdown.js';

export const WikiCodeBlock = CodeBlock.extend({
	addAttributes() {
		return {
			...this.parent?.(),
			label: { default: '', rendered: false },
		};
	},

	parseMarkdown: parseCodeBlockMarkdown,

	renderMarkdown: renderCodeBlockMarkdown,
});

export const CodeGroup = Node.create({
	name: 'codeGroup',

	group: 'block',

	content: 'codeBlock+',

	// Like a callout: a unit that Backspace at an edge cannot merge away.
	defining: true,

	isolating: true,

	draggable: true,

	parseHTML() {
		return [
			{ tag: 'div.wiki-code-group', contentElement: '.wiki-code-group__body' },
		];
	},

	renderHTML() {
		return [
			'div',
			{ class: 'wiki-code-group' },
			['div', { class: 'wiki-code-group__body' }, 0],
		];
	},

	addNodeView() {
		return VueNodeViewRenderer(CodeGroupView);
	},

	addCommands() {
		return {
			setCodeGroup:
				() =>
				({ commands, editor }) => {
					// `:::code-group` cannot hold a group, and a group inside a callout
					// would not survive the callout's own fence.
					if (editor.isActive(this.name)) return false;

					return commands.insertContent({
						type: this.name,
						content: [
							{ type: 'codeBlock', attrs: { language: 'bash' } },
							{ type: 'codeBlock', attrs: { language: 'json', label: '' } },
						],
					});
				},
		};
	},

	markdownTokenizer: codeGroupMarkdownTokenizer,

	parseMarkdown: parseCodeGroupMarkdown,

	renderMarkdown: renderCodeGroupMarkdown,
});
