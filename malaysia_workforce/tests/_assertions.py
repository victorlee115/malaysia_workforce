from __future__ import annotations

import re
from contextlib import contextmanager


@contextmanager
def raises(exception_type, *, match: str | None = None):
	"""Small stdlib-only equivalent used by tests loaded inside a Frappe bench."""
	try:
		yield
	except exception_type as exc:
		if match is not None and not re.search(match, str(exc)):
			raise AssertionError(f"{exc!r} does not match {match!r}") from exc
	else:
		raise AssertionError(f"Expected {exception_type.__name__} to be raised")
