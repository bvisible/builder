# //// Neoffice — added file (no upstream equivalent): an include with nothing to show on the
# //// site is not drawn, nor the short heading that announces it (2026-09-13).
"""Includes that draw the site's own records, and what a page does when the record is empty.

Four includes the site generator offers show the site's data: the map shows the business
address, the opening hours come from the shop's settings, the team and the milestones from
About Us Settings. With the record empty, the include draws nothing (or, for a signed-in
user, an editor's hint) and the page keeps what was written around it: a "Hours" label over
an empty space, a grey frame where the map would be, a "Key figures" heading over nothing
(the contact and about pages of a reseller site, 2026-09-13).

The generator no longer offers such an include (site_builder.available_includes asks
include_has_data), but a page written earlier, or by hand, still carries it, and a record can
be emptied after the page is written. So the renderer drops it as well (prune_for_render, in
BuilderPage.get_context): each bare include whose record is empty, the short text-only
blocks right before it that announce it, and every block the removal leaves with nothing to
show. An include not listed in DATA_CHECKS, or one written with parameters, draws as before.
"""

import copy
import html
import json
import re

import frappe

# a block whose whole text is one include tag, optionally preceded by the {% set %} parameters
# that configure it. The parameters are a composition choice — a title, a limit — but what the
# include has to SHOW is not, and a block that is nothing but an include has nothing else to say.
# //// Neoffice — the {% set %} prefix was added 2026-09-15: the generator offers the shop's
# //// carousels with their title and their limit set, so the old bare-only rule left every one of
# //// them in place, and a home kept "Our products" over an empty strip.
BARE_INCLUDE = re.compile(
	r"^\s*(?:\{%-?\s*set\s+[^%]*?-?%\}\s*)*\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}\s*$"
)

# a heading group announces what follows it: a kicker, a title, a one-line lede. A longer
# text says something of its own and stays when the include under it goes.
ANNOUNCEMENT_MAX_CHARS = 140

MEDIA_ELEMENTS = {"img", "picture", "video", "audio", "iframe", "svg", "canvas", "object", "embed"}
ACTIVE_ELEMENTS = {"a", "button", "form", "input", "select", "textarea"}
ACTIVE_MARKUP = re.compile(
	r"<\s*(img|picture|video|audio|iframe|svg|canvas|object|embed|a|button|form|input|select|textarea)\b",
	re.I,
)
STYLE_FIELDS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
# an inline icon hidden from assistive technology is an ornament, not content
DECORATIVE_SVG = re.compile(r"<svg\b[^>]*\baria-hidden\s*=\s*['\"]?true['\"]?[^>]*>.*?</svg>", re.I | re.S)


def site_has_address(profile: str | None = None) -> bool:
	"""Whether the site's business has an address for the map to show."""
	from builder.api import get_site_contact_context

	return bool(get_site_contact_context(profile).get("address"))


def opening_hours_configured() -> bool:
	"""Whether the shop has opening hours typed."""
	from webshop.webshop.utils.store_hours import webshop_opening_hours

	return bool(webshop_opening_hours())


def about_us_rows(field: str) -> bool:
	"""Whether About Us Settings has rows in `field` (team_members, company_history): the test
	the team and timeline includes make before drawing anything."""
	if not frappe.db.exists("About Us Settings", "About Us Settings"):
		return False
	return bool(frappe.get_cached_doc("About Us Settings").get(field))


# what a carousel fetches, and how many of them must carry a picture for it to be worth drawing
CAROUSEL_FETCH = 8
CAROUSEL_MIN_PICTURED = 3


def shop_has_pictured(doctype: str, image_field: str, filters: dict | None = None, among: int = 0) -> bool:
	"""Whether the shop has enough pictured records of `doctype` for a carousel to show something.

	//// Neoffice — added 2026-09-15: the carousels are offered with hide_without_image, so a shop
	whose articles have no photograph draws an empty strip under its heading. Before that switch it
	drew grey squares with the initials of each name ("VW", "VS", "VD") across a home.

	//// Neoffice — `among` added the same day: asking "does ANY article have a picture?" was the
	wrong question. A catalogue of 380 articles had 9 pictured, none of them among the eight newest
	— which is exactly the set the carousel fetches (sort_by creation desc, carousel_limit) — so the
	check passed and the home still drew "Our products" over an empty strip. Asked of the same set
	the carousel will fetch, and of at least CAROUSEL_MIN_PICTURED of them, the answer matches what
	a visitor will see."""
	if not frappe.db.exists("DocType", doctype):
		return False
	conditions = dict(filters or {})
	if not among:
		conditions[image_field] = ("is", "set")
		return bool(frappe.db.count(doctype, conditions))
	rows = frappe.get_all(doctype, filters=conditions, fields=[image_field], order_by="creation desc", limit=among)
	return sum(1 for row in rows if row.get(image_field)) >= min(CAROUSEL_MIN_PICTURED, among)


