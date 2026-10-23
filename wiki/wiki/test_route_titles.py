"""Pure tests for the route planner (no Frappe needed): run with
`python3 -m unittest wiki.wiki.test_route_titles` from the app root."""

import re
import sys
import types
import unittest

# route_titles imports frappe for the apply step only; the planner needs none of it.
if "frappe" not in sys.modules:
	frappe = types.ModuleType("frappe")
	frappe._ = lambda text: text
	frappe.whitelist = lambda *a, **k: (lambda fn: fn)
	sys.modules["frappe"] = frappe

from wiki.wiki.route_titles import plan_route_fixes


def slugify(text):
	text = (text or "").lower()
	for src, dst in zip("áéíóúñ", "aeioun", strict=True):
		text = text.replace(src, dst)
	return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def doc(name, parent, title, route, slug=None, **extra):
	return {
		"name": name,
		"parent": parent,
		"title": title,
		"route": route,
		"slug": slug if slug is not None else route.rsplit("/", 1)[-1],
		"sort_order": extra.pop("sort_order", 0),
		**extra,
	}


def plan(docs, reserved=None):
	return plan_route_fixes("docs", "root", docs, reserved, slugify=slugify)


class TestPlanRouteFixes(unittest.TestCase):
	def test_a_renamed_page_gets_the_route_of_its_title(self):
		docs = [doc("p1", "root", "Banderas de configuración", "docs/verificador-integrado")]
		self.assertEqual(
			[(c["old_route"], c["new_route"]) for c in plan(docs)],
			[("docs/verificador-integrado", "docs/banderas-de-configuracion")],
		)

	def test_a_page_already_on_its_title_is_left_alone(self):
		self.assertEqual(plan([doc("p1", "root", "Inicio", "docs/inicio")]), [])

	def test_a_renamed_group_moves_its_branch(self):
		docs = [
			doc("g", "root", "Guía de usuario", "docs/guia"),
			doc("p", "g", "Configurar", "docs/guia/configurar"),
		]
		changes = {c["name"]: c["new_route"] for c in plan(docs)}
		self.assertEqual(changes, {"g": "docs/guia-de-usuario", "p": "docs/guia-de-usuario/configurar"})

	def test_the_page_served_at_the_space_route_is_skipped(self):
		self.assertEqual(plan([doc("home", "root", "Bienvenida", "docs")]), [])

	def test_external_links_are_skipped_and_keep_their_route_reserved(self):
		docs = [
			doc("link", "root", "Sitio", "docs/sitio", is_external_link=1),
			doc("p", "root", "Sitio", "docs/viejo"),
		]
		changes = plan(docs)
		self.assertEqual([(c["name"], c["new_route"]) for c in changes], [("p", "docs/sitio-2")])

	def test_two_pages_with_one_title_do_not_share_a_route(self):
		docs = [
			doc("a", "root", "Notas", "docs/a", sort_order=1),
			doc("b", "root", "Notas", "docs/b", sort_order=2),
		]
		self.assertEqual(
			[(c["name"], c["new_route"]) for c in plan(docs)],
			[("a", "docs/notas"), ("b", "docs/notas-2")],
		)

	def test_a_route_held_by_another_space_is_not_taken(self):
		docs = [doc("a", "root", "Notas", "docs/a")]
		self.assertEqual(plan(docs, reserved={"docs/notas"})[0]["new_route"], "docs/notas-2")

	def test_a_stale_slug_alone_is_reported(self):
		docs = [doc("a", "root", "Notas", "docs/notas", slug="viejo")]
		change = plan(docs)[0]
		self.assertEqual((change["old_route"], change["new_route"], change["new_slug"]), ("docs/notas", "docs/notas", "notas"))

	def test_a_page_swapping_into_a_sibling_title_ends_consistent(self):
		docs = [
			doc("a", "root", "Dos", "docs/uno", sort_order=1),
			doc("b", "root", "Uno", "docs/dos", sort_order=2),
		]
		routes = {c["name"]: c["new_route"] for c in plan(docs)}
		self.assertEqual(routes, {"a": "docs/dos", "b": "docs/uno"})
		self.assertEqual(len(set(routes.values())), 2)


if __name__ == "__main__":
	unittest.main()
