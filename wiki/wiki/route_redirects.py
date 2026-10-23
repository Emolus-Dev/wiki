"""Keep the old address of a page working after its route changes.

Renaming a page moves its route (see `_route_following_title` in the change request
module); when that merges, the old address becomes a permanent redirect in Website Settings.
"""

import re

import frappe


def add_route_redirect(old_route: str, new_route: str) -> None:
	"""One page moved: keep its old address working. Never blocks the caller."""
	try:
		_redirect_old_routes(old_route, new_route)
	except Exception:
		frappe.log_error(title="Wiki route redirect failed")


def _redirect_old_routes(old_route: str, new_route: str) -> None:
	if not old_route or old_route == new_route:
		return
	# A redirect from an address that is a page's own today would hide that page.
	if frappe.db.exists("Wiki Document", {"route": old_route}):
		return
	settings = frappe.get_doc("Website Settings")
	new_target = "/" + new_route
	# A redirect that pointed at the old address now follows the page.
	for row in settings.get("route_redirects") or []:
		if (row.target or "").strip("/") == old_route:
			row.target = new_target
	source = re.escape(old_route)
	if source not in {row.source for row in settings.get("route_redirects") or []}:
		settings.append(
			"route_redirects",
			{"source": source, "target": new_target, "redirect_http_status": 301},
		)
	settings.save(ignore_permissions=True)
