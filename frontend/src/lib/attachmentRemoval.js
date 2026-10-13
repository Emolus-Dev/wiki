import { fileUrl } from './attachments.js';

/**
 * Take a file out of the document: a PDF embed goes; a paragraph holding only
 * links to it goes; a link inside running text keeps its words and loses the
 * link. Edits are applied back to front so earlier positions stay valid.
 * Returns the number of places changed.
 */
export function removeAttachment(tr, url) {
	const edits = [];
	const { doc } = tr;

	doc.descendants((node, pos) => {
		if (node.type.name === 'pdfBlock') {
			if (fileUrl(node.attrs?.src) === url) {
				edits.push({ kind: 'delete', from: pos, to: pos + node.nodeSize });
			}
			return false;
		}
		if (!node.isTextblock) return true;

		const links = [];
		let onlyThisFile = node.childCount > 0;
		node.forEach((child, offset) => {
			const mark = child.marks.find(
				(m) => m.type.name === 'link' && fileUrl(m.attrs.href) === url,
			);
			if (mark) {
				links.push({
					mark,
					from: pos + 1 + offset,
					to: pos + 1 + offset + child.nodeSize,
				});
			} else if (!(child.isText && !child.text.trim())) {
				onlyThisFile = false;
			}
		});
		if (!links.length) return false;

		if (onlyThisFile && node.type.name === 'paragraph') {
			edits.push({ kind: 'delete', from: pos, to: pos + node.nodeSize });
		} else {
			for (const link of links) edits.push({ kind: 'unlink', ...link });
		}
		return false;
	});

	for (const edit of edits.sort((a, b) => b.from - a.from)) {
		if (edit.kind === 'delete') tr.delete(edit.from, edit.to);
		else tr.removeMark(edit.from, edit.to, edit.mark);
	}
	return edits.length;
}
