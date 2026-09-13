# //// Neoffice — added file (no upstream equivalent): one photo treatment for the whole site.
"""A black-and-white site shows its photographs in black and white, on every page.

The page writer decides one page at a time. On a monochrome site it put
`filter: grayscale(100%)` on the seven photographs of the home and on none of the other
pages, so the client's pictures changed colour from one page to the next (2026-09-12).
The treatment belongs to the site: once the site is monochrome, grayscale_photos() gives
every photograph of a page the filter, whatever the model wrote.
"""

import json
import re

GRAYSCALE = "grayscale(100%)"
# the bindings that carry a picture: an image's source, a block's background
PICTURE_BINDINGS = {"src", "backgroundImage", "background-image", "background"}
STYLE_FIELDS = ("baseStyles", "rawStyles", "mobileStyles", "tabletStyles")
URL = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)")


def grayscale_photos(blocks: list, keep=frozenset()) -> list[str]:
	"""Gives filter: grayscale(100%) to every photograph of the page that does not have it
	yet, nor sits in a block that has: an <img>, a block painted with a background image,
	a block whose picture the page's data binds. A picture listed in `keep` stays in colour
	(the site's own logo may be the one coloured thing on a black-and-white site), and an
	SVG is a drawing, not a photograph. Returns one line per block changed."""
	edits: list[str] = []

	def walk(block, grey: bool) -> None:
		if not isinstance(block, dict):
			return
		grey = grey or _is_grey(block)
		picture = _picture(block)
		if picture is not None and not grey and not _kept(picture, keep):
			styles = dict(block.get("baseStyles") or {})
			current = str(styles.get("filter") or "").strip()
			styles["filter"] = f"{current} {GRAYSCALE}" if current and current != "none" else GRAYSCALE
			block["baseStyles"] = styles
			edits.append(
				f"{block.get('element') or 'div'} {picture or '(bound picture)'}: {styles['filter']}"
			)
			grey = True
		for child in block.get("children") or []:
			walk(child, grey)

	for block in blocks or []:
		walk(block, False)
	return edits


def _is_grey(block: dict) -> bool:
	return any("grayscale" in json.dumps(block.get(field) or {}) for field in STYLE_FIELDS)


def _picture(block: dict) -> str | None:
	"""The picture a block shows: its address, "" when the page's data binds it, None when
	the block shows no picture (a gradient is not one)."""
	bound = {str(d.get("property") or "") for d in block.get("dynamicValues") or [] if isinstance(d, dict)}
	if bound & PICTURE_BINDINGS:
		return ""
	if str(block.get("element") or "").lower() == "img":
		return str((block.get("attributes") or {}).get("src") or "")
	match = URL.search(str((block.get("baseStyles") or {}).get("backgroundImage") or ""))
	return match.group(2) if match else None


def _kept(picture: str, keep) -> bool:
	return bool(picture) and (picture in keep or picture.split("?", 1)[0].lower().endswith(".svg"))
