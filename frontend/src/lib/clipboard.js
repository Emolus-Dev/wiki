/**
 * Copy text to the clipboard; true when it worked.
 *
 * `navigator.clipboard` only exists on a secure origin (HTTPS or localhost) and
 * can be refused by a permissions policy, so a plain `await writeText()` fails
 * silently on, for example, an intranet wiki served over HTTP. The fallback is a
 * hidden textarea and `execCommand('copy')`, which works everywhere a click does.
 */
export async function copyText(text) {
	try {
		if (navigator.clipboard?.writeText) {
			await navigator.clipboard.writeText(text);
			return true;
		}
	} catch {
		// Fall through to the textarea route.
	}
	return copyWithSelection(text);
}

function copyWithSelection(text) {
	const area = document.createElement('textarea');
	area.value = text;
	area.setAttribute('readonly', '');
	area.style.position = 'fixed';
	area.style.top = '0';
	area.style.opacity = '0';
	const previous = document.activeElement;
	document.body.appendChild(area);
	area.select();
	area.setSelectionRange(0, text.length);
	let copied = false;
	try {
		copied = document.execCommand('copy');
	} catch {
		copied = false;
	}
	document.body.removeChild(area);
	previous?.focus?.();
	return copied;
}
