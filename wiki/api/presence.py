import time

import frappe

from wiki.presence_logic import fresh_editors

CACHE_KEY = "wiki_presence"


@frappe.whitelist()
def heartbeat(space: str, page: str) -> list[dict]:
	"""Record that the current user has `page` open for editing; return who else does.

	Called every few seconds by an open editor. Nothing is written to the
	database: pings live in the cache and age out on their own, so presence costs
	one cache write per ping and never touches a document.
	"""
	from wiki.permissions import can_read_space

	user = frappe.session.user
	if user == "Guest" or not space or not page or not can_read_space(space):
		return []

	cache = frappe.cache()
	key = f"{space}:{page}"
	now = time.time()
	cache.hset(CACHE_KEY, key, {**_beats(cache, key), user: now})

	others, stale = fresh_editors(_beats(cache, key), now, user)
	if stale:
		beats = {u: seen for u, seen in _beats(cache, key).items() if u not in stale}
		cache.hset(CACHE_KEY, key, beats)

	return [_person(other) for other in others]


@frappe.whitelist()
def leave(space: str, page: str):
	"""Forget the current user's ping, so the others stop seeing them at once."""
	cache = frappe.cache()
	key = f"{space}:{page}"
	beats = _beats(cache, key)
	if beats.pop(frappe.session.user, None) is not None:
		cache.hset(CACHE_KEY, key, beats)


def _beats(cache, key: str) -> dict:
	return cache.hget(CACHE_KEY, key) or {}


def _person(user: str) -> dict:
	full_name, image = frappe.get_cached_value("User", user, ["full_name", "user_image"]) or (user, None)
	return {"user": user, "full_name": full_name or user, "image": image}
