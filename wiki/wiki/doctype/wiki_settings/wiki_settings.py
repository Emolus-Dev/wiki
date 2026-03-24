# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WikiSettings(Document):
	def on_update(self):
		for key in frappe.cache().hgetall("wiki_sidebar").keys():
			frappe.cache().hdel("wiki_sidebar", key)

		_clear_wiki_page_cache()


def is_guest_access_disabled() -> bool:
	return bool(frappe.db.get_single_value("Wiki Settings", "disable_guest_access"))


def enforce_guest_access_disabled() -> None:
	if frappe.session.user == "Guest" and is_guest_access_disabled():
		frappe.throw(frappe._("You must be logged in to view this page"), frappe.PermissionError)


@frappe.whitelist()
def get_all_spaces():
	return frappe.get_all("Wiki Space", pluck="route")


@frappe.whitelist()
def clear_wiki_page_cache():
	frappe.only_for("System Manager")
	_clear_wiki_page_cache()
	return True


def _clear_wiki_page_cache():
	routes = set()

	for doctype in ("Wiki Page", "Wiki Document", "Wiki Space"):
		for route in frappe.get_all(doctype, pluck="route"):
			if route:
				routes.add(route.lstrip("/"))

	for route in routes:
		frappe.cache().hdel("website_page", route)
