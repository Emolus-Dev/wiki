import unittest

from wiki.versions_logic import counterpart_route, order_versions


class TestOrderVersions(unittest.TestCase):
	def labels(self, labels):
		return [
			row["version_label"] for row in order_versions([{"version_label": label} for label in labels])
		]

	def test_newest_first(self):
		self.assertEqual(self.labels(["v1", "v3", "v2"]), ["v3", "v2", "v1"])

	def test_numbers_compare_as_numbers(self):
		self.assertEqual(self.labels(["v9", "v10", "v2"]), ["v10", "v9", "v2"])

	def test_dotted_versions(self):
		self.assertEqual(self.labels(["1.2", "1.10", "1.9"]), ["1.10", "1.9", "1.2"])

	def test_a_missing_label_falls_back_to_the_route(self):
		rows = [{"version_label": "", "route": "docs/a"}, {"version_label": "", "route": "docs/b"}]
		self.assertEqual([r["route"] for r in order_versions(rows)], ["docs/b", "docs/a"])


class TestCounterpartRoute(unittest.TestCase):
	def test_the_same_page_in_another_version(self):
		self.assertEqual(
			counterpart_route("docs/v1/setup/install", "docs/v1", "docs/v2"), "docs/v2/setup/install"
		)

	def test_the_space_landing_maps_to_the_other_landing(self):
		self.assertEqual(counterpart_route("docs/v1", "docs/v1", "docs/v2"), "docs/v2")

	def test_a_sibling_prefix_is_not_mistaken_for_a_child(self):
		self.assertEqual(counterpart_route("docs/v10/x", "docs/v1", "docs/v2"), "docs/v2")

	def test_a_page_outside_the_space_route_maps_to_the_landing(self):
		self.assertEqual(counterpart_route("elsewhere/page", "docs/v1", "docs/v2"), "docs/v2")
