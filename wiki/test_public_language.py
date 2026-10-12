import frappe

from wiki.tests import WikiTestCase as FrappeTestCase
from wiki.utils import apply_public_language, reader_lang


class TestPublicLanguage(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.original_lang = frappe.local.lang

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.lang = self.original_lang
		frappe.db.rollback()

	def test_guest_gets_the_configured_public_language(self):
		frappe.db.set_single_value("Wiki Settings", "public_language", "es")
		frappe.local.lang = "en"
		frappe.set_user("Guest")

		apply_public_language()

		self.assertEqual(frappe.local.lang, "es")
		self.assertEqual(reader_lang(), "es")

	def test_logged_in_user_keeps_their_own_language(self):
		frappe.db.set_single_value("Wiki Settings", "public_language", "es")
		frappe.local.lang = "fr"

		apply_public_language()

		self.assertEqual(frappe.local.lang, "fr")

	def test_spanish_catalogue_translates_reader_strings(self):
		frappe.local.lang = "es"

		self.assertEqual(frappe._("On this page"), "En esta página")
		self.assertEqual(frappe._("Type to search documentation"), "Escribe para buscar en la documentación")
