import re
from html import unescape

import frappe

from wiki.wiki.doctype.wiki_settings.wiki_settings import enforce_guest_access_disabled


def _extract_match_text(*values: str | None) -> str:
	for value in values:
		if not value:
			continue

		match = re.search(r"<mark>(.*?)</mark>", value, flags=re.IGNORECASE | re.DOTALL)
		if match:
			return unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()

	return ""


@frappe.whitelist(allow_guest=True)
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

	enforce_guest_access_disabled()

	if not query or not query.strip():
		return {"results": [], "total": 0}

	search_engine = WikiSQLiteSearch()
	filters = {"space": space} if space else {}

	result = search_engine.search(query, filters=filters)

	return {
		"results": [
			{
				"name": r["name"],
				"title": r["title"],
				"route": r.get("route", ""),
				"content": r["content"],
				"match_text": _extract_match_text(r["content"], r["title"]),
				"score": r["score"],
			}
			for r in result["results"]
		],
		"total": result["summary"]["total_matches"],
	}
