# //// Neoffice — added file (no upstream equivalent): what a turn of Nora changed on a site, said page by page.
"""What one turn of Nora's site conversation changed, page by page, for the cards under her answer.

The cards are computed from the pages themselves, not from the tool calls: the draft a page had when the turn
opened it, against the draft it has when the turn ends. Whatever path an edit took (a block tool, a page
rewritten by generate_site, a component synced into the page), the card says what the visitor will see change,
in the words a client uses: the section, and whether its text, a photo or its look changed.

Nothing here writes. `page_card` and `section_changes` are pure (the tests feed them block trees); `page_state`
and `page_links` read the page and its site.
"""

from __future__ import annotations

import html
import json
import re

import frappe
from frappe import _

# The kinds of change a section can carry, in the order a card names them.
KINDS = ("added", "removed", "text", "photo", "look", "content")
# Elements whose text names a section better than its technical name.
HEADINGS = ("h1", "h2", "h3", "h4")
STYLE_KEYS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
IMAGE_STYLE_KEYS = ("backgroundImage", "background")
LABEL_LENGTH = 48
TAG = re.compile(r"<[^>]+>")


def parse_blocks(value) -> dict | None:
	"""The root block of a page's blocks (a JSON list holding the root, or the root itself), else None."""
	if not value:
		return None
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except ValueError:
			return None
	if isinstance(value, list):
		value = value[0] if value else None
	return value if isinstance(value, dict) else None


def plain_text(markup) -> str:
	text = html.unescape(TAG.sub(" ", str(markup or "")))
	return " ".join(text.split())


def flatten(block: dict) -> dict[str, dict]:
	"""Every block under `block` (itself included) by its id, each without its children."""
	out: dict[str, dict] = {}
	stack = [block]
	while stack:
		node = stack.pop()
		if not isinstance(node, dict):
			continue
		children = node.get("children") or []
		block_id = node.get("blockId")
		if block_id:
			out[block_id] = {k: v for k, v in node.items() if k != "children"}
		stack.extend(reversed(children))
	return out


def section_label(section: dict) -> str:
	"""How a client names a section: its first heading, else its name, else its first words."""
	first_text = ""
	stack = [section]
	while stack:
		node = stack.pop(0)
		if not isinstance(node, dict):
			continue
		text = plain_text(node.get("innerHTML"))
		if text and (node.get("element") or "").lower() in HEADINGS:
			return clip(text)
		if text and not first_text:
			first_text = text
		stack.extend(node.get("children") or [])
	name = (section.get("blockName") or "").strip()
	if name and not name.startswith("<"):
		return clip(name)
	return clip(first_text) if first_text else _("A section")


def clip(text: str) -> str:
	return text if len(text) <= LABEL_LENGTH else text[: LABEL_LENGTH - 1].rstrip() + "…"


def has_image(block: dict) -> bool:
	if (block.get("element") or "").lower() in ("img", "picture", "video"):
		return True
	for key in STYLE_KEYS:
		styles = block.get(key) or {}
		if isinstance(styles, dict) and any(styles.get(k) for k in IMAGE_STYLE_KEYS):
			return True
	return False


def image_of(block: dict) -> tuple:
	attrs = block.get("attributes") or {}
	images = [attrs.get("src"), attrs.get("srcset"), attrs.get("poster")]
	for key in STYLE_KEYS:
		styles = block.get(key) or {}
		if isinstance(styles, dict):
			images.extend(styles.get(k) for k in IMAGE_STYLE_KEYS)
	return tuple(str(v or "") for v in images)


def block_kinds(before: dict, after: dict) -> set[str]:
	"""What changed in one block, in the card's words."""
	kinds: set[str] = set()
	if plain_text(before.get("innerHTML")) != plain_text(after.get("innerHTML")):
		kinds.add("text")
	if (has_image(before) or has_image(after)) and image_of(before) != image_of(after):
		kinds.add("photo")
	if any((before.get(k) or {}) != (after.get(k) or {}) for k in STYLE_KEYS) and "photo" not in kinds:
		kinds.add("look")
	if not kinds and before != after:
		kinds.add("content")
	return kinds


