"""Bring page URLs back in line with page titles, and undo it.

A page's route is fixed when it is created and did not follow a rename, so a
page renamed later kept the old words in its address ("Banderas de
configuración" at `/docs/verificador-integrado`). `plan_route_fixes` works out,
for each page, the route with the last segment taken from its title and
everything before it left alone: a flat `space/page` route stays flat, a nested
one keeps its path. Groups, external links and the page served at the space
route are not touched.

Both commands are a dry run until `apply` is set:

    bench --site <site> execute wiki.wiki.route_titles.fix_routes_from_titles \
        --kwargs "{'space': '<route or name of the space>'}"

    bench --site <site> execute wiki.wiki.route_titles.undo_route_fixes \
        --kwargs "{'since': '2026-10-23 18:00:00'}"

`undo_route_fixes` puts back every route that has a redirect created since the given
time, using the redirect itself as the record of where the page used to be.
"""

import re
from collections import defaultdict

import frappe
from frappe import _


def plan_route_fixes(
	space_route: str,
	docs: list[dict],
	reserved: set[str] | None = None,
	slugify=None,
) -> list[dict]:
	"""The pages whose last route segment differs from the slug of their title.

	A new route is never one that another page holds today, whether or not that
	page is moving too: the old address of a moved page is turned into a redirect,
	and a redirect from an address that belongs to another page would hide it. A
	slug that is taken gets `-2`, `-3`...
	"""
	slugify = slugify or _slugify
	current = {doc.get("route") for doc in docs if doc.get("route")}
	claimed = set(reserved or ())
	changes = []

	for doc in sorted(docs, key=lambda d: (d.get("sort_order") or 0, d["name"])):
		route = doc.get("route") or ""
		if doc.get("is_group") or doc.get("is_external_link") or not route or route == space_route:
			continue
		slug = slugify(doc.get("title"))
		if not slug:
			continue
		prefix = route.rsplit("/", 1)[0] + "/" if "/" in route else ""
		if route == prefix + slug:
			claimed.add(route)
			continue
		candidate, n = prefix + slug, 2
		while candidate in claimed or (candidate in current and candidate != route):
			candidate = f"{prefix}{slug}-{n}"
			n += 1
		claimed.add(candidate)
		changes.append(
			{
				"name": doc["name"],
				"title": doc.get("title"),
				"old_route": route,
				"new_route": candidate,
				"old_slug": doc.get("slug"),
				"new_slug": candidate.rsplit("/", 1)[-1],
			}
		)
	return changes


def _slugify(text):
	from wiki.frappe_wiki.doctype.wiki_document.wiki_document import slugify_segment

	return slugify_segment(text)


def _find_space(identifier: str) -> str:
	"""The Wiki Space's record name from its record name, route or display name.

	The record name is an id, not what the sidebar shows, so "Emolus Docs" and
	"emolus-docs" both have to find it.
	"""
	wanted = (identifier or "").strip()
	if frappe.db.exists("Wiki Space", wanted):
		return wanted
	for field, value in (("route", wanted.strip("/")), ("space_name", wanted)):
		name = frappe.db.get_value("Wiki Space", {field: value}, "name")
		if name:
			return name
	available = ", ".join(
		f"{row.space_name} (route {row.route})"
		for row in frappe.get_all("Wiki Space", fields=["space_name", "route"], limit=0)
	)
	frappe.throw(_("No Wiki Space matches '{0}'. Available: {1}").format(identifier, available))


@frappe.whitelist()
def fix_routes_from_titles(space: str, apply: int | bool = 0) -> dict:
	"""Dry-run (default) or apply the title-based routes of one Wiki Space."""
	frappe.only_for("Wiki Manager")
	from frappe.utils.nestedset import get_descendants_of

	space_doc = frappe.get_doc("Wiki Space", _find_space(space))
	if space_doc.git_synced:
		frappe.throw(_("The repository owns the routes of a git-synced space."))
	if not space_doc.root_group:
		frappe.throw(_("This Wiki Space has no root group."))

	names = [space_doc.root_group, *get_descendants_of("Wiki Document", space_doc.root_group, ignore_permissions=True)]
	fields = ["name", "doc_key", "title", "slug", "route", "is_group", "is_external_link", "sort_order"]
	docs = frappe.get_all("Wiki Document", filters={"name": ["in", names]}, fields=fields, limit=0)
	by_name = {doc["name"]: doc for doc in docs}

	reserved = set(
		frappe.get_all("Wiki Document", filters={"name": ["not in", names]}, pluck="route", limit=0)
	)
	changes = plan_route_fixes(space_doc.route, docs, reserved)
	for change in changes:
		change["doc_key"] = by_name[change["name"]]["doc_key"]

	if apply:
		_apply(changes)
	return {"space": space_doc.name, "applied": bool(apply), "count": len(changes), "changes": changes}


