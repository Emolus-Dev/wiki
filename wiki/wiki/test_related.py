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
