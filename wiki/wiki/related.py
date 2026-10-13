"""What a published page says about its neighbours: where it sits, who links to it.

Both are rendered by one template per block, used for the first page load and
for client-side navigation alike, so the two can never drift.
"""

from urllib.parse import quote

import frappe

BACKLINKS_CACHE_KEY = "wiki_backlinks"
BACKLINK_LIMIT = 20


def find_backlinks(doc_key: str, wiki_space: str | None, exclude: str) -> list[dict]:
	"""Published pages of the same space that link to `doc_key` with `[..](wiki:<key>)`.

	Same space only, like the links themselves: access is granted per space, so
	nothing here can name a page the reader may not see.
	"""
	if not doc_key or not wiki_space:
		return []

	rows = frappe.get_all(
		"Wiki Document",
		filters={
			"wiki_space": wiki_space,
			"is_published": 1,
			"is_group": 0,
			"is_external_link": 0,
			"name": ("!=", exclude),
			"content": ("like", f"%(wiki:{doc_key}%"),
		},
		fields=["title", "route"],
		order_by="title asc",
		limit=BACKLINK_LIMIT,
	)
	return [row for row in rows if row.route]


def get_backlinks(doc) -> list[dict]:
	"""`find_backlinks`, cached per page. Every wiki edit clears the lot (see
	`clear_wiki_tree_cache`), so a new link shows up on the next view."""
	cache = frappe.cache()
	cached = cache.hget(BACKLINKS_CACHE_KEY, doc.name)
	if cached is not None:
		return cached
	links = find_backlinks(doc.doc_key, doc.get_space_name(), doc.name)
	cache.hset(BACKLINKS_CACHE_KEY, doc.name, links)
	return links


def clear_backlinks_cache():
	frappe.cache().delete_value(BACKLINKS_CACHE_KEY)
	frappe.db.after_commit.add(lambda: frappe.cache().delete_value(BACKLINKS_CACHE_KEY))


def breadcrumb_trail(doc) -> dict | None:
	"""The space, then the groups the page sits in, outermost first."""
	space = doc.get_wiki_space()
	if not space:
		return None

	root_group = frappe.db.get_value("Wiki Space", space["name"], "root_group")
	groups = []
	for name in reversed(doc.get_ancestors()):
		if name == root_group:
			continue
		title = frappe.get_cached_value("Wiki Document", name, "title")
		if title:
			groups.append(title)

	return {
		"space_name": space.get("space_name") or space["name"],
		"space_url": "/" + quote(space["route"]) if space.get("route") else None,
		"groups": groups,
	}


def render_related(doc) -> dict:
	"""HTML for the breadcrumb bar and the "Linked from" list."""
	trail = breadcrumb_trail(doc)
	links = get_backlinks(doc)
	return {
		"breadcrumbs_html": frappe.render_template(
			"templates/wiki/includes/breadcrumbs.html", {"trail": trail}
		)
		if trail
		else "",
		"backlinks_html": frappe.render_template(
			"templates/wiki/includes/backlinks.html", {"links": links}
		)
		if links
		else "",
	}
