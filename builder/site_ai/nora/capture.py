# //// Neoffice — added file (no upstream equivalent): a section of a written page, kept as a block of the Builder Hub.
"""A section the generator wrote and the judge accepted is a design worth keeping: the hub's library (hub_blocks.py) grows from what works instead of
from what somebody draws by hand. This module turns one section of a stored page into the block the hub takes (block_format.py), and sends it there
as a DRAFT: a block reaches every site that is generated, so a person reads it in the hub's desk and publishes it (the hub's `publish_block` never
publishes, and never overwrites a block that is published).

What a block may keep of a written section, and what it may not:
- its STRUCTURE and its look are kept: the tags, the grid, the spacing, the classes of the design system (`u-card`, `u-grid`, `u-btn`…);
- every colour and font of the site becomes a TOKEN (`{{primary}}`, `{{font_heading}}`), and what depends on the ground the section sits on
  (its background, its ink, its hairlines) becomes `{{ground.*}}`, so that the block takes the ground the plan gives it on another site;
- every word becomes a SLOT (`WRITE heading: 4 to 8 words`): the length is the one of the original, the words are never carried, a block
  carries nothing of the business it was written for. The same goes for the photographs (`{{photo.N}}`) and the alt of each (the generator's own
  guidance), for the links (`{{cta_href}}`) and for the names of the nodes (only a plain structural word survives);
- a section that cannot be a block is refused with the reason: a live component, an icon, a data binding, a script, a tag the format does not
  know, a photograph set as a background, and too many colours that are not the site's.

Pure Python (no Frappe at import), so that the tests run anywhere."""

import hashlib
import json
import re

from builder.site_ai.nora import block_format
from builder.site_ai.nora import recipes as section_recipes

HANDLE_KEYS = (
	"primary",
	"secondary",
	"background",
	"text",
	"font-heading",
	"font-body",
	"container",
	"gutter",
	"gutter-phone",
)
# the block's token for each handle of the site
TOKEN_OF_HANDLE = {
	"primary": "primary",
	"secondary": "secondary",
	"background": "background",
	"text": "text",
	"font-heading": "font_heading",
	"font-body": "font_body",
	"container": "container",
	"gutter": "gutter",
	"gutter-phone": "gutter_phone",
}
# on each ground, what the section's own surface, ink, hairline and accent are called (they follow the ground the plan gives it)
GROUND_TOKENS = {
	"plain": {
		"background": "ground.background",
		"text": "ground.ink",
		"muted": "ground.muted",
		"hair": "ground.hair",
		"secondary": "ground.accent",
	},
	"tint": {
		"tint": "ground.background",
		"text": "ground.ink",
		"muted": "ground.muted",
		"hair": "ground.hair",
		"secondary": "ground.accent",
	},
	"deep": {
		"deep": "ground.background",
		"ink_on_deep": "ground.ink",
		"deep_muted": "ground.muted",
		"deep_hair": "ground.hair",
		"secondary": "ground.accent",
	},
}
LOOK_VALUES = ("muted", "hair", "tint", "frame", "deep", "ink_on_deep", "deep_muted", "deep_hair")
MAX_LITERAL_COLOURS = 3
REFUSED_KEYS = {
	"extendedFromComponent": "it holds a component",
	"isChildOfComponent": "it holds a component",
	"isRepeaterBlock": "it holds a repeater (data of the site)",
	"dynamicValues": "it holds a data binding",
	"clientScript": "it holds a script",
	"blockClientScript": "it holds a script",
	"referenceBlockId": "it holds a component",
}
ALLOWED_ATTRS = re.compile(r"^(?:role|title|aria-[\w-]+|data-[\w-]+)$")
SAFE_NAME = re.compile(r"^[a-z][a-z0-9-]{0,23}$")
TAG = re.compile(r"<[^>]+>")
ACCENT_MARK = re.compile(r"<(?:em|i|strong|b|span)\b", re.IGNORECASE)
NUMERAL = re.compile(r"^\s*\d{1,3}\s*$")
FIGURE = re.compile(r"^\s*[\d][\d\s.,'’]*\s*[+%a-zA-Z/]{0,4}\s*$")
KIND_BY_NAME = (
	("hero", "hero"),
	("statement", "statement"),
	("intro", "intro"),
	("feature", "feature-grid"),
	("card", "cards"),
	("tile", "photo-tiles"),
	("two-column", "two-column"),
	("product", "product-row"),
	("brand", "brand-row"),
	("story", "story"),
	("step", "steps"),
	("process", "steps"),
	("figure", "figures"),
	("stat", "figures"),
	("testimonial", "testimonials"),
	("quote", "testimonials"),
	("faq", "faq"),
	("team", "team"),
	("pricing", "pricing"),
	("gallery", "gallery"),
	("contact-details", "contact-details"),
	("contact-form", "contact-form"),
	("map", "map"),
	("hours", "hours"),
	("cta", "cta"),
)


