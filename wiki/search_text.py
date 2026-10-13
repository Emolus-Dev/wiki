"""Word handling shared by both searches (the editor's and the reader's).

No Frappe imports: this runs on plain strings so it can be tested on its own.
"""

import unicodedata

# A stem shorter than this matches too much ("con" is every second word).
MIN_STEM = 4

# Longest first, so "aciones" is tried before "ones". Spanish only strips what a
# reader would call the same word: plurals, verb endings, -ción, -mente, -idad.
_SUFFIXES = tuple(
	sorted(
		{
			"amientos",
			"imientos",
			"amiento",
			"imiento",
			"aciones",
			"uciones",
			"iciones",
			"adoras",
			"adores",
			"ancias",
			"encias",
			"logias",
			"idades",
			"acion",
			"ucion",
			"icion",
			"adora",
			"ador",
			"ancia",
			"encia",
			"logia",
			"idad",
			"mente",
			"antes",
			"ables",
			"ibles",
			"ismos",
			"istas",
			"ando",
			"iendo",
			"aron",
			"ieron",
			"aran",
			"eran",
			"aria",
			"eria",
			"ados",
			"adas",
			"idos",
			"idas",
			"ante",
			"able",
			"ible",
			"ismo",
			"ista",
			"ado",
			"ada",
			"ido",
			"ida",
			"ar",
			"er",
			"ir",
			"es",
			"as",
			"os",
			"s",
		},
		key=len,
		reverse=True,
	)
)


def fold(text: str) -> str:
	"""Lowercase and strip accents, so "configuracion" finds "Configuración"."""
	decomposed = unicodedata.normalize("NFD", text)
	return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def stem(word: str) -> str:
	"""A word's stem, so "configurar", "configurado" and "configuración" meet.

	Words are folded first. A word too short to lose a suffix and keep
	`MIN_STEM` letters is returned folded and whole.
	"""
	word = fold(word)
	for suffix in _SUFFIXES:
		if word.endswith(suffix) and len(word) - len(suffix) >= MIN_STEM:
			word = word[: -len(suffix)]
			break
	# "usuario" and "usuarios" must meet: the plural ends in -os, the singular in -o.
	while word[-1:] in ("a", "e", "i", "o") and len(word) - 1 >= MIN_STEM:
		word = word[:-1]
	return word
