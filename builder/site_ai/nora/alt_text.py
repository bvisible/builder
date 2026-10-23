# //// Neoffice — added file (no upstream equivalent): every picture of a generated page has an alt text.
"""A picture with no alt text says nothing to a person who cannot see it, and an accessible site is part of a lawful one (the Swiss
Federal Act on Equality for People with Disabilities, WCAG 2.1 level A, success criterion 1.1.1). The writer is asked for a
descriptive alt on every photograph and forgets it on some (an empty one, a file name, the word "image"), and a model cannot be
trusted to remember on all of them.

After the page is written, every `img` that has no usable alt gets one, from what the page says around it: the heading of the card
or of the section it sits in, else the title of the page, else the name of the site. A logo is the name of the site. A picture the
writer marked decorative, or an icon (an svg with an empty alt), keeps its empty alt: that is the right alt for it.

A picture of a repeated card is bound to its data (`dynamicValues`: its src comes from the item): its alt cannot be one text for every
card. It is bound to the same field as the heading of its card (the title of the item) when the heading is bound too, so each card's
picture is described by its own title; an alt the writer bound itself is left alone.

No model is called here. An alt this pass writes is a floor, not a description; the writer's own always wins."""

import re

TAG = re.compile(r"<[^>]+>")
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# an alt that is not one: a file name, a counter, the word "image", a slot the writer did not fill, an address
POOR = re.compile(r"^(?:img|image|photo|picture|pic|placeholder|untitled|dsc|screenshot|banner|hero|bg|background|slide)[\s_\-.]*\d*$", re.I)
FILE_NAME = re.compile(r"\.(?:jpe?g|png|webp|gif|avif|svg)\b", re.I)
MAX_ALT = 125


BREAK = re.compile(r"<br\s*/?>", re.I)


def _text(block: dict) -> str:
	"""The words of a block: a line break is a space, an inline tag is nothing (a heading "Nos <em>spécialités</em>." reads "Nos spécialités.",
	not "Nos spécialités ." as it did on the first real build, 2026-10-23)."""
	return " ".join(TAG.sub("", BREAK.sub(" ", str(block.get("innerHTML") or ""))).split())


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


def _bound(block: dict, prop: str) -> bool:
	"""Whether a block's property is bound to the data of a repeated item (dynamicValues)."""
	return any(isinstance(d, dict) and d.get("property") == prop for d in block.get("dynamicValues") or [])


def _bound_key(block: dict, prop: str) -> str:
	return next((str(d.get("key") or "") for d in block.get("dynamicValues") or [] if isinstance(d, dict) and d.get("property") == prop), "")


def _headings_in(block: dict) -> list[dict]:
	"""The headings below a block (itself included): {"text": the words} or {"key": the data field it shows} when it is bound."""
	found: list[dict] = []
	stack = [block]
	while stack:
		node = stack.pop(0)
		if not isinstance(node, dict):
			continue
		if str(node.get("element") or "").lower() in HEADINGS:
			if _text(node):
				found.append({"text": _text(node)})
			elif _bound_key(node, "innerHTML"):
				found.append({"key": _bound_key(node, "innerHTML")})
		stack = list(node.get("children") or []) + stack
	return found


def _cut(text: str) -> str:
	text = " ".join(str(text).split())
	if len(text) <= MAX_ALT:
		return text
	return text[:MAX_ALT].rsplit(" ", 1)[0].rstrip(" ,;:-")


def heading_of(ancestors: list[dict]) -> dict | None:
	"""The single heading of the nearest ancestor that has one: {"text": ...} or {"key": ...}; None when the nearest ancestor with
	headings has several (a section of many cards) or none has one."""
	for ancestor in reversed(ancestors):
		headings = _headings_in(ancestor)
		if len(headings) == 1:
			return headings[0]
		if len(headings) > 1:
			break
	return None


def alt_from_context(ancestors: list[dict], page_title: str, site_name: str) -> str:
	"""The alt for a picture: the single heading of the nearest ancestor that has one, else the page's title, else the site's name."""
	heading = heading_of(ancestors)
	if heading and heading.get("text"):
		return _cut(heading["text"])
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
			if _bound(block, "alt"):
				pass  # the writer bound it to the item's own field
			elif is_poor(alt) and not (is_decorative(block) and (alt is None or not str(alt).strip())):
				heading = heading_of(ancestors)
				if _bound(block, "src") and heading and heading.get("key"):
					# a picture of a repeated card: described by the title of its own item
					block.setdefault("dynamicValues", []).append({"key": heading["key"], "property": "alt", "type": "attribute"})
					attrs["alt"] = ""
					edits.append(f"{_src(block).rsplit('/', 1)[-1][:40] or 'bound image'}: bound to {heading['key']}")
				else:
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
			if _bound(block, "alt"):
				continue
			if alt is None or (is_poor(alt) and not (is_decorative(block) and not str(alt or "").strip())):
				missing.append(_src(block) or "?")
		stack.extend(block.get("children") or [])
	return missing
