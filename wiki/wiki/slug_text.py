import unicodedata


def strip_accents(text: str | None) -> str:
	"""`configuración` -> `configuracion`, so a Spanish title makes a plain-ASCII address."""
	decomposed = unicodedata.normalize("NFKD", text or "")
	return "".join(char for char in decomposed if not unicodedata.combining(char))