class Refused(Exception):
	"""A section that cannot be a block, and why."""


# ---------------------------------------------------------------- the site's own values, as tokens


def prefix_of(blocks) -> str | None:
	"""The token prefix of the site a page was written for (`qm` of `var(--qm-primary)`)."""
	found = re.search(r"var\(--([a-z0-9]+)-primary\)", json.dumps(blocks or []))
	return found.group(1) if found else None


def handles_of(prefix: str) -> dict:
	return {key: f"var(--{prefix}-{key})" for key in HANDLE_KEYS}


def token_pairs(look, ground: str, handles: dict) -> list[tuple[str, str]]:
	"""(value in the site, token of the block), the longest value first so that a longer one is never cut by a shorter. What depends on the
	ground comes first (`{{ground.ink}}` rather than `{{text}}`)."""
	by_role: dict[str, str] = {}
	for key in TOKEN_OF_HANDLE:
		if handles.get(key):
			by_role[key.replace("-", "_")] = handles[key]
	for role in LOOK_VALUES:
		value = getattr(look, role, None)
		if value:
			by_role[role] = value
	grounded = GROUND_TOKENS[ground]
	pairs: list[tuple[str, str]] = []
	seen: set[str] = set()
	# the roles of the ground first, then the handles of the site, then the colours derived from them: of two roles with the same value the first wins
	for role, value in sorted(
		by_role.items(), key=lambda kv: (kv[0] not in grounded, kv[0] in LOOK_VALUES, kv[0])
	):
		if value in seen:
			continue
		seen.add(value)
		token = grounded.get(role) or TOKEN_OF_HANDLE.get(role.replace("_", "-")) or role
		pairs.append((value, token))
	return sorted(pairs, key=lambda p: -len(p[0]))


def ground_of_section(section: dict, look) -> str:
	background = (section.get("baseStyles") or {}).get("backgroundColor")
	if background and background == look.deep:
		return "deep"
	if background and background == look.tint:
		return "tint"
	return "plain"


# ---------------------------------------------------------------- the words, as slots


def _plain(text: str) -> str:
	return " ".join(TAG.sub(" ", text or "").split())


def _range(words: int) -> str:
	low = max(1, round(words * 0.7))
	high = max(low, round(words * 1.3))
	return f"{low} to {high} words" if high > low else f"{low} word" + ("s" if low > 1 else "")


