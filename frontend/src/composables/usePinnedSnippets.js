import { useStorage } from '@vueuse/core';
import { getCookieUser } from '../lib/cookieUser.js';

export const SNIPPET_LIMIT = 12;

// Per-user and per-browser, keyed by user for the same reason as recent pages:
// localStorage outlives a logout and a snippet can hold a credential-adjacent
// command. A shared snippet list would be a DocType; this is deliberately not.
const STORAGE_KEY = `wiki:pinned-snippets:${getCookieUser()}`;

const pinnedSnippets = useStorage(STORAGE_KEY, [], localStorage);

/** Newest first, capped, and refuses an empty body. Pure so it can be tested. */
export function withSnippet(list, { title, code } = {}, id = newId()) {
	const body = (code || '').replace(/\s+$/, '');
	if (!body.trim()) return list;
	const snippet = {
		id,
		title: (title || '').trim() || firstLine(body),
		code: body,
	};
	return [snippet, ...list].slice(0, SNIPPET_LIMIT);
}

export function withoutSnippet(list, id) {
	return list.filter((snippet) => snippet.id !== id);
}

function firstLine(code) {
	return code.trim().split('\n')[0].slice(0, 60);
}

function newId() {
	return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

export function usePinnedSnippets() {
	function addSnippet(input) {
		const next = withSnippet(pinnedSnippets.value, input);
		const added = next !== pinnedSnippets.value;
		pinnedSnippets.value = next;
		return added;
	}

	function removeSnippet(id) {
		pinnedSnippets.value = withoutSnippet(pinnedSnippets.value, id);
	}

	return { pinnedSnippets, addSnippet, removeSnippet };
}