# //// Neoffice ▼▼▼ — named checks, so the component catalogue can point at them by name
# //// (site_ai/components.py, data_check). Each takes the profile and ignores it when the record
# //// it reads is instance-wide.
def has_pictured_products(profile=None) -> bool:
	"""Whether the products a carousel fetches carry photographs (see shop_has_pictured)."""
	return shop_has_pictured("Website Item", "website_image", {"published": 1}, among=CAROUSEL_FETCH)


def has_pictured_brands(profile=None) -> bool:
	return shop_has_pictured("Brand", "image")


def has_team_members(profile=None) -> bool:
	return about_us_rows("team_members")


def has_company_history(profile=None) -> bool:
	return about_us_rows("company_history")


# //// Neoffice — a listing with ONE card is a hole (2026-09-17): a home showed "Actualités de
# //// l'agence" over a single news card and a huge empty area, and the judge refused it. A
# //// listing is offered when there is enough to list.
LISTING_MIN_POSTS = 3


def has_blog_posts(profile=None) -> bool:
	"""Whether the site has enough published blog posts for a listing to look like one."""
	if not frappe.db.exists("DocType", "Blog Post"):
		return False
	try:
		return int(frappe.db.count("Blog Post", {"published": 1}) or 0) >= LISTING_MIN_POSTS
	except Exception:
		return False
# //// Neoffice ▲▲▲


# include file name -> whether it has something to show on the site of `profile`
DATA_CHECKS = {
	# //// Neoffice — the same named checks the component catalogue points at, so a component
	# //// and the renderer's pruning can never disagree about what "nothing to show" means
	# //// Neoffice — the checks are called through a lambda, not bound here: naming the function
	# //// object in the dict freezes the one that existed at import, so a later override — or a
	# //// test that patches the module — silently does not apply.
	"google_map.html": lambda profile: site_has_address(profile),
	"opening_hours.html": lambda profile: opening_hours_configured(),
	"team_grid.html": lambda profile: has_team_members(profile),
	"company_timeline.html": lambda profile: has_company_history(profile),
	"product_carousel.html": lambda profile: has_pictured_products(profile),
	"brand_carousel.html": lambda profile: has_pictured_brands(profile),
	"blog_listing.html": lambda profile: has_blog_posts(profile),
	"contact_info.html": lambda profile: site_has_address(profile),
}


def include_has_data(path: str, profile: str | None = None) -> bool | None:
	"""Whether the include at `path` has something to show on this site: True or False for an
	include listed in DATA_CHECKS, None for any other. A check that fails counts as nothing
	to show: the app it reads is absent or broken, and the include would fail the same way."""
	check = DATA_CHECKS.get(str(path or "").rsplit("/", 1)[-1])
	if not check:
		return None
	try:
		return bool(check(profile))
	except Exception:
		return False


def prune_for_render(blocks, profile: str | None = None):
	"""The blocks a page renders, without the includes that have nothing to show on this site
	(prune_empty_includes). `blocks` as stored (JSON text) or parsed; returned untouched when
	nothing goes, and on any error: this runs on every page view and must never be the reason
	a page fails."""
	if not blocks or (isinstance(blocks, str) and "include" not in blocks):
		return blocks
	try:
		data = frappe.parse_json(blocks) if isinstance(blocks, str) else copy.deepcopy(blocks)
		checked = {}

		def has_data(path):
			if path not in checked:
				checked[path] = include_has_data(path, profile)
			return checked[path]

		return data if prune_empty_includes(data, has_data) else blocks
	except Exception:
		frappe.log_error("Empty includes: page rendered without pruning", frappe.get_traceback())
		return blocks


