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

from wiki.wiki.route_titles import plan_route_fixes, plan_undo


def slugify(text):
	text = (text or "").lower()
	for src, dst in zip("áéíóúñ", "aeioun", strict=True):
		text = text.replace(src, dst)
	return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def doc(name, parent, title, route, slug=None, **extra):
	return {
		"name": name,
		"title": title,
		"route": route,
		"slug": slug if slug is not None else route.rsplit("/", 1)[-1],
		"sort_order": extra.pop("sort_order", 0),
		**extra,
	}


def plan(docs, reserved=None):
	return plan_route_fixes("docs", docs, reserved, slugify=slugify)


class TestPlanRouteFixes(unittest.TestCase):
	def test_a_renamed_page_gets_the_route_of_its_title(self):
		docs = [doc("p1", "root", "Banderas de configuración", "docs/verificador-integrado")]
		self.assertEqual(
			[(c["old_route"], c["new_route"]) for c in plan(docs)],
			[("docs/verificador-integrado", "docs/banderas-de-configuracion")],
		)

	def test_only_the_last_segment_changes(self):
		"""A nested route keeps its path, a flat one stays flat: nothing is restructured."""
		docs = [
			doc("a", "root", "Nueva", "docs/apps/fel/vieja"),
			doc("b", "root", "Otra", "docs/vieja-2"),
			doc("c", "root", "Solo", "solo-vieja"),
		]
		routes = {c["name"]: c["new_route"] for c in plan(docs)}
		self.assertEqual(routes, {"a": "docs/apps/fel/nueva", "b": "docs/otra", "c": "solo"})

	def test_a_page_already_on_its_title_is_left_alone(self):
		self.assertEqual(plan([doc("p1", "root", "Inicio", "docs/inicio")]), [])

	def test_a_flat_route_is_not_given_the_tree_path(self):
		"""The tree says Apps / FEL App / Page; the route is `docs/page` and stays so."""
		self.assertEqual(plan([doc("p", "g", "Verificador", "docs/verificador")]), [])

	def test_groups_are_not_touched(self):
		self.assertEqual(plan([doc("g", "root", "Guía de usuario", "docs/guia", is_group=1)]), [])

	def test_the_page_served_at_the_space_route_is_skipped(self):
		self.assertEqual(plan([doc("home", "root", "Bienvenida", "docs")]), [])

	def test_external_links_are_skipped(self):
		self.assertEqual(plan([doc("link", "root", "Sitio", "docs/viejo", is_external_link=1)]), [])

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
		self.assertEqual(plan([doc("a", "root", "Notas", "docs/a")], reserved={"docs/notas"})[0]["new_route"], "docs/notas-2")

	def test_a_new_route_never_lands_on_the_old_route_of_another_page(self):
		"""Otherwise the redirect from that old address would hide the page that owns it."""
		docs = [
			doc("a", "root", "Dos", "docs/uno", sort_order=1),
			doc("b", "root", "Uno", "docs/dos", sort_order=2),
		]
		routes = {c["name"]: c["new_route"] for c in plan(docs)}
		old_routes = {"docs/uno", "docs/dos"}
		self.assertEqual(routes, {"a": "docs/dos-2", "b": "docs/uno-2"})
		self.assertFalse(old_routes & set(routes.values()))

	def test_a_stale_slug_alone_is_reported(self):
		docs = [doc("a", "root", "Notas", "docs/notas", slug="viejo")]
		self.assertEqual(plan(docs), [])


class TestPlanUndo(unittest.TestCase):
	def test_a_moved_page_goes_back(self):
		rows = [{"old_route": "docs/viejo", "new_route": "docs/nuevo"}]
		moves, stuck = plan_undo(rows, {"docs/nuevo": "p1"})
		self.assertEqual([(m["name"], m["old_route"]) for m in moves], [("p1", "docs/viejo")])
		self.assertEqual(stuck, [])

	def test_a_chain_goes_back_in_an_order_that_never_doubles_a_route(self):
		# a: r1 -> r2, b: r2 -> r3. Today a is at r2 and b at r3.
		rows = [
			{"old_route": "r1", "new_route": "r2"},
			{"old_route": "r2", "new_route": "r3"},
		]
		moves, stuck = plan_undo(rows, {"r2": "a", "r3": "b"})
		self.assertEqual(stuck, [])
		final = {}
		for move in moves:
			final[move["name"]] = move["old_route"]
		self.assertEqual(final, {"a": "r1", "b": "r2"})
		# a left r2 before b took it.
		self.assertLess([m["name"] for m in moves].index("a"), [m["name"] for m in moves].index("b"))

	def test_a_route_someone_else_holds_is_reported_not_forced(self):
		rows = [{"old_route": "docs/viejo", "new_route": "docs/nuevo"}]
		moves, stuck = plan_undo(rows, {"docs/nuevo": "p1", "docs/viejo": "other"})
		self.assertEqual(moves, [])
		self.assertEqual(stuck, rows)

	def test_a_redirect_with_no_page_behind_it_is_not_a_move(self):
		moves, stuck = plan_undo([{"old_route": "a", "new_route": "gone"}], {})
		self.assertEqual(moves, [])
		self.assertEqual(len(stuck), 1)


if __name__ == "__main__":
	unittest.main()
