import unittest

from wiki.wiki.slug_text import strip_accents


class TestStripAccents(unittest.TestCase):
	def test_spanish_titles(self):
		self.assertEqual(strip_accents("Banderas de configuración"), "Banderas de configuracion")
		self.assertEqual(strip_accents("Operación y Administración"), "Operacion y Administracion")
		self.assertEqual(strip_accents("Año Pingüino"), "Ano Pinguino")

	def test_plain_text_and_empty_pass_through(self):
		self.assertEqual(strip_accents("Inicio"), "Inicio")
		self.assertEqual(strip_accents(None), "")
		self.assertEqual(strip_accents(""), "")

	def test_other_scripts_are_not_destroyed(self):
		self.assertEqual(strip_accents("日本語"), "日本語")


if __name__ == "__main__":
	unittest.main()
