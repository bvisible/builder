"""//// Neoffice — added file (no upstream equivalent): what a run of the pipeline spends.

A site build makes dozens of model calls — the design brief, one per page written, one per
page read by the vision model, one per revision — and until 2026-09-15 not one of them was
counted anywhere. The agent loop tallied its own turns into a log line; the build tallied
nothing. So the only way to learn what a build cost was to watch a prepaid balance empty,
which is exactly how a day of work ended: four full rebuilds and no idea where the money went.

This is the counter that was missing. Every call goes through builder.ai.llm.complete, so the
tally lives there: one place, no caller to remember. A build opens a span, does its work, and
reads back what it spent — by KIND, because the answer mattered: reading the pages cost six
times writing them, and nobody knew.

It counts tokens, not money: the price of a token belongs to the provider's contract, not to
this code. Multiply by the rate on your invoice.
"""

from __future__ import annotations

import threading

# the kinds a caller can name; anything else lands in "other"
WRITING = "writing"  # the pages, the brief — text in, text out
READING = "reading"  # a screenshot read by the vision model

_local = threading.local()


def _span() -> dict | None:
	return getattr(_local, "span", None)


def start() -> None:
	"""Open a tally for this thread. A second call resets it."""
	_local.span = {"calls": 0, "prompt": 0, "completion": 0, "by_kind": {}}


def stop() -> dict:
	"""Close the tally and return it. An empty one when none was open."""
	span = _span() or {"calls": 0, "prompt": 0, "completion": 0, "by_kind": {}}
	_local.span = None
	return span


def read() -> dict:
	"""The tally so far, without closing it."""
	return dict(_span() or {"calls": 0, "prompt": 0, "completion": 0, "by_kind": {}})


def kind(name: str):
	"""Name what the next calls on this thread are for, as a context manager."""

	class _Kind:
		def __enter__(self):
			self.previous = getattr(_local, "kind", None)
			_local.kind = name
			return self

		def __exit__(self, *exc):
			_local.kind = self.previous
			return False

	return _Kind()


def add(model: str, usage) -> None:
	"""Add one call to the open tally. Never raises: a counter must not break a build."""
	span = _span()
	if span is None:
		return
	try:
		prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
		completion = int(getattr(usage, "completion_tokens", 0) or 0)
		if not prompt and not completion:
			return
		span["calls"] += 1
		span["prompt"] += prompt
		span["completion"] += completion
		row = span["by_kind"].setdefault(getattr(_local, "kind", None) or "other", {"calls": 0, "prompt": 0, "completion": 0})
		row["calls"] += 1
		row["prompt"] += prompt
		row["completion"] += completion
	except Exception:
		pass


def summary_line(span: dict) -> str:
	"""One line for the build's summary, in thousands of tokens."""
	if not span or not span.get("calls"):
		return ""
	def k(n):
		return f"{round(n / 1000):d}k" if n >= 1000 else str(n)

	parts = []
	for name in (WRITING, READING, "other"):
		row = (span.get("by_kind") or {}).get(name)
		if row:
			parts.append(f"{name} {row['calls']} call(s), {k(row['prompt'])} in / {k(row['completion'])} out")
	detail = "; ".join(parts)
	return (
		f"This build made {span['calls']} model call(s): {k(span['prompt'])} tokens in, "
		f"{k(span['completion'])} out" + (f" ({detail})." if detail else ".")
	)


# //// Neoffice — a ceiling, because a counter that only reports is a counter you read after the
# //// fact. `nora_build_token_budget` in site_config, in thousands of tokens; 0 or absent means no
# //// ceiling. The build checks it between pages and stops writing new ones, finishing what it has
# //// rather than dying: a site with four good pages beats a crash at page five.
def over_budget() -> int:
	"""How many thousand tokens the open span is over its budget, 0 while inside it."""
	span = _span()
	if not span:
		return 0
	try:
		import frappe

		budget = int(frappe.utils.cint(frappe.conf.get("nora_build_token_budget") or 0))
	except Exception:
		return 0
	if budget <= 0:
		return 0
	spent = round((span["prompt"] + span["completion"]) / 1000)
	return max(0, spent - budget)

