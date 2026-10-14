/**
 * An uploaded file's url as it should be written into markdown.
 *
 * Frappe keeps the name as uploaded, so `/files/Manual de usuario.pdf` is a
 * normal url, but a space ends a link destination in markdown: the link would
 * save as plain text and never reach the published page or its attachments list.
 */
export function markdownSafeUrl(url) {
	return typeof url === 'string' ? url.replace(/ /g, '%20') : url;
}
