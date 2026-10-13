"""Turn a page's snapshots into its list of versions. No Frappe imports."""


def distinct_versions(snapshots: list[dict]) -> list[dict]:
	"""Keep only the snapshots where the page changed.

	`snapshots` is ordered newest first, one per merge that held the page, each
	with `title`, `content_blob` and `is_deleted`. The result is newest first
	and each entry is the merge that *introduced* that state, so a page edited
	once in March and left alone since lists March, not every merge after it.
	"""
	versions = []
	previous_state = None
	for snapshot in reversed(snapshots):
		state = (snapshot.get("title"), snapshot.get("content_blob"), bool(snapshot.get("is_deleted")))
		if state != previous_state:
			versions.append(snapshot)
		previous_state = state
	versions.reverse()
	return versions
