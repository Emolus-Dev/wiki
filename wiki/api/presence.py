import hashlib
import re
import time

import frappe
from frappe import _

from wiki.presence_logic import fresh_editors

CACHE_KEY = "wiki_presence"
# A page key is what the editor calls a page: letters, digits, `-` and `_`. Anything
# else would let a signed-in user fill the cache with keys of their own making.
_KEY = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@frappe.whitelist()
def heartbeat(space: str, page: str) -> list[dict]:
	"""Record that the current user has `page` open for editing; return who else does.

	Called every few seconds by an open editor. Nothing is written to the
	database: pings live in the cache and age out on their own, so presence costs
	one cache write per ping and never touches a document.
	"""
	from wiki.permissions import can_read_space

	user = frappe.session.user
	if user == "Guest" or not _valid(space) or not _valid(page) or not can_read_space(space):
		return []

	cache = frappe.cache()
	key = f"{space}:{page}"
	now = time.time()
	beats = {**_beats(cache, key), user: now}
	others, stale = fresh_editors(beats, now, user)
	for gone in stale:
		beats.pop(gone, None)
	cache.hset(CACHE_KEY, key, beats)

	return [_person(other) for other in others]


@frappe.whitelist()
def leave(space: str, page: str):
	"""Forget the current user's ping, so the others stop seeing them at once."""
	if not _valid(space) or not _valid(page):
		return
	cache = frappe.cache()
	key = f"{space}:{page}"
	beats = _beats(cache, key)
	if beats.pop(frappe.session.user, None) is not None:
		if beats:
			cache.hset(CACHE_KEY, key, beats)
		else:
			# Nobody left: forget the page, so keys do not pile up.
			cache.hdel(CACHE_KEY, key)


def _valid(value) -> bool:
	return isinstance(value, str) and bool(_KEY.match(value))


def _beats(cache, key: str) -> dict:
	return cache.hget(CACHE_KEY, key) or {}


def _person(user: str) -> dict:
	"""What another viewer is shown as: a name and a picture. Never their email, which
	is the user id and would be handed to everyone who can read the space."""
	full_name, image = frappe.get_cached_value("User", user, ["full_name", "user_image"]) or (None, None)
	return {
		"id": hashlib.sha256(f"{frappe.local.site}:{user}".encode()).hexdigest()[:12],
		"full_name": full_name or _("Someone"),
		"image": image,
	}