def section_changes(before_root: dict | None, after_root: dict | None) -> list[dict]:
	"""The sections (the root's children) that changed, in the page's order:
	[{block_id, label, kinds: [...]}]. A section that left the page comes last."""
	before_sections = {
		s.get("blockId"): s for s in (before_root or {}).get("children") or [] if isinstance(s, dict)
	}
	after_sections = [s for s in (after_root or {}).get("children") or [] if isinstance(s, dict)]
	out: list[dict] = []
	for section in after_sections:
		block_id = section.get("blockId")
		old = before_sections.pop(block_id, None)
		if old is None:
			out.append({"block_id": block_id, "label": section_label(section), "kinds": ["added"]})
			continue
		old_blocks, new_blocks = flatten(old), flatten(section)
		kinds: set[str] = set()
		for bid, block in new_blocks.items():
			previous = old_blocks.get(bid)
			kinds |= {"content"} if previous is None else block_kinds(previous, block)
		if set(old_blocks) - set(new_blocks):
			kinds.add("content")
		if kinds:
			out.append({"block_id": block_id, "label": section_label(section), "kinds": ordered(kinds)})
	for section in before_sections.values():
		out.append({"block_id": None, "label": section_label(section), "kinds": ["removed"]})
	return out


def ordered(kinds) -> list[str]:
	kinds = set(kinds)
	if "content" in kinds and len(kinds) > 1:
		kinds.discard("content")
	return [k for k in KINDS if k in kinds]


def page_state(doc) -> str:
	"""`draft`: changes the visitors do not see yet; `published`: what is saved is online; `offline`: never published."""
	draft = doc.get("draft_blocks")
	if draft and draft != doc.get("blocks"):
		return "draft"
	return "published" if doc.get("published") else "offline"


def visitor_route(route: str | None) -> str:
	route = (route or "").strip().strip("/")
	return "/" if route in ("", "home", "index") else f"/{route}"


def site_origin(profile: str | None) -> str:
	"""The address of the site a page is served on: its profile's own domain, else this instance."""
	domain = ""
	if profile and frappe.db.exists("DocType", "Website Profile"):
		domain = (frappe.db.get_value("Website Profile", profile, "primary_domain") or "").strip()
	if domain:
		domain = re.sub(r"^https?://", "", domain).rstrip("/")
		return f"https://{domain}"
	return frappe.utils.get_url().rstrip("/")


def page_links(doc, profile: str | None, first_block: str | None = None) -> dict:
	"""Where a card leads, each in a new tab: the page as visitors see it (online), its draft (preview), the editor
	on the page or on its first changed section."""
	editor_root = "/" + (frappe.conf.builder_path or "builder") + "/page/" + doc.name
	links = {
		"preview": editor_root + "/preview",
		"editor": editor_root + (f"?block={first_block}" if first_block else ""),
	}
	if doc.get("published"):
		links["online"] = site_origin(profile) + visitor_route(doc.get("route"))
	return links


def page_card(page_id: str, before_blocks, profile: str | None, rebuilt: bool = False) -> dict | None:
	"""The card of one page: None when nothing a visitor sees changed on it."""
	if not frappe.db.exists("Builder Page", page_id):
		return None
	doc = frappe.get_doc("Builder Page", page_id)
	after_root = parse_blocks(doc.get("draft_blocks") or doc.get("blocks"))
	before_root = parse_blocks(before_blocks)
	new_page = before_root is None or rebuilt
	sections = [] if new_page else section_changes(before_root, after_root)
	if not new_page and not sections:
		return None
	first = next((s["block_id"] for s in sections if s.get("block_id")), None)
	return {
		"kind": "page",
		"page": doc.name,
		"title": doc.get("page_title") or doc.name,
		"route": visitor_route(doc.get("route")),
		"new": bool(new_page),
		"sections": sections,
		"state": page_state(doc),
		"links": page_links(doc, profile, first),
	}


def site_card(kind: str, profile: str | None) -> dict:
	"""A change that is not one page's: the header and footer, the site's colours and type."""
	return {
		"kind": kind,
		"state": "site",
		"links": {"online": site_origin(profile) + "/"},
	}
