# //// Neoffice — added file (no upstream equivalent): every picture of a generated page has an alt text.
"""A picture with no alt text says nothing to a person who cannot see it, and an accessible site is part of a lawful one (the Swiss
Federal Act on Equality for People with Disabilities, WCAG 2.1 level A, success criterion 1.1.1). The writer is asked for a
descriptive alt on every photograph and forgets it on some (an empty one, a file name, the word "image"), and a model cannot be
trusted to remember on all of them.

After the page is written, every `img` that has no usable alt gets one, from what the page says around it: the heading of the card
or of the section it sits in, else the title of the page, else the name of the site. A logo is the name of the site. A picture the
writer marked decorative, or an icon (an svg with an empty alt), keeps its empty alt: that is the right alt for it.

No model is called here. An alt this pass writes is a floor, not a description; the writer's own always wins."""

import re

TAG = re.compile(r"<[^>]+>")
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# an alt that is not one: a file name, a counter, the word "image", a slot the writer did not fill, an address
POOR = re.compile(r"^(?:img|image|photo|picture|pic|placeholder|untitled|dsc|screenshot|banner|hero|bg|background|slide)[\s_\-.]*\d*$", re.I)
FILE_NAME = re.compile(r"\.(?:jpe?g|png|webp|gif|avif|svg)\b", re.I)
MAX_ALT = 125


def _text(block: dict) -> str:
	return " ".join(TAG.sub(" ", str(block.get("innerHTML") or "")).split())


def is_poor(alt) -> bool:
	"""Whether an alt is missing or says nothing: absent, blank, a file name, a counter, an unfilled slot, an address."""
	if alt is None:
		return True
	text = str(alt).strip()
	if len(text) < 3:
		return True
	return bool(POOR.match(text) or FILE_NAME.search(text) or text.startswith(("WRITE ", "http", "//", "data:")) or "placehold" in text.lower())


def _src(block: dict) -> str:
	attrs = block.get("attributes") or {}
	return str(attrs.get("src") or "")


def is_decorative(block: dict) -> bool:
	"""A picture whose empty alt is the right one: marked so by the writer, or an icon (an svg)."""
	attrs = block.get("attributes") or {}
	if str(attrs.get("aria-hidden") or "").lower() == "true" or str(attrs.get("role") or "").lower() in ("presentation", "none"):
		return True
	src = _src(block).split("?")[0].lower()
	return src.endswith(".svg") or src.startswith("data:image/svg")


def _is_logo(block: dict) -> bool:
	hint = " ".join([_src(block), str(block.get("blockName") or ""), " ".join(block.get("classes") or [])]).lower()
	return "logo" in hint


def _headings_in(block: dict) -> list[str]:
	found: list[str] = []
	stack = [block]
	while stack:
		node = stack.pop(0)
		if not isinstance(node, dict):
			continue
		if str(node.get("element") or "").lower() in HEADINGS and _text(node):
			found.append(_text(node))
		stack = list(node.get("children") or []) + stack
	return found


def _cut(text: str) -> str:
	text = " ".join(str(text).split())
	if len(text) <= MAX_ALT:
		return text
	return text[:MAX_ALT].rsplit(" ", 1)[0].rstrip(" ,;:-")


def alt_from_context(ancestors: list[dict], page_title: str, site_name: str) -> str:
	"""The alt for a picture: the single heading of the nearest ancestor that has one, else the page's title, else the site's name."""
	for ancestor in reversed(ancestors):
		headings = _headings_in(ancestor)
		if len(headings) == 1:
			return _cut(headings[0])
		if len(headings) > 1:
			break
	return _cut(page_title or site_name or "")


def ensure_alts(blocks: list, page_title: str, site_name: str) -> list[str]:
	"""Gives every picture of the page a usable alt; returns what it wrote, as "src: alt"."""
	edits: list[str] = []

	def visit(block: dict, ancestors: list[dict]) -> None:
		if not isinstance(block, dict):
			return
		if str(block.get("element") or "").lower() == "img":
			attrs = block.setdefault("attributes", {}) if isinstance(block.get("attributes") or {}, dict) else {}
			alt = attrs.get("alt")
			if is_poor(alt) and not (is_decorative(block) and (alt is None or not str(alt).strip())):
				value = _cut(site_name) if _is_logo(block) else alt_from_context(ancestors, page_title, site_name)
				if value:
					attrs["alt"] = value
					edits.append(f"{_src(block).rsplit('/', 1)[-1][:40] or 'image'}: {value[:60]}")
			elif alt is None:
				attrs["alt"] = ""
		for child in block.get("children") or []:
			visit(child, [*ancestors, block])

	for root in blocks or []:
		visit(root, [])
	return edits


def pictures_without_alt(blocks: list) -> list[str]:
	"""The pictures of a page that would still read as nothing: used by the tests and by the checks."""
	missing: list[str] = []
	stack = list(blocks or [])
	while stack:
		block = stack.pop()
		if not isinstance(block, dict):
			continue
		if str(block.get("element") or "").lower() == "img":
			attrs = block.get("attributes") or {}
			alt = attrs.get("alt")
			if alt is None or (is_poor(alt) and not (is_decorative(block) and not str(alt or "").strip())):
				missing.append(_src(block) or "?")
		stack.extend(block.get("children") or [])
	return missing
