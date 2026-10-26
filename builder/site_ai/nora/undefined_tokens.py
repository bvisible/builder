# //// Neoffice — added file (no upstream equivalent): a token the writer invented is replaced by the one it meant.
"""The writer is given the handles of the site (`var(--<prefix>-primary)`, `-secondary`, `-background`, `-text`, `-accent`) and, now and then,
writes one that does not exist: `var(--<prefix>-tint)` for the tinted band of a page (2026-10-26: the services page of a live site, two
sections). The browser drops a declaration whose variable is undefined, so the band painted nothing, the page showed through and the rhythm of
grounds the writer had planned was gone, with no error anywhere. Here every `var(--<prefix>-name)` of a page that no token of the site
defines is replaced by the handle of what it meant: a tinted ground becomes the tint the recipes use (the brand at 8 %), a dark one the
primary, an ink the text, a pale ink the background. A variable that carries its own fallback, and one that is not the site's, is left alone."""

import re

from builder.site_ai.nora.contrast import parse_color

STYLE_KEYS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
GROUND_KEYS = ("backgroundColor", "background")
INK_KEYS = ("color", "borderColor", "borderTopColor", "borderBottomColor", "borderLeftColor", "borderRightColor", "outlineColor", "fill", "stroke", "caretColor")

DEEP = re.compile(r"dark|deep|strong|bold|primary|brand|main|night|ink")
PALE_INK = re.compile(r"light|white|inverse|on-dark|reverse|pale")
ACCENT = re.compile(r"accent|highlight|pop|signature")
BRAND_INK = re.compile(r"brand|primary|main")


def _walk(blocks: list):
	stack = list(blocks or [])
	while stack:
		block = stack.pop()
		if isinstance(block, dict):
			yield block
			stack.extend(block.get("children") or [])


def _tint(tokens: dict, prefix: str) -> str:
	"""The tint of the brand the recipes use (recipes.Look.tint): the primary at 8 %."""
	colour = parse_color(tokens.get(f"{prefix}-primary") or tokens.get(f"{prefix}-secondary"), tokens)
	if colour is None:
		return "rgba(0, 0, 0, 0.04)"
	return f"rgba({colour[0]:.0f}, {colour[1]:.0f}, {colour[2]:.0f}, 0.08)"


def _handle(tokens: dict, prefix: str, *names: str) -> str:
	for name in names:
		if f"{prefix}-{name}" in tokens:
			return f"var(--{prefix}-{name})"
	return ""


def _replacement(key: str, name: str, tokens: dict, prefix: str) -> str:
	"""What the variable `name` (without its prefix) stood for, as the value of the style `key`; "" when nothing can be told."""
	if key in GROUND_KEYS:
		if DEEP.search(name) and not re.search(r"tint|soft|light|pale|subtle|surface|muted|alt|bg|background", name):
			return _handle(tokens, prefix, "primary", "text")
		return _tint(tokens, prefix)
	if key in INK_KEYS:
		if ACCENT.search(name):
			return _handle(tokens, prefix, "accent", "primary")
		if PALE_INK.search(name):
			return _handle(tokens, prefix, "background")
		if BRAND_INK.search(name):
			return _handle(tokens, prefix, "primary", "text")
		return _handle(tokens, prefix, "text")
	return ""


def repair_undefined_tokens(blocks: list, tokens: dict, prefix: str) -> list[str]:
	"""Replace, in place, every `var(--<prefix>-name)` of the page that no token of the site defines. `tokens` holds every token of the site
	by name. Returns one line per replacement."""
	if not prefix or not tokens:
		return []
	pattern = re.compile(r"var\(\s*--(" + re.escape(prefix) + r"-[A-Za-z0-9_-]+)\s*\)")
	edits = []
	for block in _walk(blocks):
		for group in STYLE_KEYS:
			styles = block.get(group)
			if not isinstance(styles, dict):
				continue
			for key, value in list(styles.items()):
				if not isinstance(value, str) or "var(--" not in value:
					continue

				def swap(found: re.Match) -> str:
					if found.group(1) in tokens:
						return found.group(0)
					wanted = _replacement(key, found.group(1)[len(prefix) + 1 :], tokens, prefix)
					if wanted:
						edits.append(f"{key}: {found.group(1)} -> {wanted}")
					return wanted or found.group(0)

				styles[key] = pattern.sub(swap, value)
	return edits
