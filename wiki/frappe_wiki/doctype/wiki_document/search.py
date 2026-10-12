import re

import frappe

from wiki.telemetry import capture

# FTS wraps the match in these. Everything else in a snippet is document text.
_MARK_OPEN = "\ue000"
_MARK_CLOSE = "\ue001"

# When the whole query finds little, each word is searched on its own and the
# hits are merged (see _widen_hits). Bounded so a long query stays cheap.
_WIDEN_BELOW = 5
_MAX_TOKENS = 5
_MIN_TOKEN_LENGTH = 2
_MAX_WIDENED_RESULTS = 20


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def search(query: str, space: str | None = None) -> dict:
	"""
	Search wiki documents with space-scoped filtering.

	Args:
	    query: Search query string
	    space: Wiki space (root group) name to scope search

	Returns:
	    Search results with title, content snippets, and scores
	"""
	from wiki.frappe_wiki.doctype.wiki_document.wiki_sqlite_search import WikiSQLiteSearch

	if not query or not query.strip():
		return {"results": [], "total": 0}

	search_engine = WikiSQLiteSearch()
	filters = {"space": space} if space else {}

	result = search_engine.search(query, filters=filters)

	raw_hits = _widen_hits(search_engine, query, filters, result["results"])
	hits = _filter_hits_by_space_visibility(raw_hits)

	capture("search_performed", interval="1d", surface="reader", hits=bool(hits))

	return {
		"results": [
			{
				"name": r["name"],
				"title": _clean_snippet(r["title"]),
				"route": r.get("route", ""),
				"content": _clean_snippet(r["content"]),
				"score": r["score"],
			}
			for r in hits
		],
		"total": len(hits),
	}


def _query_tokens(query: str) -> list[str]:
	seen: set[str] = set()
	tokens = []
	for token in query.split():
		key = token.casefold()
		if len(token) < _MIN_TOKEN_LENGTH or key in seen:
			continue
		seen.add(key)
		tokens.append(token)
	return tokens[:_MAX_TOKENS]


def _merge_token_hits(full_hits: list[dict], per_token_hits: list[list[dict]]) -> list[dict]:
	"""Merge hits for the whole query with hits for each of its words.

	A page that matched the whole query counts as matching every word. Pages
	matching more words come first; ties keep the order the engine returned
	them in, so its own ranking still decides within a group.
	"""
	entries: dict[str, list] = {}  # name -> [hit, words matched, first-seen order]

	for hit in full_hits:
		entries.setdefault(hit["name"], [hit, len(per_token_hits), len(entries)])

	for token_hits in per_token_hits:
		for hit in token_hits:
			entry = entries.setdefault(hit["name"], [hit, 0, len(entries)])
			if entry[1] < len(per_token_hits):
				entry[1] += 1

	ranked = sorted(entries.values(), key=lambda entry: (-entry[1], entry[2]))
	return [entry[0] for entry in ranked]


def _widen_hits(search_engine, query: str, filters: dict, hits: list[dict]) -> list[dict]:
	"""Search each word alone when the whole query returned few results.

	Issues only plain single-word queries, so it does not depend on the
	engine's query syntax, and only when the first pass came back thin, so a
	good query costs nothing extra. Any failure falls back to the first pass.
	"""
	tokens = _query_tokens(query)
	if len(hits) >= _WIDEN_BELOW or len(tokens) < 2:
		return hits

	try:
		per_token = [search_engine.search(token, filters=filters)["results"] for token in tokens]
	except Exception:
		frappe.log_error(title="Wiki Search Widen Error", message=f"Query: {query!r}")
		return hits

	return _merge_token_hits(hits, per_token)[:_MAX_WIDENED_RESULTS]


def _clean_snippet(text: str | None) -> str:
	"""Turn an FTS snippet into readable prose without another database read.

	The index still holds markdown on pages that have not been reindexed, and
	the parent indexer flattens headings onto one line before wiki can strip
	them. Cleaning the handful of snippets already returned is enough: no extra
	query, no full-document load.
	"""
	if not text:
		return ""

	text = text.replace("<mark>", _MARK_OPEN).replace("</mark>", _MARK_CLOSE)
	text = re.sub(r"<[^>]+>", " ", text)
	text = re.sub(r"(?:^|\s)#{1,6}(?=\s|$)", " ", text)
	text = re.sub(r"`+", "", text)
	text = re.sub(r"\*{1,3}", "", text)
	text = re.sub(r"(?:^|\s)[-*_]{3,}(?=\s|$)", " ", text)
	text = re.sub(r"\s+", " ", text).strip()
	return text.replace(_MARK_OPEN, "<mark>").replace(_MARK_CLOSE, "</mark>")


def _filter_hits_by_space_visibility(hits: list[dict]) -> list[dict]:
	"""Drop search hits the current user couldn't open as a page.

	The SQLite index is built without user context, so titles/snippets from
	restricted spaces can surface here. Resolve each hit's denormalized
	wiki_space and gate it through the same checks as page rendering: the
	space must be published (`check_published`) and readable by the current
	user (`check_space_access`). Orphan documents (no wiki_space) stay
	readable by all.
	"""
	from wiki.permissions import can_read_space

	names = [hit["name"] for hit in hits]
	if not names:
		return hits

	space_by_name = {
		row.name: row.wiki_space
		for row in frappe.get_all(
			"Wiki Document",
			filters={"name": ("in", names)},
			fields=["name", "wiki_space"],
		)
	}

	visible: dict[str, bool] = {}

	def _is_visible(space_name: str) -> bool:
		if space_name not in visible:
			space_published = frappe.get_cached_value("Wiki Space", space_name, "is_published")
			visible[space_name] = bool(space_published) and can_read_space(space_name)
		return visible[space_name]

	allowed = []
	for hit in hits:
		hit_space = space_by_name.get(hit["name"])
		if not hit_space or _is_visible(hit_space):
			allowed.append(hit)
	return allowed
