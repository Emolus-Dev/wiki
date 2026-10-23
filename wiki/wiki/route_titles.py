"""Bring page URLs back in line with page titles.

A page's route is fixed when it is created and, by design, never follows a
rename: authors own their URLs. The cost is a page renamed later keeps the old
words in its address ("Banderas de configuración" served at
`/docs/verificador-integrado`). `plan_route_fixes` works out the route each page
would have if it were created today, and `fix_routes_from_titles` applies it.

Run it as a dry run first; nothing is written until `apply` is set:

    bench --site <site> execute wiki.wiki.route_titles.fix_routes_from_titles \
        --kwargs "{'space': '<space name>'}"
    bench --site <site> execute wiki.wiki.route_titles.fix_routes_from_titles \
        --kwargs "{'space': '<space name>', 'apply': 1}"
"""

from collections import defaultdict

import frappe
from frappe import _


def plan_route_fixes(
	space_route: str,
	root_name: str,
	docs: list[dict],
	reserved: set[str] | None = None,
	slugify=None,
) -> list[dict]:
	"""Return the pages whose route differs from the one their title gives.

	`docs` are the space's Wiki Documents (name, parent, title, slug, route,
	is_external_link, sort_order). A route is the space route, then the new slug of
	each ancestor group below the root, then the page's own slug, so a renamed
	group moves its whole branch. Pages are visited in tree order, and a slug that
	another page already holds gets `-2`, `-3`... Skipped on purpose: the root
	group, the page served at the space route itself, and external links.
	"""
	slugify = slugify or _slugify
	reserved = set(reserved or ())
	children = defaultdict(list)
	for doc in docs:
		children[doc.get("parent")].append(doc)
	for siblings in children.values():
		siblings.sort(key=lambda d: (d.get("sort_order") or 0, d["name"]))

	# Routes this pass leaves alone still belong to somebody.
	kept = {
		doc["route"]
		for doc in docs
		if doc.get("route") and (doc.get("is_external_link") or doc["route"] == space_route)
	}
	taken = reserved | kept
	changes = []

	def visit(parent_name, prefix):
		for doc in children.get(parent_name, []):
			if doc.get("is_external_link") or doc.get("route") == space_route:
				continue
			slug = slugify(doc.get("title")) or doc.get("slug") or slugify(doc["name"])
			route = _free_route(prefix, slug, taken)
			taken.add(route)
			if route != doc.get("route") or slug != doc.get("slug"):
				changes.append(
					{
						"name": doc["name"],
						"title": doc.get("title"),
						"old_route": doc.get("route"),
						"new_route": route,
						"old_slug": doc.get("slug"),
						"new_slug": route.rsplit("/", 1)[-1],
					}
				)
			visit(doc["name"], route)

	visit(root_name, space_route.strip("/"))
	return changes


def _free_route(prefix: str, slug: str, taken: set[str]) -> str:
	base = f"{prefix}/{slug}" if prefix else slug
	candidate, n = base, 2
	while candidate in taken:
		candidate = f"{base}-{n}"
		n += 1
	return candidate


def _slugify(text):
	from wiki.frappe_wiki.doctype.wiki_document.wiki_document import slugify_segment

	return slugify_segment(text)


@frappe.whitelist()
def fix_routes_from_titles(space: str, apply: int | bool = 0) -> dict:
	"""Dry-run (default) or apply the title-based routes of one Wiki Space."""
	frappe.only_for("Wiki Manager")

	space_doc = frappe.get_doc("Wiki Space", space)
	if space_doc.git_synced:
		frappe.throw(_("The repository owns the routes of a git-synced space."))
	if not space_doc.root_group:
		frappe.throw(_("This Wiki Space has no root group."))

	fields = ["name", "doc_key", "title", "slug", "route", "is_external_link", "sort_order", "parent_wiki_document"]
	docs = frappe.get_all("Wiki Document", filters={"wiki_space": space}, fields=fields, limit=0)
	for doc in docs:
		doc["parent"] = doc.pop("parent_wiki_document")
	by_name = {doc["name"]: doc for doc in docs}

	reserved = set(
		frappe.get_all(
			"Wiki Document",
			filters={"wiki_space": ["!=", space], "is_group": 0},
			pluck="route",
			limit=0,
		)
	)
	changes = plan_route_fixes(space_doc.route, space_doc.root_group, docs, reserved)
	for change in changes:
		change["doc_key"] = by_name[change["name"]]["doc_key"]

	if apply:
		_apply(changes)
	return {"space": space, "applied": bool(apply), "count": len(changes), "changes": changes}


def _apply(changes: list[dict]):
	from wiki.frappe_wiki.doctype.wiki_document.wiki_document import clear_wiki_tree_cache
	from frappe.website.utils import clear_cache as clear_website_cache

	for change in changes:
		frappe.db.set_value(
			"Wiki Document",
			change["name"],
			{"route": change["new_route"], "slug": change["new_slug"]},
			update_modified=False,
		)
		# Snapshots carry their own copy of the route: a change request opened before this
		# would put the old one back when it merges.
		frappe.db.set_value(
			"Wiki Revision Item",
			{"doc_key": change["doc_key"], "route": change["old_route"]},
			{"route": change["new_route"], "slug": change["new_slug"]},
			update_modified=False,
		)

	_redirect_old_routes([c for c in changes if c["old_route"] and c["old_route"] != c["new_route"]])
	clear_website_cache()
	frappe.db.after_commit.add(clear_website_cache)
	clear_wiki_tree_cache()


def _redirect_old_routes(changes: list[dict]):
	"""Keep old addresses working (permanent redirects) through Website Settings."""
	import re

	if not changes:
		return
	settings = frappe.get_doc("Website Settings")
	existing = {row.source: row for row in settings.get("route_redirects") or []}
	for change in changes:
		new_target = "/" + change["new_route"]
		# A redirect that pointed at the old address now follows the page.
		for row in settings.route_redirects:
			if (row.target or "").strip("/") == change["old_route"]:
				row.target = new_target
		source = re.escape(change["old_route"])
		if source not in existing:
			row = settings.append(
				"route_redirects",
				{"source": source, "target": new_target, "redirect_http_status": 301},
			)
			existing[source] = row
	settings.save(ignore_permissions=True)


def add_route_redirect(old_route: str, new_route: str) -> None:
	"""One page moved: keep its old address working. Never blocks the caller."""
	try:
		_redirect_old_routes([{"old_route": old_route, "new_route": new_route}])
	except Exception:
		frappe.log_error(title="Wiki route redirect failed")