class Words:
	"""Turns the text of a node into the slot that asks for the same thing, from its tag, its style and its length."""

	def __init__(self):
		self.headings = 0
		self.leads = 0

	def slot(self, node: dict, text: str) -> str:
		plain = _plain(text)
		words = len(plain.split())
		el = node.get("el")
		classes = node.get("classes") or []
		style = node.get("style") or {}
		accent = (
			", one accent word"
			if ACCENT_MARK.search(text) and el in {"h1", "h2", "h3", "h4", "h5", "h6"}
			else ""
		)
		if el == "a" and any(c.startswith("u-btn") for c in classes):
			return section_recipes.slot("button", _range(words))
		if el in {"h1", "h2", "h3", "h4", "h5", "h6"}:
			role = "heading" if self.headings == 0 else "item-title"
			self.headings += 1
			return section_recipes.slot(role, _range(words) + accent)
		if FIGURE.match(plain) and any(ch.isdigit() for ch in plain) and _size(style) >= 2.5:
			return section_recipes.slot(
				"figure", "one number in digits, a quantity the material gives, never a year, never invented"
			)
		if NUMERAL.match(plain) and words == 1:
			return section_recipes.slot("numeral", "the number of the item, 01, 02, 03")
		if el in {"p", "span", "small", "li", "figcaption"}:
			upper = str(style.get("textTransform", "")) == "uppercase"
			if words <= 4 and (upper or style.get("letterSpacing")):
				return section_recipes.slot("label", _range(words) + " naming the subject")
			if words > 14:
				role = "lead" if self.leads == 0 else "item-text"
				self.leads += 1
				return section_recipes.slot(role, _range(words))
			return section_recipes.slot("text" if words > 6 else "caption", _range(words))
		return section_recipes.slot("text", _range(words))


def _size(style: dict) -> float:
	"""The font size of a style, in rem (px counted as 16 to the rem); 0 when it is not a plain length."""
	found = re.match(r"^\s*([\d.]+)\s*(rem|px)\s*$", str(style.get("fontSize", "")))
	if not found:
		return 0.0
	value = float(found.group(1))
	return value if found.group(2) == "rem" else value / 16


# ---------------------------------------------------------------- the tree


class Capture:
	def __init__(self, pairs: list[tuple[str, str]], forbidden: set[str]):
		self.pairs = pairs
		self.forbidden = forbidden
		self.photos: dict[str, int] = {}
		self.words = Words()
		self.literals = 0
		self.nodes = 0

	def value(self, raw):
		if not isinstance(raw, str):
			return raw
		out = raw
		for needle, token in self.pairs:
			if needle in out:
				out = out.replace(needle, "{{" + token + "}}")
		stripped = block_format.TOKEN.sub("", out)
		if block_format.CSS_FORBIDDEN.search(stripped):
			if "url(" in stripped.lower():
				raise Refused("a photograph is set as a background (a block's photographs are images)")
			raise Refused(f"a style value the format refuses: {stripped[:40]}")
		self.literals += len(block_format.COLOUR_LITERAL.findall(stripped))
		return out

	def styles(self, raw) -> dict | None:
		out = {}
		for key, value in (raw or {}).items():
			if not block_format.CSS_KEY.match(str(key)) or isinstance(value, (dict, list)) or value is None:
				continue
			out[key] = self.value(value)
		return out or None

	def name(self, name) -> str | None:
		name = str(name or "").strip().lower()
		if not SAFE_NAME.match(name) or any(word in name for word in self.forbidden):
			return None
		return name

	def attrs(self, block: dict, el: str, classes: list) -> dict | None:
		attributes = {**(block.get("attributes") or {}), **(block.get("customAttributes") or {})}
		out = {}
		if el == "img":
			src = str(attributes.get("src") or "")
			index = self.photos.setdefault(src, len(self.photos))
			out["src"] = "{{photo." + str(index) + "}}"
			out["alt"] = section_recipes.slot("alt", section_recipes.ALT_GUIDANCE)
			return out
		if el == "a":
			href = str(attributes.get("href") or "")
			out["href"] = (
				href
				if href.startswith("#") and len(href) > 1 and block_format.SAFE_HREF.match(href)
				else "{{cta_href}}"
			)
		for key, value in attributes.items():
			if (
				ALLOWED_ATTRS.match(str(key))
				and isinstance(value, (str, int, float))
				and not block_format.TOKEN.search(str(value))
			):
				# a title or a label is words of the business: the structure keeps only what is not words
				if key in {"title", "aria-label"}:
					continue
				out[key] = str(value)
		return out or None

	def node(self, block: dict, depth: int = 1) -> dict:
		self.nodes += 1
		for key, why in REFUSED_KEYS.items():
			if block.get(key):
				raise Refused(why)
		custom = block.get("customAttributes") or {}
		if custom.get("data-lucide"):
			raise Refused("it holds an icon")
		el = block.get("element") or "div"
		if el not in block_format.TAGS:
			raise Refused(f"a `{el}` is not a tag of the format")
		inner = block.get("innerHTML")
		if isinstance(inner, str) and ("{%" in inner or "{{" in inner):
			raise Refused("it holds a live component")
		classes = [
			c
			for c in (block.get("classes") or [])
			if isinstance(c, str) and c.startswith("u-") and block_format.CLASS.match(c)
		]
		# the reveals are given to every section by the site, they are not part of the design
		classes = [c for c in classes if not c.startswith("u-reveal")]
		node: dict = {"el": el}
		if (name := self.name(block.get("blockName"))) is not None:
			node["name"] = name
		if classes:
			node["classes"] = classes
		for src, dst in (("baseStyles", "style"), ("tabletStyles", "t_style"), ("mobileStyles", "m_style")):
			if (styles := self.styles(block.get(src))) is not None:
				node[dst] = styles
		if (attrs := self.attrs(block, el, classes)) is not None:
			node["attrs"] = attrs
		children = [c for c in block.get("children") or [] if isinstance(c, dict)]
		if children:
			node["c"] = [self.node(c, depth + 1) for c in children]
		elif isinstance(inner, str) and _plain(inner):
			node["text"] = self.words.slot(node, inner)
		return node


