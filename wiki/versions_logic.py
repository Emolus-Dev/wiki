"""Documentation versions: ordering the switcher and mapping a page across them.

No Frappe imports, so it runs on plain data and tests on its own.
"""

import re


def _natural_key(label: str):
	"""'v10' sorts after 'v9': digits compare as numbers."""
	return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", label or "")]


def order_versions(rows: list[dict]) -> list[dict]:
	"""Newest first, by label. Labels are compared naturally, so v10 comes before v9."""
	return sorted(
		rows, key=lambda row: _natural_key(row.get("version_label") or row.get("route")), reverse=True
	)


def counterpart_route(current_route: str, current_space_route: str, target_space_route: str) -> str:
	"""Where the same page would live in another version of the space.

	`docs/v1/setup/install` in space `docs/v1` maps to `docs/v2/setup/install` in
	`docs/v2`. A page that is not under its space's route maps to the target's own.
	"""
	if current_route == current_space_route or not current_route:
		return target_space_route
	prefix = current_space_route.rstrip("/") + "/"
	if current_route.startswith(prefix):
		return target_space_route.rstrip("/") + "/" + current_route[len(prefix) :]
	return target_space_route