def _apply(changes: list[dict]):
	from frappe.website.utils import clear_cache as clear_website_cache

	from wiki.frappe_wiki.doctype.wiki_document.wiki_document import clear_wiki_tree_cache

	for change in changes:
		_move_route(change["name"], change["doc_key"], change["old_route"], change["new_route"], change["new_slug"])

	_redirect_old_routes([c for c in changes if c["old_route"] != c["new_route"]])
	clear_website_cache()
	frappe.db.after_commit.add(clear_website_cache)
	clear_wiki_tree_cache()


def _move_route(name: str, doc_key: str, old_route: str, new_route: str, new_slug: str):
	frappe.db.set_value(
		"Wiki Document", name, {"route": new_route, "slug": new_slug}, update_modified=False
	)
	# Snapshots carry their own copy of the route: a change request opened before this
	# would put the old one back when it merges.
	frappe.db.set_value(
		"Wiki Revision Item",
		{"doc_key": doc_key, "route": old_route},
		{"route": new_route, "slug": new_slug},
		update_modified=False,
	)


def _redirect_old_routes(changes: list[dict]):
	"""Keep old addresses working (permanent redirects) through Website Settings."""
	changes = [c for c in changes if c["old_route"] and c["old_route"] != c["new_route"]]
	if not changes:
		return
	live = set(frappe.get_all("Wiki Document", pluck="route", limit=0))
	settings = frappe.get_doc("Website Settings")
	existing = {row.source for row in settings.get("route_redirects") or []}
	for change in changes:
		# A redirect from an address that is a page's own today would hide that page.
		if change["old_route"] in live:
			continue
		new_target = "/" + change["new_route"]
		# A redirect that pointed at the old address now follows the page.
		for row in settings.route_redirects:
			if (row.target or "").strip("/") == change["old_route"]:
				row.target = new_target
		source = re.escape(change["old_route"])
		if source not in existing:
			settings.append(
				"route_redirects",
				{"source": source, "target": new_target, "redirect_http_status": 301},
			)
			existing.add(source)
	settings.save(ignore_permissions=True)


def add_route_redirect(old_route: str, new_route: str) -> None:
	"""One page moved: keep its old address working. Never blocks the caller."""
	try:
		_redirect_old_routes([{"old_route": old_route, "new_route": new_route}])
	except Exception:
		frappe.log_error(title="Wiki route redirect failed")


def plan_undo(rows: list[dict], holders: dict[str, str]) -> tuple[list[dict], list[dict]]:
	"""Which redirects can be reversed, in an order that never puts two pages on one route.

	`rows` are `{old_route, new_route}` pairs read from the redirects, `holders` maps each
	route today to the page that has it. A move is ready when its old route is free; moving
	one page frees its current route, which can make another ready, so it repeats until
	nothing more can move. Returns (moves, stuck).
	"""
	holders = dict(holders)
	pending = list(rows)
	moves = []
	progressed = True
	while pending and progressed:
		progressed = False
		for row in list(pending):
			page = holders.get(row["new_route"])
			if not page:
				continue
			if row["old_route"] in holders:
				continue
			holders.pop(row["new_route"])
			holders[row["old_route"]] = page
			moves.append({**row, "name": page})
			pending.remove(row)
			progressed = True
	return moves, pending


@frappe.whitelist()
def undo_route_fixes(since: str, apply: int | bool = 0) -> dict:
	"""Dry-run (default) or apply the reversal of every redirect created since `since`.

	`since` is a date and time such as '2026-10-23 18:00:00', server time, a little before
	the fix was run.
	"""
	frappe.only_for("Wiki Manager")
	from frappe.website.utils import clear_cache as clear_website_cache

	from wiki.frappe_wiki.doctype.wiki_document.wiki_document import clear_wiki_tree_cache

	redirect_rows = frappe.get_all(
		"Website Route Redirect",
		filters={"parent": "Website Settings", "creation": [">=", since]},
		fields=["name", "source", "target"],
		limit=0,
	)
	rows = [
		{
			"old_route": re.sub(r"\\(.)", r"\1", row["source"]).strip("/"),
			"new_route": (row["target"] or "").strip("/"),
			"redirect": row["name"],
		}
		for row in redirect_rows
	]
	pages = frappe.get_all("Wiki Document", fields=["name", "doc_key", "route"], limit=0)
	holders = {page["route"]: page["name"] for page in pages if page["route"]}
	doc_keys = {page["name"]: page["doc_key"] for page in pages}

	moves, stuck = plan_undo(rows, holders)
	for move in moves:
		move["doc_key"] = doc_keys[move["name"]]

	if apply:
		for move in moves:
			_move_route(move["name"], move["doc_key"], move["new_route"], move["old_route"], move["old_route"].rsplit("/", 1)[-1])
		undone = {move["redirect"] for move in moves}
		# Rows with no page at their target go too: the page they pointed at is already back.
		undone |= {row["redirect"] for row in stuck if row["new_route"] not in holders}
		settings = frappe.get_doc("Website Settings")
		settings.route_redirects = [row for row in settings.route_redirects if row.name not in undone]
		settings.save(ignore_permissions=True)
		clear_website_cache()
		frappe.db.after_commit.add(clear_website_cache)
		clear_wiki_tree_cache()

	return {"applied": bool(apply), "restored": moves, "not_restored": stuck}
