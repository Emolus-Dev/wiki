import re

import frappe

from wiki.search_text import fold as _fold
from wiki.search_text import stem
from wiki.telemetry import capture

PAGE_SEARCH_LIMIT = 20

# Content search narrows in SQL on the longest word, then checks every word in
# Python (case- and accent-insensitive). The cap bounds how much page text one
# request reads; the oldest candidates are the ones dropped.
CONTENT_CANDIDATE_LIMIT = 100
CONTENT_MIN_QUERY = 3
SNIPPET_RADIUS = 80


@frappe.whitelist()
def search_pages(query: str) -> list[dict]:
	"""Find pages by URL across every space the user can read."""
	query = (query or "").strip()
	if not query:
		return []

	# Routes hyphenate words, so "getting started" still finds `getting-started`.
	# The slash skips the space's own segment, which every page in it shares.
	route = query.replace(" ", "-")
	pages = frappe.get_list(
		"Wiki Document",
		filters={
			"route": ("like", f"%/%{route}%"),
			"is_group": 0,
			"is_external_link": 0,
			"wiki_space": ("is", "set"),
		},
		fields=[
			"name",
			"title",
			"route",
			"is_published",
			"wiki_space",
			"wiki_space.space_name as space_name",
			"wiki_space.route as space_route",
		],
		order_by="`tabWiki Document`.modified desc",
		limit=PAGE_SEARCH_LIMIT,
	)
	capture("search_performed", interval="1d", surface="app", hits=bool(pages))
	return pages


@frappe.whitelist()
def search_content(query: str) -> list[dict]:
	"""Find pages by title and body text across every space the user can read.

	Complements `search_pages`, which matches URLs only. Drafts and unpublished
	pages are included: the editor works on them, and the reader's published-only
	index cannot find them. `get_list` applies the space permission conditions.
	"""
	words = _query_words(query)
	if not words or len(max(words, key=len)) < CONTENT_MIN_QUERY:
		return []

	anchor = max(words, key=len)
	candidates = frappe.get_list(
		"Wiki Document",
		or_filters=[["title", "like", f"%{anchor}%"], ["content", "like", f"%{anchor}%"]],
		filters={"is_group": 0, "is_external_link": 0, "wiki_space": ("is", "set")},
		fields=[
			"name",
			"title",
			"route",
			"content",
			"is_published",
			"wiki_space",
			"wiki_space.space_name as space_name",
		],
		order_by="`tabWiki Document`.modified desc",
		limit=CONTENT_CANDIDATE_LIMIT,
	)

	hits = []
	for page in candidates:
		title, content = page.title or "", page.content or ""
		haystack = _fold(f"{title} {content}")
		if not all(word in haystack for word in words):
			continue
		hits.append(
			{
				"name": page.name,
				"title": title,
				"route": page.route,
				"is_published": page.is_published,
				"wiki_space": page.wiki_space,
				"space_name": page.space_name,
				"in_title": all(word in _fold(title) for word in words),
				"snippet": _content_snippet(content, words),
			}
		)

	# Title matches first; each group keeps the most recently modified first.
	hits.sort(key=lambda hit: not hit["in_title"])
	hits = hits[:PAGE_SEARCH_LIMIT]
	capture("search_performed", interval="1d", surface="app-content", hits=bool(hits))
	return hits


def _query_words(query: str) -> list[str]:
	seen: set[str] = set()
	words = []
	# Stems, so "configurar" finds a page that says "configuración". A stem is a
	# prefix of every form it came from, so the SQL narrowing and the snippet
	# search (both substring matches) work on it unchanged.
	for word in (query or "").split():
		root = stem(word)
		if root not in seen:
			seen.add(root)
			words.append(root)
	return words[:6]


def _plain(markdown: str) -> str:
	text = re.sub(r"```[a-zA-Z0-9_+-]*", " ", markdown)
	text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
	text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
	text = re.sub(r"(?m)^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+", "", text)
	text = re.sub(r"[`*_]+", "", text)
	text = re.sub(r":::[a-z-]*", " ", text)
	return re.sub(r"\s+", " ", text).strip()


def _content_snippet(content: str, words: list[str]) -> str:
	"""A short run of plain text around the first word found in the body."""
	text = _plain(content)
	folded = _fold(text)
	# `_fold` keeps one character per character for NFC text, so offsets line up.
	if len(folded) != len(text):
		return text[: SNIPPET_RADIUS * 2].strip()

	positions = [at for at in (folded.find(word) for word in words) if at != -1]
	if not positions:
		return text[: SNIPPET_RADIUS * 2].strip()

	start = max(min(positions) - SNIPPET_RADIUS, 0)
	end = min(min(positions) + SNIPPET_RADIUS, len(text))
	snippet = text[start:end].strip()
	return f"{'…' if start else ''}{snippet}{'…' if end < len(text) else ''}"