# ---------------------------------------------------------------- what the plan reads


def kind_of(section: dict, given: str | None = None) -> str:
	"""The kind of a section of the plan: the one given, else the one its name says, else a plain text section."""
	if given in section_recipes_kinds():
		return given
	name = str(section.get("blockName") or "").lower()
	for start, kind in KIND_BY_NAME:
		if name.startswith(start) or name.endswith(start):
			return kind
	return "text"


def section_recipes_kinds() -> set[str]:
	from builder.site_ai.nora.site_plan import SECTION_KINDS

	return set(SECTION_KINDS)


def family_of(kind: str) -> str:
	"""The family the recipes of a kind go by (`feature-grid` is `features`), the kind itself when no recipe has it yet."""
	count: dict[str, int] = {}
	for recipe in section_recipes.REGISTRY.values():
		if kind in recipe.kinds:
			count[recipe.family] = count.get(recipe.family, 0) + 1
	return max(count, key=count.get) if count else kind


def _shape(node: dict) -> str:
	"""What one item of a repeated group holds, in words ("a numeral, a title and a text")."""
	parts = []

	def walk(n):
		text = str(n.get("text") or "")
		slot = block_format.SLOT.match(text)
		if slot:
			parts.append(
				{
					"item-title": "a title",
					"numeral": "a numeral",
					"item-text": "a text",
					"text": "a text",
					"figure": "a figure",
					"label": "a small label",
					"caption": "a caption",
					"button": "a button",
				}.get(slot.group(1), "")
			)
		if n.get("el") == "img":
			parts.append("a photograph")
		for c in n.get("c") or []:
			walk(c)

	walk(node)
	seen = []
	for p in parts:
		if p and p not in seen:
			seen.append(p)
	return ", ".join(seen[:-1]) + (" and " if len(seen) > 1 else "") + seen[-1] if seen else "a few words"


