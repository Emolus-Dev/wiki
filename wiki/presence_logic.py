"""Who is editing a page right now, from heartbeats. No Frappe imports."""

# An editor pings every 20 s; this tolerates one missed ping.
PRESENCE_TTL = 50


def fresh_editors(beats: dict[str, float], now: float, me: str, ttl: int = PRESENCE_TTL):
	"""Split `{user: last_ping_time}` into (other active users, stale users).

	`me` is never listed among the others. Stale users are returned so the caller
	can forget them.
	"""
	others = []
	stale = []
	for user, seen in beats.items():
		if now - float(seen) > ttl:
			stale.append(user)
		elif user != me:
			others.append(user)
	return sorted(others), sorted(stale)
