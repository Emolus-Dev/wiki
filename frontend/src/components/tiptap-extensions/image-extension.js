import { Node, mergeAttributes, nodeInputRule } from '@tiptap/core';
import { VueNodeViewRenderer } from '@tiptap/vue-3';
import ImageNodeView from './ImageNodeView.vue';
import { isVideoUrl } from './video-block.js';

// Markdown image regex: ![alt](src "title")
const inputRegex = /(?:^|\s)(!\[(.+|:?)]\((\S+)(?:(?:\s+)["'](\S+)["'])?\))$/;

/**
 * Custom Image extension with caption support
 *
 * Captions use the Stack Overflow pattern in markdown:
 *   ![alt text](image.jpg)
 *   *caption text*
 *
 * - alt: For accessibility (screen readers)
 * - caption: Visible caption text below the image
 */

/**
 * Custom marked tokenizer that matches image followed by caption on next line.
 * Pattern: ![alt](src "title")\n*caption*
 */
const imageCaptionTokenizer = {
	name: 'wikiImage',
	level: 'block',

	start(src) {
		return src.indexOf('![');
	},

	tokenize(src, tokens, lexer) {
		// Match: ![alt](src) or ![alt](src "title") optionally followed by \n*caption*
		const imagePattern = /^!\[([^\]]*)\]\(([^)"]+)(?:\s+"([^"]*)")?\)/;
		const captionPattern = /^\n\*([^*]+)\*/;
		// Metadata block: {width=320}, {align=center} or {width=320 align=center}
		// (order-independent, both keys optional inside the braces)
		const metaPattern = /^\n?\{([^}\n]*)\}/;

		const imageMatch = imagePattern.exec(src);
		if (!imageMatch) {
			return undefined;
		}

		const [imageRaw, alt, href, title] = imageMatch;
		if (isVideoUrl(href)) {
			return undefined;
		}
		let caption = null;
		let raw = imageRaw;
		let width = null;
		let align = null;

		// Check for metadata + caption on the following lines
		let remaining = src.slice(imageRaw.length);
		const metaMatch = metaPattern.exec(remaining);
		if (metaMatch) {
			const meta = metaMatch[1];
			const widthToken = /width=(\d+)/.exec(meta);
			const alignToken = /align=(left|center|right|full)/.exec(meta);
			if (widthToken) width = Number(widthToken[1]);
			if (alignToken) align = alignToken[1];
			// Only consume the metadata block if it actually carried known keys
			if (widthToken || alignToken) {
				raw += metaMatch[0];
				remaining = remaining.slice(metaMatch[0].length);
			}
		}

		const captionMatch = captionPattern.exec(remaining);
		if (captionMatch) {
			caption = captionMatch[1];
			raw += captionMatch[0];
		}

		return {
			type: 'wikiImage',
			raw,
			text: alt || '',
			href: href || '',
			title: title || null,
			width: width,
			align: align,
			caption: caption,
		};
	},
};

export const WikiImage = Node.create({
	name: 'image',

	group: 'block',

	draggable: true,

	addOptions() {
		return {
			inline: false,
			allowBase64: true,
			HTMLAttributes: {},
		};
	},

	addAttributes() {
		return {
			src: {
				default: null,
			},
			alt: {
				default: null,
			},
			title: {
				default: null,
			},
			caption: {
				default: null,
			},
			width: {
				default: null,
			},
			height: {
				default: null,
			},
			align: {
				default: null,
			},
		};
	},

	parseHTML() {
		return [
			{
				tag: 'img[src]',
				getAttrs: (dom) => ({
					src: dom.getAttribute('src'),
					alt: dom.getAttribute('alt'),
					title: dom.getAttribute('title'),
					width:
						dom.getAttribute('width') ||
						dom.style.width?.replace('px', '') ||
						null,
					height:
						dom.getAttribute('height') ||
						dom.style.height?.replace('px', '') ||
						null,
					align:
						dom.getAttribute('data-align') ||
						dom.closest?.('[data-align]')?.getAttribute('data-align') ||
						null,
				}),
			},
		];
	},

	renderHTML({ HTMLAttributes }) {
		const width = HTMLAttributes.width ? String(HTMLAttributes.width) : null;
		const height = HTMLAttributes.height ? String(HTMLAttributes.height) : null;
		const align = HTMLAttributes.align || null;
		return [
			'img',
			mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, {
				width: width || undefined,
				height: height || undefined,
				align: undefined,
				'data-align': align || undefined,
			}),
		];
	},

	// Custom tokenizer for marked.js to capture image + caption pattern
	markdownTokenizer: imageCaptionTokenizer,

	// Token name must match the tokenizer's type
	markdownTokenName: 'wikiImage',

	// Parse markdown image with optional caption
	parseMarkdown: (token, helpers) => {
		return helpers.createNode('image', {
			src: token.href,
			title: token.title,
			alt: token.text,
			caption: token.caption || null,
			width: token.width || null,
			align: token.align || null,
		});
	},

	// Render to markdown using Stack Overflow caption pattern:
	// ![alt](src "title")
	// *caption*
	renderMarkdown: (node) => {
		const src = node.attrs?.src ?? '';
		const alt = node.attrs?.alt ?? '';
		const title = node.attrs?.title ?? '';
		const caption = node.attrs?.caption ?? '';
		const width = node.attrs?.width ?? null;
		const align = node.attrs?.align ?? null;

		let md = title ? `![${alt}](${src} "${title}")` : `![${alt}](${src})`;

		// Serialize width/align into a single metadata block: {width=320 align=center}
		const metaParts = [];
		if (width) metaParts.push(`width=${width}`);
		if (align && align !== 'left') metaParts.push(`align=${align}`);
		if (metaParts.length) {
			md += `\n{${metaParts.join(' ')}}`;
		}

		// Add caption on next line (no blank line) if present
		if (caption) {
			md += `\n*${caption}*`;
		}

		return md;
	},

	addNodeView() {
		return VueNodeViewRenderer(ImageNodeView);
	},

	addCommands() {
		return {
			setImage:
				(options) =>
				({ commands }) => {
					return commands.insertContent({
						type: this.name,
						attrs: options,
					});
				},
		};
	},

	addInputRules() {
		return [
			nodeInputRule({
				find: inputRegex,
				type: this.type,
				getAttributes: (match) => {
					const [, , alt, src, title] = match;
					return { src, alt, title };
				},
			}),
		];
	},
});

export default WikiImage;
