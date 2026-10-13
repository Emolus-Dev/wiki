import frappe

from wiki.frappe_wiki.doctype.wiki_document.test_wiki_document import WikiDocumentTestBase
from wiki.wiki.related import get_backlinks


class TestBacklinks(WikiDocumentTestBase):
	def setUp(self):
		super().setUp()
		self.space = self.wiki.space()
		self.target = self.wiki.document(parent=self.space.root_group, title="Install Guide")
		self.source = self.wiki.document(
			parent=self.space.root_group,
			title="Quick Start",
			content=f"First read the [guide](wiki:{self.target.doc_key}).",
		)
		self.unrelated = self.wiki.document(parent=self.space.root_group, title="Changelog")

	def titles(self):
		return [link["title"] for link in get_backlinks(self.target)]

	def test_a_page_that_links_here_is_listed(self):
		self.assertEqual(self.titles(), ["Quick Start"])

	def test_a_page_never_lists_itself(self):
		self.target.content = f"Self [link](wiki:{self.target.doc_key})."
		self.target.save()
		self.assertEqual(self.titles(), ["Quick Start"])

	def test_an_unpublished_linker_is_hidden(self):
		self.source.is_published = 0
		self.source.save()
		self.assertEqual(self.titles(), [])

	def test_a_page_in_another_space_is_not_listed(self):
		other = self.wiki.space()
		self.wiki.document(
			parent=other.root_group,
			title="Elsewhere",
			content=f"[guide](wiki:{self.target.doc_key})",
		)
		self.assertEqual(self.titles(), ["Quick Start"])

	def test_a_new_link_shows_up_after_an_edit(self):
		self.assertEqual(self.titles(), ["Quick Start"])
		self.unrelated.content = f"See [guide](wiki:{self.target.doc_key})"
		self.unrelated.save()
		self.assertEqual(self.titles(), ["Changelog", "Quick Start"])

	def test_a_removed_link_goes_away_after_an_edit(self):
		self.assertEqual(self.titles(), ["Quick Start"])
		self.source.content = "No links now."
		self.source.save()
		self.assertEqual(self.titles(), [])

	def test_the_reader_context_carries_the_html(self):
		context = self.target.get_web_context()
		self.assertIn("Quick Start", context["backlinks_html"])
		self.assertIn("Linked from", context["backlinks_html"])
		self.assertIn(self.space.space_name, context["breadcrumbs_html"])

	def test_a_page_nobody_links_to_has_no_backlinks_html(self):
		self.assertEqual(self.unrelated.get_web_context()["backlinks_html"], "")
		self.assertEqual(frappe.cache().hget("wiki_backlinks", self.unrelated.name), None)


class TestVersionSwitcher(WikiDocumentTestBase):
	def setUp(self):
		super().setUp()
		group = f"product-{frappe.generate_hash(length=6)}"
		route = frappe.generate_hash(length=6)
		self.v1 = self.wiki.space(
			route=f"{route}-docs/v1",
			version_group=group,
			version_label="v1",
			pages=[
				{"title": "Install", "route": f"{route}-docs/v1/install"},
				{"title": "Legacy Only", "route": f"{route}-docs/v1/legacy"},
			],
		)
		self.v2 = self.wiki.space(
			route=f"{route}-docs/v2",
			version_group=group,
			version_label="v2",
			pages=[{"title": "Install", "route": f"{route}-docs/v2/install"}],
		)
		self.route = route

	def page(self, space, title):
		name = frappe.db.get_value("Wiki Document", {"wiki_space": space.name, "title": title})
		return frappe.get_doc("Wiki Document", name)

	def options(self, space, title):
		from wiki.wiki.related import version_options

		return {o["label"]: o for o in version_options(self.page(space, title))}

	def test_lists_every_version_newest_first_and_marks_the_current(self):
		from wiki.wiki.related import version_options

		options = version_options(self.page(self.v1, "Install"))
		self.assertEqual([o["label"] for o in options], ["v2", "v1"])
		self.assertEqual([o["current"] for o in options], [False, True])

	def test_the_same_page_in_another_version_is_linked_directly(self):
		self.assertEqual(self.options(self.v1, "Install")["v2"]["url"], f"/{self.route}-docs/v2/install")

	def test_a_page_missing_from_the_other_version_falls_back_to_its_landing(self):
		self.assertEqual(self.options(self.v1, "Legacy Only")["v2"]["url"], f"/{self.route}-docs/v2")

	def test_a_space_without_a_group_has_no_switcher(self):
		from wiki.wiki.related import version_options

		alone = self.wiki.space(pages=[{"title": "Solo"}])
		self.assertEqual(version_options(self.page(alone, "Solo")), [])

	def test_an_unpublished_version_is_not_offered(self):
		from wiki.wiki.related import version_options

		frappe.db.set_value("Wiki Space", self.v2.name, "is_published", 0)
		frappe.clear_document_cache("Wiki Space", self.v2.name)
		self.assertEqual(version_options(self.page(self.v1, "Install")), [])

	def test_the_reader_context_carries_the_switcher(self):
		context = self.page(self.v1, "Install").get_web_context()
		self.assertIn("wiki-version-select", context["versions_html"])