def describe(tree: dict, ground: str, photos: int) -> str:
	"""A line for the plan, made from the structure only (nothing of the business it came from); a person refines it in the hub."""
	grid = None

	def find(n):
		nonlocal grid
		classes = n.get("classes") or []
		style = n.get("style") or {}
		if (
			grid is None
			and (any(c.startswith("u-grid") for c in classes) or str(style.get("display")) == "grid")
			and len(n.get("c") or []) >= 2
		):
			grid = n
		for c in n.get("c") or []:
			find(c)

	find(tree)
	heading = any(re.match(r"^WRITE heading", str(n.get("text") or "")) for n in _all(tree))
	bits = []
	if heading:
		short = any(str(n.get("text") or "").startswith(("WRITE lead", "WRITE text")) for n in _all(tree))
		bits.append("a heading" + (" and a short text" if short else ""))
	if grid is not None:
		bits.append(
			("over " if bits else "")
			+ f"{len(grid['c'])} items side by side, each holding {_shape(grid['c'][0])}"
		)
	if not bits:
		bits.append("a band")
	if photos:
		bits.append(f"with {photos} photograph{'s' if photos > 1 else ''}")
	bits.append(
		{"plain": "on the plain ground", "tint": "on a tinted ground", "deep": "on a deep band"}[ground]
	)
	return ("; ".join(bits) + ". Kept from a written site: the structure of a section the judge accepted.")[
		:400
	]


def _all(node: dict):
	yield node
	for c in node.get("c") or []:
		yield from _all(c)


def fingerprint(tree: dict) -> str:
	return hashlib.sha1(json.dumps(tree, sort_keys=True).encode("utf-8")).hexdigest()[:8]


# ---------------------------------------------------------------- the block


def capture_section(
	section: dict, *, handles: dict, palette: dict | None = None, kind: str | None = None, forbidden=()
) -> dict:
	"""The hub's block (the body of its `publish_block`) for one section of a written page. Raises `Refused` with the reason when the section
	cannot be a block. `forbidden`: words of the business (its name, its activity) that no node name may carry."""
	look = section_recipes.Look(handles, palette)
	ground = ground_of_section(section, look)
	capture = Capture(token_pairs(look, ground, handles), {w.lower() for w in forbidden if len(w) >= 4})
	tree = capture.node(section)
	if tree.get("el") != "section":
		raise Refused("it is not a section")
	if capture.literals > MAX_LITERAL_COLOURS:
		raise Refused(
			f"{capture.literals} colours are not the site's own: the block would look the same on every site"
		)
	photos = len(capture.photos)
	motion = "None"
	for node in _all(tree):
		for cls in node.get("classes") or []:
			if cls.startswith("u-marquee"):
				motion = "Brisk"
			elif cls.startswith(("u-count",)) and motion == "None":
				motion = "Calm"
	kind = kind_of(section, kind)
	family = family_of(kind)
	block_id = f"{family}.cap-{fingerprint(tree)}"
	errors, _warnings = block_format.lint(
		tree, block_id=block_id, kinds=[kind], photos=photos, form=False, motion=motion
	)
	if errors:
		raise Refused(errors[0])
	return {
		"id": block_id,
		"title": f"{kind.replace('-', ' ').capitalize()}, kept from a written site",
		"kinds": [kind],
		"look": describe(tree, ground, photos),
		"photos": photos,
		"form": False,
		"ground": ground,
		"motion": motion,
		"notes": "Captured from a section a written site kept (judged professional). It carries no words, no photograph and no colour of the site it came from. Read it, correct its look line, then publish it.",
		"tree": tree,
	}


def capture_page(
	blocks: list, *, forbidden=(), palette: dict | None = None, kinds: dict | None = None
) -> tuple[list[dict], list[str]]:
	"""(the blocks of a page's sections after the first, why each other section was refused). The first section of a page is its opening and stays
	with its site."""
	prefix = prefix_of(blocks)
	if not prefix:
		return [], ["the page does not use the tokens of a generated site"]
	handles = handles_of(prefix)
	sections = [b for b in section_recipes._in_order(blocks) if b.get("element") == "section"]
	nested = {
		id(b)
		for s in sections
		for b in section_recipes._in_order(s.get("children") or [])
		if b.get("element") == "section"
	}
	top = [s for s in sections if id(s) not in nested]
	made, why = [], []
	for index, section in enumerate(top[1:], start=1):
		label = f"section {index} ({section.get('blockName') or 'unnamed'})"
		try:
			made.append(
				capture_section(
					section,
					handles=handles,
					palette=palette,
					kind=(kinds or {}).get(index),
					forbidden=forbidden,
				)
			)
		except Refused as e:
			why.append(f"{label}: {e}")
	return made, why