def prune_empty_includes(blocks, has_data) -> int:
	"""Removes, in place, each bare include block for which has_data(path) is False, the short
	text-only blocks right before it that announce it (ANNOUNCEMENT_MAX_CHARS together, and
	only when nothing with content follows it in the same parent: a heading over more than
	the include, such as key figures the page's data fills, stays), and every block the
	removal leaves with nothing to show. `blocks` is a block or a list of blocks; a top-level
	block is never removed. Returns how many includes went."""
	removed = 0

	def empty_include(block: dict) -> bool:
		text = block.get("innerHTML")
		if block.get("children") or not isinstance(text, str):
			return False
		match = BARE_INCLUDE.match(text)
		return bool(match) and has_data(match.group(1)) is False

	def prune(block: dict) -> bool:
		# prunes the block's children; True when that left the block with nothing to show
		nonlocal removed
		children = block.get("children")
		if not isinstance(children, list) or not children:
			return False
		kept, dropped = [], False
		for index, child in enumerate(children):
			if not isinstance(child, dict):
				kept.append(child)
				continue
			if empty_include(child):
				removed += 1
			elif not prune(child):
				kept.append(child)
				continue
			# the child goes (an empty include, or a block its own pruning emptied), and so
			# does what announced it, unless that also heads the content after it
			dropped = True
			if not any(_carries_content(c) for c in children[index + 1 :] if isinstance(c, dict)):
				_drop_announcement(kept)
		if not dropped:
			return False
		block["children"] = kept
		return not kept and not _shows_something(block)

	for root in blocks if isinstance(blocks, list) else [blocks]:
		if isinstance(root, dict):
			prune(root)
	return removed


def _drop_announcement(kept: list) -> None:
	# the short text-only blocks right before a removed block announced it
	budget = ANNOUNCEMENT_MAX_CHARS
	while kept and isinstance(kept[-1], dict):
		size = _text_only_size(kept[-1])
		if size is None or size > budget:
			return
		budget -= size
		kept.pop()


def _text_only_size(block: dict) -> int | None:
	"""The length of the text a block and its children show, or None when one of them shows
	more than text: media, a link or a control, a background image, an include, a binding
	(key figures bound to the page's data are content). An ornament hidden from assistive
	technology (an icon marked aria-hidden) is not content and does not count."""
	size = 0
	for node in _content_nodes(block):
		element = str(node.get("element") or "").lower()
		if element in MEDIA_ELEMENTS or element in ACTIVE_ELEMENTS or node.get("dynamicValues"):
			return None
		if any(key in (node.get("attributes") or {}) for key in ("href", "src", "srcset")):
			return None
		if _has_background_image(node):
			return None
		text = DECORATIVE_SVG.sub("", node.get("innerHTML") if isinstance(node.get("innerHTML"), str) else "")
		if "{%" in text or "{{" in text or ACTIVE_MARKUP.search(text):
			return None
		size += len(_plain(text))
	return size


def _carries_content(block: dict) -> bool:
	# text, or values the page's data fills (bound key figures), anywhere in the block; a
	# photo alone does not need the heading above the include
	for node in _content_nodes(block):
		text = node.get("innerHTML") if isinstance(node.get("innerHTML"), str) else ""
		if node.get("dynamicValues") or "{%" in text or "{{" in text or _plain(DECORATIVE_SVG.sub("", text)):
			return True
	return False


def _shows_something(block: dict) -> bool:
	# a block whose children all went may still show its own text, media or background image
	text = block.get("innerHTML") if isinstance(block.get("innerHTML"), str) else ""
	element = str(block.get("element") or "").lower()
	return bool(text.strip()) or element in MEDIA_ELEMENTS or _has_background_image(block)


def _has_background_image(block: dict) -> bool:
	return any("url(" in json.dumps(block.get(field) or {}) for field in STYLE_FIELDS)


def _plain(text) -> str:
	return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text if isinstance(text, str) else "")).split())


def _decorative(block: dict) -> bool:
	# hidden from assistive technology: an ornament (an icon, a rule), not content
	attributes = block.get("attributes")
	return isinstance(attributes, dict) and str(attributes.get("aria-hidden", "")).lower() == "true"


def _content_nodes(block: dict):
	# the block and its children, ornaments left out
	if _decorative(block):
		return
	yield block
	for child in block.get("children") or []:
		if isinstance(child, dict):
			yield from _content_nodes(child)
