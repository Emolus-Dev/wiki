import frappe
from frappe import _

from wiki.page_history_logic import distinct_versions

# How many merges back to look. A merge snapshots every page, so this bounds
# the query, not the page's age: the newest 300 merges of a space.
MAX_MERGES = 300
MAX_VERSIONS = 50


def _require_read(space: str):
	from wiki.permissions import can_read_space

	if not space or not can_read_space(space):
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def get_page_history(space: str, doc_key: str) -> list[dict]:
	"""The versions a page has had, newest first, from the space's merged change requests."""
	_require_read(space)
	if not doc_key:
		return []

	merges = frappe.get_all(
		"Wiki Revision",
		filters={"wiki_space": space, "is_merge": 1},
		fields=["name", "created_at", "created_by", "change_request"],
		order_by="created_at desc, creation desc",
		limit=MAX_MERGES,
	)
	if not merges:
		return []

	items = frappe.get_all(
		"Wiki Revision Item",
		filters={"revision": ("in", [m.name for m in merges]), "doc_key": doc_key},
		fields=["revision", "title", "content_blob", "is_deleted"],
	)
	item_by_revision = {item.revision: item for item in items}

	snapshots = []
	for merge in merges:
		item = item_by_revision.get(merge.name)
		if not item:
			continue
		snapshots.append(
			{
				"revision": merge.name,
				"created_at": merge.created_at,
				"created_by": merge.created_by,
				"change_request": merge.change_request,
				"title": item.title,
				"content_blob": item.content_blob,
				"is_deleted": item.is_deleted,
			}
		)

	versions = distinct_versions(snapshots)[:MAX_VERSIONS]
	for version in versions:
		version["full_name"] = frappe.get_cached_value("User", version["created_by"], "full_name") or version[
			"created_by"
		]
		version.pop("content_blob")
	return versions


@frappe.whitelist()
def get_page_version(space: str, doc_key: str, revision: str) -> dict:
	"""One version's title and text."""
	_require_read(space)

	belongs = frappe.db.get_value(
		"Wiki Revision", revision, ["wiki_space", "is_merge", "created_at"], as_dict=True
	)
	if not belongs or belongs.wiki_space != space or not belongs.is_merge:
		frappe.throw(_("Version not found"), frappe.DoesNotExistError)

	item = frappe.db.get_value(
		"Wiki Revision Item",
		{"revision": revision, "doc_key": doc_key},
		["title", "content_blob"],
		as_dict=True,
	)
	if not item:
		frappe.throw(_("Version not found"), frappe.DoesNotExistError)

	content = frappe.db.get_value("Wiki Content Blob", item.content_blob, "content") if item.content_blob else ""
	return {"title": item.title, "content": content or "", "created_at": belongs.created_at}
