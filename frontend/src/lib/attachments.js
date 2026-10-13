// Which files a page offers for download. Mirrors wiki/wiki/attachments.py: an
// attachment is a link to one of this site's uploads, or a PDF embed. Images and
// video show inline, so they are not repeated as downloads.

const INLINE_MEDIA = new Set([
	'png',
	'jpg',
	'jpeg',
	'gif',
	'webp',
	'avif',
	'svg',
	'bmp',
	'mp4',
	'webm',
	'ogg',
	'mov',
	'avi',
	'mkv',
	'm4v',
]);

const KINDS = {
	pdf: 'red',
	doc: 'blue',
	docx: 'blue',
	odt: 'blue',
	rtf: 'blue',
	txt: 'blue',
	md: 'blue',
	xls: 'green',
	xlsx: 'green',
	ods: 'green',
	csv: 'green',
	zip: 'amber',
	gz: 'amber',
	tar: 'amber',
	'7z': 'amber',
	rar: 'amber',
};

const FILE_PREFIXES = ['/files/', '/private/files/'];

/** Walk a ProseMirror JSON doc and list its attachments, in order, once each. */
export function collectAttachments(doc) {
	const found = [];
	const seen = new Set();

	function add(href, label) {
		const url = fileUrl(href);
		if (!url || seen.has(url)) return;

		const filename = decodeURIComponent(url.split('/').pop());
		const extension = filename.includes('.')
			? filename.split('.').pop().toLowerCase()
			: '';
		if (INLINE_MEDIA.has(extension)) return;

		seen.add(url);
		found.push({
			url,
			name: (label || '').trim() || filename,
			filename,
			extension,
			kind: KINDS[extension] || 'gray',
		});
	}

	function visit(node) {
		if (!node) return;
		if (node.type === 'pdfBlock') add(node.attrs?.src, node.attrs?.filename);
		for (const mark of node.marks || []) {
			if (mark.type === 'link') add(mark.attrs?.href, node.text);
		}
		for (const child of node.content || []) visit(child);
	}

	visit(doc);
	return found;
}

/** A path on this site's own uploads, or null. */
export function fileUrl(href) {
	if (!href || /^[a-z][a-z0-9+.-]*:|^\/\//i.test(href)) return null;
	const path = href.split(/[?#]/)[0];
	return FILE_PREFIXES.some((prefix) => path.startsWith(prefix)) ? path : null;
}
