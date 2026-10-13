"""What a published page says about its neighbours: where it sits, who links to it.

Both are rendered by one template per block, used for the first page load and
for client-side navigation alike, so the two can never drift.
"""

from urllib.parse import quote

import frappe

from wiki.versions_logic import counterpart_route, order_versions

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


def version_options(doc) -> list[dict]:
	"""The other versions of this page's documentation, for the reader's switcher.

	A space joins a group by sharing its `version_group`. Each option points at the
	same page in that version when it exists, else at that version's landing page.
	Only published spaces the reader may open are listed; nothing happens for a
	space with no group, so the common case costs no query.
	"""
	from wiki.permissions import can_read_space

	space = doc.get_space_name()
	group = space and frappe.get_cached_value("Wiki Space", space, "version_group")
	if not group:
		return []

	rows = frappe.get_all(
		"Wiki Space",
		filters={"version_group": group, "is_published": 1},
		fields=["name", "route", "version_label", "space_name"],
	)
	if len(rows) < 2:
		return []

	current_space_route = next((row.route for row in rows if row.name == space), None)
	if current_space_route is None:
		return []

	options = []
	for row in order_versions([r for r in rows if r.name == space or can_read_space(r.name)]):
		if row.name == space:
			url = doc.route
		else:
			url = counterpart_route(doc.route or "", current_space_route, row.route)
			if url != row.route and not frappe.db.exists(
				"Wiki Document", {"route": url, "is_published": 1, "wiki_space": row.name}
			):
				url = row.route
		options.append(
			{
				"label": row.version_label or row.space_name or row.route,
				"url": "/" + quote(url),
				"current": row.name == space,
			}
		)
	return options


def render_related(doc) -> dict:
	"""HTML for the breadcrumb bar and the "Linked from" list."""
	trail = breadcrumb_trail(doc)
	links = get_backlinks(doc)
	versions = version_options(doc)
	return {
		"versions_html": frappe.render_template(
			"templates/wiki/includes/version_switcher.html", {"versions": versions}
		)
		if versions
		else "",
		"breadcrumbs_html": frappe.render_template(
			"templates/wiki/includes/breadcrumbs.html", {"trail": trail}
		)
		if trail
		else "",
		"backlinks_html": frappe.render_template("templates/wiki/includes/backlinks.html", {"links": links})
		if links
		else "",
	}
