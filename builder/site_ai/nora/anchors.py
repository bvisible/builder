# //// Neoffice — added file (no upstream equivalent): a category tile leads to its own panel.
"""A category tile leads to its category, not to the top of the page that lists them all.

A home names its categories in tiles (Snow, Street, Water...), and every tile led to the
top of the page that lists what the site offers, where the visitor had to find the panel
again (2026-09-13). The listing page's panel of each category gets an anchor, the
category's slug as its id, and each link to the listing page that names one category
points at it: /brands#snow. On the listing page itself, the same link scrolls in place.
"""

import html
import re
import unicodedata

HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
PICTURE_BINDINGS = {"src", "backgroundImage", "background-image", "background"}
DATA_ROUTE_KEYS = ("route", "href", "url", "link")
# the site's header may be sticky: an anchored panel stops below it, not under it
SCROLL_MARGIN = "calc(var(--header-height, 72px) + 16px)"


def category_slug(name: str) -> str:
	text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
	return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def anchor_category_panels(blocks: list, categories: list[str]) -> list[str]:
	"""Gives the panel of each category an id, the category's slug: the nearest block around
	the category's heading that also holds a picture and no other category, else the
	heading's own block. A block that already has an id keeps it, and the slug goes on the
	heading instead. Returns what it anchored."""
	edits: list[str] = []
	for name in categories or []:
		slug = category_slug(name)
		if not slug:
			continue
		chain = _heading_chain(blocks, name)
		if not chain:
			continue
		others = [c for c in categories if c != name]
		heading = chain[-1]
		panel = next(
			(b for b in reversed(chain[:-1]) if _has_picture(b) and not _one_of(_text(b), others)),
			heading,
		)
		for target in (panel, heading):
			attributes = target.get("attributes") or {}
			if attributes.get("id"):
				if attributes["id"] == slug:
					break
				continue
			target["attributes"] = {**attributes, "id": slug}
			target["baseStyles"] = {**(target.get("baseStyles") or {}), "scrollMarginTop": SCROLL_MARGIN}
			edits.append(f"{name}: #{slug} on the {target.get('element') or 'div'}")
			break
	return edits


def anchor_category_links(blocks: list, listing: str, categories: list[str]) -> list[str]:
	"""Points each link to the listing page that names one category, by its own words or by
	the tile around it, at that category's panel: listing#slug. A link naming no category or
	several, or already carrying an anchor, is left alone. Returns what it changed."""
	path = (listing or "").rstrip("/") or "/"
	edits: list[str] = []
	if not listing:
		return edits

	def walk(block: dict, ancestors: list[dict]) -> None:
		attributes = block.get("attributes") or {}
		href = str(attributes.get("href") or "")
		if href.startswith("/") and "#" not in href and (href.split("?", 1)[0].rstrip("/") or "/") == path:
			# the link's own words first, then the tile around it (two levels up at most)
			name = _one_category(_text(block), categories)
			for ancestor in reversed(ancestors[-2:]):
				name = name or _one_category(_text(ancestor), categories)
			if name:
				target = f"{href}#{category_slug(name)}"
				block["attributes"] = {**attributes, "href": target}
				edits.append(f"'{_text(block)[:40]}' {href} -> {target}")
		for child in block.get("children") or []:
			if isinstance(child, dict):
				walk(child, [*ancestors, block])

	for block in blocks or []:
		if isinstance(block, dict):
			walk(block, [])
	return edits


def anchor_category_data_links(
	script: str, listing: str, categories: list[str], extra_keys=()
) -> tuple[str, list[str]]:
	"""The same for the routes a page's data script hands its repeated tiles: an entry that
	names one category ("title": "Snow") and routes to the listing page gets the anchor.
	`extra_keys` adds the keys the page binds to an href (a tile linked through "slug")."""
	if not script or not listing:
		return script, []
	path = listing.rstrip("/") or "/"
	names = "|".join(re.escape(k) for k in sorted(set(DATA_ROUTE_KEYS) | set(extra_keys or ())))
	route = re.compile(rf"""(["'](?:{names})["']\s*:\s*["'])(/[^"'#?\s]*)(["'])""")
	edits: list[str] = []

	def entry(m: re.Match) -> str:
		body = m.group(0)
		named = [c for c in categories if re.search(rf"""["']{re.escape(c)}["']""", body, re.I)]
		if len(named) != 1:
			return body
		slug = category_slug(named[0])

		def swap(r: re.Match) -> str:
			if (r.group(2).rstrip("/") or "/") != path:
				return r.group(0)
			edits.append(f"{named[0]}: {r.group(2)} -> {r.group(2)}#{slug}")
			return f"{r.group(1)}{r.group(2)}#{slug}{r.group(3)}"

		return route.sub(swap, body)

	return re.sub(r"\{[^{}]*\}", entry, script), edits


def _heading_chain(blocks: list, name: str) -> list[dict]:
	"""The blocks from the top of the page down to the category's heading: a heading element
	whose text is the category's name, else any text block that says exactly that."""
	wanted = name.strip().lower()
	best: list[dict] = []

	def walk(block: dict, chain: list[dict]) -> bool:
		nonlocal best
		chain = [*chain, block]
		own = _plain(block.get("innerHTML")).lower()
		if own == wanted and not block.get("children"):
			if str(block.get("element") or "").lower() in HEADINGS:
				best = chain
				return True
			best = best or chain
		for child in block.get("children") or []:
			if isinstance(child, dict) and walk(child, chain):
				return True
		return False

	for block in blocks or []:
		if isinstance(block, dict) and walk(block, []):
			break
	return best


def _has_picture(block: dict) -> bool:
	for node in _subtree(block):
		bound = {str(d.get("property") or "") for d in node.get("dynamicValues") or [] if isinstance(d, dict)}
		styles = node.get("baseStyles") or {}
		if (
			str(node.get("element") or "").lower() == "img"
			or bound & PICTURE_BINDINGS
			or "url(" in str(styles.get("backgroundImage") or "")
		):
			return True
	return False


def _one_category(text: str, categories: list[str]) -> str | None:
	named = _one_of(text, categories)
	return named[0] if len(named) == 1 else None


def _one_of(text: str, categories: list[str]) -> list[str]:
	return [
		c
		for c in categories or []
		if c.strip() and re.search(rf"(?<![\w-]){re.escape(c.strip())}(?![\w-])", text or "", re.I)
	]


def _text(block: dict) -> str:
	return " ".join(t for t in (_plain(node.get("innerHTML")) for node in _subtree(block)) if t)


def _plain(text) -> str:
	return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text if isinstance(text, str) else "")).split())


def _subtree(block: dict):
	yield block
	for child in block.get("children") or []:
		if isinstance(child, dict):
			yield from _subtree(child)