# ---------------------------------------------------------------- from a stored page to the hub


def push_block(block: dict) -> str:
	"""Sends a block to the hub (`template_hub_url`, with the publisher's key of the site) where it becomes a DRAFT. Returns what happened, in a
	line: never a key, never a payload."""
	import frappe
	import requests

	hub = (frappe.conf.get("template_hub_url") or "").rstrip("/")
	key, secret = frappe.conf.get("hub_publish_api_key"), frappe.conf.get("hub_publish_api_secret")
	if not (hub and key and secret):
		return "not sent: this site has no hub to publish to"
	try:
		response = requests.post(
			f"{hub}/api/method/builder_hub.publish.publish_block",
			data=json.dumps(block),
			headers={"Authorization": f"token {key}:{secret}", "Content-Type": "application/json"},
			timeout=30,
		)
	except Exception as e:
		return f"not sent: {type(e).__name__}"
	if response.status_code == 200:
		body = (response.json() or {}).get("message") or {}
		return f"draft {body.get('block')} v{body.get('version')}"
	if response.status_code == 403:
		return (
			"not sent: the hub refused the block (it is already published, or the key is not a publisher's)"
		)
	return f"not sent: the hub answered {response.status_code}"


def capture_stored_page(page: str, push: bool = False, forbidden=()) -> dict:
	"""For `bench execute`: the sections of a stored page (after its first) that can be blocks, and why the others cannot; with `push` they go to the
	hub as drafts. `forbidden`: words of the business that no name may carry (its name, its activity)."""
	import frappe

	from builder.site_ai.nora.site_builder import palette_values

	blocks = (
		frappe.db.get_value("Builder Page", page, "blocks")
		or frappe.db.get_value("Builder Page", page, "draft_blocks")
		or "[]"
	)
	blocks = json.loads(blocks) if isinstance(blocks, str) else blocks
	prefix = prefix_of(blocks)
	made, why = capture_page(blocks, palette=palette_values(prefix) if prefix else None, forbidden=forbidden)
	sent = {b["id"]: push_block(b) for b in made} if push else {}
	return {"blocks": [b["id"] for b in made], "refused": why, "sent": sent}


def enabled(conf=None) -> bool:
	"""Whether a finished build keeps its accepted sections as drafts in the hub (`nora_capture_blocks` in site_config, off unless set)."""
	try:
		import frappe

		conf = conf if conf is not None else frappe.conf
		return str(conf.get("nora_capture_blocks", 0)).strip().lower() in ("1", "true", "yes", "on")
	except Exception:
		return False


def keep_accepted(
	pages: list[dict], reviews: list[dict], *, hidden=(), held=(), site_name: str = "", activity: str = ""
) -> list[str]:
	"""After a build: the sections of the pages the judge accepted go to the hub as drafts. A page is taken only when it was read, called
	professional and has nothing measured against it (visual_check.accepted), and was neither held nor hidden. Returns one line per block
	(its id and what the hub said), never raises: a hub that does not answer never costs a build anything."""
	from builder.site_ai.nora import visual_check

	forbidden = {w for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", f"{site_name} {activity}")}
	held_names = {h.get("name") for h in held}
	lines: list[str] = []
	for page in pages:
		name = page.get("name")
		report = next((r for r in reviews if r.get("name") == name), None)
		if (
			not name
			or name in hidden
			or name in held_names
			or not report
			or not visual_check.accepted(report, lenient=False)
		):
			continue
		try:
			done = capture_stored_page(name, push=True, forbidden=forbidden)
		except Exception as e:
			lines.append(f"{page.get('title')}: not kept ({type(e).__name__})")
			continue
		lines.extend(f"{block}: {done['sent'].get(block)}" for block in done["blocks"])
	return lines
