import unittest

from wiki.search_text import fold, stem


class TestStem(unittest.TestCase):
	def test_related_forms_share_a_stem(self):
		for forms in (
			("configurar", "configurado", "configuración", "configuraciones", "configurando"),
			("instalar", "instalación", "instalaciones", "instalado"),
			("usuario", "usuarios"),
			("permiso", "permisos"),
		):
			self.assertEqual({stem(word) for word in forms}, {stem(forms[0])}, forms)

	def test_accents_and_case_do_not_matter(self):
		self.assertEqual(stem("CONFIGURACIÓN"), stem("configuracion"))
		self.assertEqual(fold("Ñandú"), "nandu")

	def test_short_words_are_left_whole(self):
		self.assertEqual(stem("con"), "con")
		self.assertEqual(stem("los"), "los")
		self.assertEqual(stem("peso"), "peso")

	def test_a_stem_never_gets_too_short(self):
		for word in ("casas", "ver", "dar", "ir", "mesas", "peso"):
			self.assertGreaterEqual(len(stem(word)), min(len(fold(word)), 4), word)

	def test_unrelated_words_keep_different_stems(self):
		self.assertNotEqual(stem("configurar"), stem("instalar"))
		self.assertNotEqual(stem("permiso"), stem("usuario"))

	def test_english_words_pass_through_sensibly(self):
		self.assertEqual(stem("deploy"), "deploy")
		self.assertTrue(stem("deploys").startswith("deploy"))
