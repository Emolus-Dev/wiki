from wiki.frappe_wiki.doctype.wiki_document.search import _clean_snippet
from wiki.frappe_wiki.doctype.wiki_document.wiki_sqlite_search import WikiSQLiteSearch
from wiki.tests import WikiTestCase as IntegrationTestCase


class TestSearchSnippet(IntegrationTestCase):
	def test_clean_snippet_drops_markdown_and_keeps_the_highlight(self):
		raw = "<mark>Git</mark> - Guía Completa ok --- ## Configuración Inicial ### Guardar credenciales"
		cleaned = _clean_snippet(raw)

		self.assertIn("<mark>Git</mark>", cleaned)
		self.assertNotIn("#", cleaned)
		self.assertNotIn("---", cleaned)
		self.assertIn("Configuración Inicial", cleaned)
		self.assertIn("Guardar credenciales", cleaned)

	def test_strip_markdown_cleans_text_the_indexer_already_flattened(self):
		flat = "Git guía --- ## Configuración ### Identidad global"
		plain = WikiSQLiteSearch()._strip_markdown(flat)

		self.assertNotIn("#", plain)
		self.assertNotIn("---", plain)
		self.assertIn("Configuración", plain)
		self.assertIn("Identidad global", plain)
