"""Telemetry is off in this fork: nothing is sent to Pulse.

The call sites keep calling `capture()` so they stay close to upstream and
merge cleanly; this module is the one place that decides nothing leaves."""


def default_properties() -> dict:
	return {}


def capture(event: str, interval: str | None = None, **props):
	return None


def error_kind(exception: BaseException) -> str:
	"""Bucket an exception by class, never by message — a message can carry a repo
	name or a token fragment."""
	import requests

	if isinstance(exception, requests.HTTPError):
		status = getattr(exception.response, "status_code", None)
		return "auth" if status in (401, 403, 404) else "other"
	if isinstance(exception, requests.RequestException):
		return "network"
	return "other"


def duration_bucket(seconds: float) -> str:
	"""Wall time as a bucket. A raw duration is a high-cardinality number; the
	decision it feeds ("is this affordable") only needs the band."""
	for limit, label in ((1, "lt_1s"), (3, "1_3s"), (10, "3_10s")):
		if seconds < limit:
			return label
	return "gt_10s"
