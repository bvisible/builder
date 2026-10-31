# //// Neoffice — added file (no upstream equivalent): a component written in Tailwind becomes a draft block of the Builder Hub.
"""The hub's library grows from what other people drew well, not only from what a site once wrote: an MIT-licensed component (HyperUI, shadcn/ui,
Flowbite…) is read as markup and written again as a block (block_format.py), in the language of the site generator.

What the import keeps, and what it does not:
- the STRUCTURE is kept: the tags, the grid, the flex rows, the spacing, the breakpoints (`sm:` `md:` `lg:` become the block's `t_style`/`m_style`);
- the DESIGN SYSTEM is applied, nothing of the source's look survives: a Tailwind palette colour becomes the token of the role it plays on its
  ground (`text-gray-900` is `{{ground.ink}}`, `text-gray-500` `{{ground.muted}}`, `bg-gray-100` `{{tint}}`, `border-gray-200` `{{ground.hair}}`,
  `text-indigo-700` `{{ground.accent}}`), a dark or coloured surface is a node on the `deep` ground, `rounded-*` and `shadow-*` are the site's
  `--radius-*` and `--shadow-*`, a button is a `u-btn`, a bordered and rounded box a `u-card`, a font the site's own;
- every word becomes a SLOT, of the length of the source's (`Lorem ipsum…` is only a measure), every picture a `{{photo.N}}`, every link the
  site's `{{cta_href}}`; an icon (inline SVG) is dropped, a block has no tag for it;
- the questions of a FAQ (`<details>` with its `<summary>`) become the site's own accordion (`u-faq`): the source's box, rule and air are not kept;
- a component that cannot be a block is refused with the reason: a form, a table, a script, more than six pictures, a gradient or a
  background image, and anything the linter (block_format.lint) refuses.

The result is a DRAFT of the hub (capture.push_block), never a published block: a person reads it in the hub's desk and publishes it. The source,
its licence and its copyright holder are written in the block's notes (MIT asks that the notice goes with copies of the work).

Pure Python (no Frappe at import), so the tests run anywhere. Fetching the source and sending the draft are the only parts that touch the network."""

import html
import re
from collections import Counter
from dataclasses import dataclass, replace
from html.parser import HTMLParser

from builder.site_ai.nora import block_format, capture
from builder.site_ai.nora import recipes as section_recipes

# ---------------------------------------------------------------- the sources

# every source is MIT: the licence text names the holder, the notes of a block carry both. Pinned to a commit, so that an import can be done again.
HYPERUI = {
	"name": "HyperUI",
	"url": "https://github.com/markmead/hyperui",
	"licence": "MIT",
	"holder": "Mark Mead",
	"ref": "637323c8d3046645ac5f28edc2074d18f22a2b94",
	"raw": "https://raw.githubusercontent.com/markmead/hyperui/{ref}/public/examples/marketing/{category}/{number}.html",
}
# a HyperUI category of the marketing set, and the kind of section its components are
HYPERUI_KINDS = {
	"ctas": "cta",
	"feature-grids": "feature-grid",
	"stats": "figures",
	"testimonials": "testimonials",
	"team-sections": "team",
	"logo-clouds": "brand-row",
	"sections": "two-column",
	"pricing": "pricing",
	"faqs": "faq",
	"blog-cards": "cards",
	"cards": "cards",
	"product-collections": "product-row",
	"banners": "cta",
}
HYPERUI_COUNT = {
	"ctas": 4,
	"feature-grids": 4,
	"stats": 3,
	"testimonials": 3,
	"team-sections": 3,
	"logo-clouds": 4,
	"sections": 4,
	"pricing": 2,
	"faqs": 3,
	"blog-cards": 7,
	"cards": 9,
	"product-collections": 4,
	"banners": 3,
}

MAX_UNKNOWN_CLASSES = 6
# a quantity written in digits, with a currency in front or a unit behind ($4.8m, 98%, 1 200+)
FIGURE_TEXT = re.compile(r"^\s*[$€£]?\s*\d[\d\s.,'’]*\s*[+%a-zA-Z/]{0,4}\s*$")
SHELL_TAGS = {"div", "section", "main", "article"}
SECTION_PADDING = "6rem 0"
SECTION_PADDING_PHONE = "4rem 0"


class Refused(Exception):
	"""A component that cannot be a block, with the reason."""


# ---------------------------------------------------------------- the markup


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# the tags that are read and thrown away, and the ones that make the whole component impossible
DROPPED_TAGS = {"svg", "script", "style", "template", "noscript", "link", "meta", "title", "path", "use"}
REFUSED_TAGS = {
	"form": "a form is a live component, not a block",
	"input": "a form field is not a tag a block may hold",
	"select": "a form field is not a tag a block may hold",
	"textarea": "a form field is not a tag a block may hold",
	"table": "a table is not a tag a block may hold",
	"iframe": "an embedded page is not a tag a block may hold",
	"video": "a video is not a tag a block may hold",
	"audio": "a sound is not a tag a block may hold",
	"canvas": "a canvas is not a tag a block may hold",
	"pre": "preformatted code is not a tag a block may hold",
}
# the tags of the format, written another way
RENAMED = {
	"dl": "div",
	"dt": "p",
	"dd": "p",
	"main": "div",
	"nav": "div",
	"button": "a",
	"label": "span",
	"time": "span",
	"abbr": "span",
	"cite": "span",
	"code": "span",
	"mark": "span",
	"b": "strong",
	"i": "em",
	"q": "p",
	"picture": "div",
}
INLINE = {
	"span",
	"strong",
	"em",
	"b",
	"i",
	"small",
	"a",
	"br",
	"time",
	"abbr",
	"cite",
	"label",
	"code",
	"mark",
	"sup",
	"sub",
	"u",
	"s",
	"svg",
}
TEXT_TAGS = {
	"h1",
	"h2",
	"h3",
	"h4",
	"h5",
	"h6",
	"p",
	"blockquote",
	"figcaption",
	"li",
	"span",
	"strong",
	"em",
	"small",
	"a",
}
RESET_MARGIN = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "figure", "ul", "ol"}


HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
FAQ_FLOW = {"display", "flexDirection", "gap", "rowGap", "columnGap", "marginTop", "marginBottom"}
# what a question keeps of the source's type: the accordion of the site draws the rest (its layout, its rule, its sign)
TYPE_KEYS = {"fontSize", "fontWeight", "lineHeight", "letterSpacing", "color", "textTransform", "fontStyle"}


class Element:
	def __init__(self, tag: str, attrs: dict):
		self.tag = tag
		self.attrs = attrs
		self.children: list = []

	@property
	def classes(self) -> list[str]:
		return (self.attrs.get("class") or "").split()


class _Parser(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.root = Element("#root", {})
		self.stack = [self.root]

	def handle_starttag(self, tag, attrs):
		element = Element(tag, {k: v or "" for k, v in attrs})
		self.stack[-1].children.append(element)
		if tag not in VOID:
			self.stack.append(element)

	def handle_startendtag(self, tag, attrs):
		self.stack[-1].children.append(Element(tag, {k: v or "" for k, v in attrs}))

	def handle_endtag(self, tag):
		for index in range(len(self.stack) - 1, 0, -1):
			if self.stack[index].tag == tag:
				del self.stack[index:]
				return

	def handle_data(self, data):
		self.stack[-1].children.append(data)


def parse(markup: str) -> Element:
	"""The `<body>` of a component page (the page itself when it is a fragment)."""
	parser = _Parser()
	parser.feed(markup)
	parser.close()

	def find(element, tag):
		for child in element.children:
			if isinstance(child, Element):
				if child.tag == tag:
					return child
				found = find(child, tag)
				if found:
					return found
		return None

	return find(parser.root, "body") or parser.root


def descendants(element):
	"""The elements under an element, in document order."""
	for child in element.children:
		if isinstance(child, Element):
			yield child
			yield from descendants(child)


def fold_accordions(root: Element) -> None:
	"""Turns an accordion drawn with a script (Flowbite: a `data-accordion` box of `h2 > button` and `div[aria-labelledby]`) into the questions that fold,
	`details` > `summary` and the answer: the block has no script, and the site's own accordion (`u-faq`) folds them."""
	for box in [root, *descendants(root)]:
		if "data-accordion" not in box.attrs:
			continue
		kids = [c for c in box.children if isinstance(c, Element)]
		folds: list[Element] = []
		index = 0
		while index < len(kids):
			head, body = kids[index], kids[index + 1] if index + 1 < len(kids) else None
			if head.tag in HEADING_TAGS and body is not None and body.attrs.get("aria-labelledby"):
				summary = Element("summary", {})
				summary.children = [clean(text_of(head))]
				answer = [c for c in body.children if isinstance(c, Element)]
				if len(answer) == 1 and answer[0].tag == "div":  # the padded wrapper of the body
					answer = [c for c in answer[0].children if isinstance(c, Element)]
				fold = Element("details", {})
				fold.children = [summary, *answer[:1]]  # an answer is one paragraph in the site's accordion
				folds.append(fold)
				index += 2
			else:
				index += 1
		if folds:
			box.children = folds
			box.attrs = {}


def text_of(element) -> str:
	"""The words of an element, one line (an `<svg>` and a `<br>` say nothing, a `<br>` is a space, a `sr-only` text is for screen readers only)."""
	if isinstance(element, str):
		return element
	if element.tag in DROPPED_TAGS or "sr-only" in element.classes:
		return ""
	if element.tag == "br":
		return " "
	return "".join(text_of(c) for c in element.children)


def clean(text: str) -> str:
	return " ".join(html.unescape(text).split())


# ---------------------------------------------------------------- Tailwind


@dataclass(frozen=True)
class Colour:
	"""A Tailwind colour as the role it plays, before the ground it sits on says which token it is."""

	kind: str  # text | bg | border
	family: str  # white | black | transparent | current | neutral | chromatic
	shade: int = 500
	alpha: float = 1.0

	@property
	def dark(self) -> bool:
		"""A surface of this colour is a deep band (black, a dark neutral, a saturated colour)."""
		if self.alpha < 0.9:
			return False
		if self.family == "black":
			return True
		if self.family == "neutral":
			return self.shade >= 800
		return self.family == "chromatic" and self.shade >= 500

	@property
	def light(self) -> bool:
		return self.family == "white" or (self.family in {"neutral", "chromatic"} and self.shade <= 200)


NEUTRALS = {"gray", "slate", "zinc", "neutral", "stone"}
CHROMATICS = {
	"red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose",
}  # fmt: skip
SHADES = {50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950}


# The libraries that name a colour by the role it plays (Flowbite's `text-heading`, `bg-neutral-secondary`, `border-default`; shadcn/ui's
# `text-muted-foreground`, `bg-primary`, `border-border`) each give it as the Tailwind colour that plays the same role, so that one table
# of roles (`resolve_colour`) serves them all. (family, shade) per kind of utility.
INK, MUTED, WHITE, PALE, PAPER = (
	("neutral", 900),
	("neutral", 500),
	("white", 500),
	("neutral", 100),
	("neutral", 200),
)
BRAND, BRAND_STRONG, BRAND_PALE, DEEP = (
	("chromatic", 600),
	("chromatic", 700),
	("chromatic", 100),
	("neutral", 900),
)
SEMANTIC = {
	"text": {
		# Flowbite
		"heading": INK,
		"body": ("neutral", 700),
		"body-subtle": MUTED,
		"brand": BRAND,
		"fg-brand": BRAND,
		"fg-brand-strong": BRAND_STRONG,
		"fg-danger": BRAND,
		"fg-success": BRAND,
		"fg-warning": BRAND,
		"fg-heading": INK,
		"fg-body": ("neutral", 700),
		# shadcn/ui
		"foreground": INK,
		"muted-foreground": MUTED,
		"card-foreground": INK,
		"popover-foreground": INK,
		"secondary-foreground": INK,
		"accent-foreground": INK,
		"primary": BRAND,
		"primary-foreground": WHITE,
		"destructive": BRAND,
		"destructive-foreground": WHITE,
	},
	"bg": {
		# Flowbite
		"neutral-primary": WHITE,
		"neutral-primary-soft": WHITE,
		"neutral-primary-medium": WHITE,
		"neutral-secondary": PALE,
		"neutral-secondary-soft": PALE,
		"neutral-secondary-medium": PALE,
		"neutral-secondary-strong": PAPER,
		"neutral-tertiary": PALE,
		"neutral-tertiary-medium": PALE,
		"neutral-quaternary": PAPER,
		"brand": BRAND,
		"brand-strong": BRAND_STRONG,
		"brand-soft": BRAND_PALE,
		"brand-subtle": BRAND_PALE,
		"dark": DEEP,
		"dark-strong": ("neutral", 950),
		"neutral-dense": DEEP,
		# shadcn/ui
		"background": WHITE,
		"card": WHITE,
		"popover": WHITE,
		"muted": PALE,
		"secondary": PALE,
		"accent": PALE,
		"primary": BRAND,
		"destructive": BRAND,
		"border": PAPER,
		"input": PAPER,
		"foreground": DEEP,
		"brand-foreground": BRAND_PALE,
	},
	"border": {
		# Flowbite
		"default": PAPER,
		"default-medium": PAPER,
		"default-strong": ("neutral", 300),
		"brand": BRAND,
		"neutral": PAPER,
		# shadcn/ui
		"border": PAPER,
		"input": PAPER,
		"primary": BRAND,
		"ring": ("chromatic", 400),
		"destructive": BRAND,
	},
}


def colour(kind: str, text: str) -> Colour | None:
	alpha = 1.0
	if "/" in text:
		text, _, tail = text.rpartition("/")
		if not tail.isdigit():
			return None
		alpha = int(tail) / 100
	role = SEMANTIC.get(kind, {}).get(text)
	if role:
		return Colour(kind, role[0], role[1], alpha)
	if text in {"white", "black"}:
		return Colour(kind, text, 500, alpha)
	if text in {"transparent", "current", "inherit"}:
		return Colour(kind, text, 500, alpha)
	found = re.fullmatch(r"([a-z]+)-(\d{2,3})", text)
	if not found or int(found.group(2)) not in SHADES:
		return None
	family = (
		"neutral" if found.group(1) in NEUTRALS else "chromatic" if found.group(1) in CHROMATICS else None
	)
	return Colour(kind, family, int(found.group(2)), alpha) if family else None


def resolve_colour(c: Colour, ground: str) -> str:
	"""The token that plays this colour's part on this ground (`plain`, `tint` or `deep`)."""
	if c.family == "transparent":
		return "transparent"
	if c.family in {"current", "inherit"}:
		return "currentColor" if c.family == "current" else "inherit"
	deep = ground == "deep"
	if c.kind == "text":
		if c.family == "white":
			return "{{ground.ink}}" if deep else "{{ground.background}}"
		if c.family == "black":
			return "{{ground.ink}}"
		if c.family == "chromatic":
			return "{{ground.accent}}"
		if deep:
			return "{{ground.ink}}" if c.shade <= 200 else "{{ground.muted}}"
		return "{{ground.ink}}" if c.shade >= 800 else "{{ground.muted}}"
	if c.kind == "border":
		if c.family == "black":
			return "{{ground.ink}}"
		if c.family == "chromatic" and c.shade >= 400:
			return "{{ground.accent}}"
		if c.family == "neutral" and c.shade >= 600:
			return "{{ground.muted}}"
		return "{{ground.hair}}"
	# a surface
	if c.alpha < 0.9:
		return "{{ground.hair}}"
	if c.family == "white":
		return "{{ground.background}}" if ground == "plain" else "{{background}}"
	if c.light:
		return {"plain": "{{tint}}", "tint": "{{background}}", "deep": "{{deep_hair}}"}[ground]
	if c.dark:
		return (
			"{{primary}}"
			if deep and c.family == "chromatic"
			else "{{deep_hair}}"
			if deep
			else "{{ground.background}}"
		)
	return "{{ground.hair}}"


def ground_of(c: Colour | None) -> str:
	"""The ground a surface of this colour is: a band of ink or colour is `deep`, a pale grey `tint`, white and nothing `plain`."""
	if c is None or c.alpha < 0.9 or c.family in {"white", "transparent", "current", "inherit"}:
		return "plain"
	if c.dark:
		return "deep"
	return "tint" if c.light and c.family == "neutral" else "plain"


BREAKPOINTS = {"sm": 1, "md": 2, "lg": 3, "xl": 4, "2xl": 5}
# the widest screen a level reaches: the phone sees the base only, the tablet the base up to `md:`, the desktop everything
PHONE, TABLET, DESKTOP = 0, 2, 5

SIZES = {
	"xs": ("0.75rem", "1.333"),
	"sm": ("0.875rem", "1.429"),
	"base": ("1rem", "1.5"),
	"lg": ("1.125rem", "1.556"),
	"xl": ("1.25rem", "1.4"),
	"2xl": ("1.5rem", "1.333"),
	"3xl": ("1.875rem", "1.2"),
	"4xl": ("2.25rem", "1.15"),
	"5xl": ("3rem", "1.1"),
	"6xl": ("3.75rem", "1.1"),
	"7xl": ("4.5rem", "1.1"),
	"8xl": ("6rem", "1.1"),
	"9xl": ("8rem", "1.1"),
}  # fmt: skip
LEADING = {"none": "1", "tight": "1.25", "snug": "1.375", "normal": "1.5", "relaxed": "1.625", "loose": "2"}
TRACKING = {
	"tighter": "-0.05em",
	"tight": "-0.025em",
	"normal": "0",
	"wide": "0.025em",
	"wider": "0.05em",
	"widest": "0.1em",
}
WEIGHTS = {
	"thin": "100", "extralight": "200", "light": "300", "normal": "400", "medium": "500", "semibold": "600", "bold": "700", "extrabold": "800", "black": "900",
}  # fmt: skip
MAX_W = {
	"xs": "20rem", "sm": "24rem", "md": "28rem", "lg": "32rem", "xl": "36rem", "2xl": "42rem", "3xl": "48rem", "4xl": "56rem", "5xl": "64rem",
	"6xl": "72rem", "7xl": "80rem", "prose": "65ch", "none": "none", "full": "100%", "screen-sm": "640px", "screen-md": "768px",
	"screen-lg": "1024px", "screen-xl": "1280px", "screen-2xl": "1536px", "min": "min-content", "max": "max-content", "fit": "fit-content",
}  # fmt: skip
ROUNDED = {
	"": "var(--radius-sm)", "sm": "var(--radius-sm)", "md": "var(--radius)", "lg": "var(--radius-lg)", "xl": "var(--radius-lg)", "2xl": "var(--radius-lg)",
	"3xl": "var(--radius-lg)",
	"base": "var(--radius)", "full": "var(--radius-pill)", "none": "0",
}  # fmt: skip
SHADOWS = {
	"": "var(--shadow)",
	"xs": "var(--shadow-sm)",
	"sm": "var(--shadow-sm)",
	"md": "var(--shadow)",
	"lg": "var(--shadow-lg)",
	"xl": "var(--shadow-lg)",
	"2xl": "var(--shadow-lg)",
	"none": "none",
}
CORNERS = {
	"t": ("TopLeft", "TopRight"), "r": ("TopRight", "BottomRight"), "b": ("BottomLeft", "BottomRight"), "l": ("TopLeft", "BottomLeft"),
	"tl": ("TopLeft",), "tr": ("TopRight",), "bl": ("BottomLeft",), "br": ("BottomRight",),
}  # fmt: skip
SIDES = {"t": "Top", "r": "Right", "b": "Bottom", "l": "Left", "s": "Left", "e": "Right"}
ALIGN = {
	"start": "flex-start",
	"end": "flex-end",
	"center": "center",
	"baseline": "baseline",
	"stretch": "stretch",
}
JUSTIFY = {
	"start": "flex-start",
	"end": "flex-end",
	"center": "center",
	"between": "space-between",
	"around": "space-around",
	"evenly": "space-evenly",
	"stretch": "stretch",
}

STATIC = {
	"flex": {"display": "flex"},
	"inline-flex": {"display": "inline-flex"},
	"grid": {"display": "grid"},
	"inline-grid": {"display": "inline-grid"},
	"block": {"display": "block"},
	"inline-block": {"display": "inline-block"},
	"inline": {"display": "inline"},
	"hidden": {"display": "none"},
	"contents": {"display": "contents"},
	"flex-col": {"flexDirection": "column"},
	"flex-row": {"flexDirection": "row"},
	"flex-col-reverse": {"flexDirection": "column-reverse"},
	"flex-row-reverse": {"flexDirection": "row-reverse"},
	"flex-wrap": {"flexWrap": "wrap"},
	"flex-nowrap": {"flexWrap": "nowrap"},
	"flex-1": {"flex": "1 1 0%"},
	"flex-auto": {"flex": "1 1 auto"},
	"flex-none": {"flex": "none"},
	"grow": {"flexGrow": "1"},
	"grow-0": {"flexGrow": "0"},
	"shrink": {"flexShrink": "1"},
	"shrink-0": {"flexShrink": "0"},
	"relative": {"position": "relative"},
	"absolute": {"position": "absolute"},
	"fixed": {"position": "fixed"},
	"sticky": {"position": "sticky"},
	"static": {"position": "static"},
	"overflow-hidden": {"overflow": "hidden"},
	"overflow-clip": {"overflow": "clip"},
	"overflow-visible": {"overflow": "visible"},
	"overflow-auto": {"overflow": "auto"},
	"object-cover": {"objectFit": "cover"},
	"object-contain": {"objectFit": "contain"},
	"object-center": {"objectPosition": "center"},
	"text-left": {"textAlign": "left"},
	"text-center": {"textAlign": "center"},
	"text-right": {"textAlign": "right"},
	"text-justify": {"textAlign": "justify"},
	"text-pretty": {"textWrap": "pretty"},
	"text-balance": {"textWrap": "balance"},
	"uppercase": {"textTransform": "uppercase"},
	"lowercase": {"textTransform": "lowercase"},
	"capitalize": {"textTransform": "capitalize"},
	"italic": {"fontStyle": "italic"},
	"not-italic": {"fontStyle": "normal"},
	"underline": {"textDecoration": "underline"},
	"no-underline": {"textDecoration": "none"},
	"truncate": {"overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"},
	"whitespace-nowrap": {"whiteSpace": "nowrap"},
	"order-last": {"order": "9999"},
	"order-first": {"order": "-9999"},
	"aspect-video": {"aspectRatio": "16 / 9"},
	"aspect-square": {"aspectRatio": "1 / 1"},
	"grayscale": {"filter": "grayscale(1)"},
	"list-disc": {"listStyleType": "disc"},
	"list-decimal": {"listStyleType": "decimal"},
	"list-none": {"listStyleType": "none"},
	"border-solid": {"borderStyle": "solid"},
	"border-dashed": {"borderStyle": "dashed"},
	"border-dotted": {"borderStyle": "dotted"},
}  # fmt: skip
# what a class that only decorates (a transition, a cursor, a focus ring) or only names a font says nothing to a block
IGNORED = re.compile(
	r"^(?:transition(?:-.+)?|duration-.+|ease-.+|delay-.+|cursor-.+|select-.+|pointer-events-.+|antialiased|subpixel-antialiased|font-(?:sans|serif|mono)"
	r"|outline(?:-.+)?|group|peer|will-change-.+|appearance-.+|scroll-.+|dark|stroke-.+|fill-.+|ring-offset-.+|object-(?:top|bottom|left|right)|box-(?:border|content)"
	# what only decorates (a glow, a mask, a gradient text, a transform, an animation) says nothing to a block
	r"|animate-.+|delay-\d+|text-transparent|bg-radial.*|bg-conic.*|drop-shadow(?:-.+)?|blur(?:-.+)?|backdrop-blur(?:-.+)?|mix-blend-.+|isolate"
	r"|fade-(?:top|bottom|x|y|left|right)(?:-lg)?|line-(?:b|t|x|y)|-?translate-[xyz]-.+|-?scale(?:-[xy])?-.+|-?rotate-.+|skew-.+"
	r"|(?:from|via|to)-\d+%|auto-rows-fr|rounded-\[.+\])$"
)
# a property that goes back to this, not to `initial`, when a smaller screen does not set it
RESET_TO = {"display": "block", "position": "static", "flexDirection": "row", "overflow": "visible"}


def length(value: str) -> str | None:
	"""A Tailwind length (`4`, `0.5`, `px`, `1/2`, `full`, `[calc(100%-2rem)]`) as a CSS one."""
	if value == "px":
		return "1px"
	if value in {"auto", "0"}:
		return value
	if value == "full":
		return "100%"
	if value in {"min", "max", "fit"}:
		return f"{value}-content"
	if re.fullmatch(r"\d+(?:\.\d+)?", value):
		return f"{float(value) * 0.25:g}rem"
	fraction = re.fullmatch(r"(\d+)/(\d+)", value)
	if fraction:
		return f"{int(fraction.group(1)) / int(fraction.group(2)) * 100:g}%"
	if value.startswith("[") and value.endswith("]"):
		inner = value[1:-1].replace("_", " ")
		inner = (
			re.sub(r"(?<=[\w%)])([+\-*/])(?=[\w(])", r" \1 ", inner) if inner.startswith("calc(") else inner
		)
		if re.fullmatch(r"[\w.%()+\-*/ ,]+", inner) and not block_format.CSS_FORBIDDEN.search(inner):
			return inner
	return None


def _sides(prefix: str, axis: str, value: str):
	"""padding/margin props of `p-4`, `px-4`, `mt-2`: `axis` is '', x, y or one side letter."""
	names = {"": ("Top", "Right", "Bottom", "Left"), "x": ("Left", "Right"), "y": ("Top", "Bottom")}.get(
		axis
	) or (SIDES[axis],)
	return {f"{prefix}{side}": value for side in names}


def utility(u: str) -> dict | None:
	"""The CSS (camelCase, a colour as a `Colour`) of one Tailwind utility: `{}` when it says nothing to a block, `None` when it is not known."""
	if u in STATIC:
		return dict(STATIC[u])
	if IGNORED.match(u):
		return {}
	negative = u.startswith("-")
	body = u[1:] if negative else u

	if body in {"max-w-container", "container"}:
		return {"maxWidth": "{{container}}"}
	if body == "bg-clip-text":  # a gradient that is the colour of a text, not a surface
		return {"__clip_text": True}
	if body == "text-md":
		return {"fontSize": "1rem", "lineHeight": "1.5"}
	if re.fullmatch(r"glass-\d", body):  # a surface with a rule round it and a gradient in it: a card
		return {f"border{side}Width": "1px" for side in ("Top", "Right", "Bottom", "Left")} | {
			"borderStyle": "solid"
		}
	if re.fullmatch(r"bg-(?:linear|gradient)-.+", body):
		return {"__gradient": True}
	found = re.fullmatch(r"(from|via|to)-(.+)", body)
	if found:
		stop = colour("bg", found.group(2))
		return {f"__{found.group(1)}": stop} if stop else {}
	found = re.fullmatch(r"(p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me)-(.+)", body)
	if found:
		kind, value = found.groups()
		amount = length(value)
		if amount is None or (amount == "auto" and kind[0] == "p"):
			return None
		if negative and amount not in {"0", "auto"}:
			amount = "-" + amount
		return _sides("padding" if kind[0] == "p" else "margin", kind[1:], amount)

	found = re.fullmatch(r"(gap|gap-x|gap-y)-(.+)", body)
	if found:
		amount = length(found.group(2))
		key = {"gap": "gap", "gap-x": "columnGap", "gap-y": "rowGap"}[found.group(1)]
		return {key: amount} if amount else None

	found = re.fullmatch(r"space-(x|y)-(.+)", body)
	if found:
		amount = length(found.group(2))
		return {f"__space_{found.group(1)}": amount} if amount else None

	found = re.fullmatch(r"(w|h|size|min-w|min-h|max-w|max-h)-(.+)", body)
	if found:
		kind, value = found.groups()
		if kind == "max-w" and value in MAX_W:
			amount = MAX_W[value]
		elif value == "screen":
			amount = "100vh" if kind.endswith("h") else "100%"
		else:
			amount = length(value)
		if amount is None:
			return None
		keys = {
			"w": ("width",),
			"h": ("height",),
			"size": ("width", "height"),
			"min-w": ("minWidth",),
			"min-h": ("minHeight",),
			"max-w": ("maxWidth",),
			"max-h": ("maxHeight",),
		}[kind]
		return {key: amount for key in keys}

	found = re.fullmatch(r"(top|right|bottom|left|inset|inset-x|inset-y)-(.+)", body)
	if found:
		amount = length(found.group(2))
		if amount is None:
			return None
		if negative and amount not in {"0", "auto"}:
			amount = "-" + amount
		keys = {
			"top": ("top",),
			"right": ("right",),
			"bottom": ("bottom",),
			"left": ("left",),
			"inset": ("top", "right", "bottom", "left"),
			"inset-x": ("left", "right"),
			"inset-y": ("top", "bottom"),
		}[found.group(1)]
		return {key: amount for key in keys}

	found = re.fullmatch(r"z-(\d+)", body)
	if found:
		return {"zIndex": found.group(1)}
	found = re.fullmatch(r"grid-cols-(\d+)", body)
	if found:
		return {"gridTemplateColumns": f"repeat({found.group(1)}, minmax(0, 1fr))"}
	if body == "grid-cols-none":
		return {"gridTemplateColumns": "none"}
	found = re.fullmatch(r"grid-rows-(\d+)", body)
	if found:
		return {"gridTemplateRows": f"repeat({found.group(1)}, minmax(0, 1fr))"}
	found = re.fullmatch(r"(col|row)-span-(\d+|full)", body)
	if found:
		key = "gridColumn" if found.group(1) == "col" else "gridRow"
		return {
			key: "1 / -1" if found.group(2) == "full" else f"span {found.group(2)} / span {found.group(2)}"
		}

	found = re.fullmatch(r"(items|self|justify|place-content|place-items|content)-(.+)", body)
	if found:
		kind, value = found.groups()
		if kind in {"items", "self"} and value in ALIGN | {"auto": ""}:
			return {"alignItems" if kind == "items" else "alignSelf": ALIGN.get(value, "auto")}
		if kind == "justify" and value in JUSTIFY:
			return {"justifyContent": JUSTIFY[value]}
		if kind == "place-content" and value in JUSTIFY:
			return {"placeContent": JUSTIFY[value].replace("flex-", "")}
		if kind == "place-items" and value in ALIGN:
			return {"placeItems": ALIGN[value].replace("flex-", "")}
		if kind == "content" and value in JUSTIFY:
			return {"alignContent": JUSTIFY[value]}
		return None

	size = re.fullmatch(r"text-(xs|sm|base|lg|xl|[2-9]xl)(?:/(\S+))?", body)
	if size:
		font, line = SIZES[size.group(1)]
		if size.group(2):
			line = (
				LEADING.get(size.group(2))
				or (length(size.group(2)) if re.fullmatch(r"\d+", size.group(2)) else None)
				or line
			)
		return {"fontSize": font, "lineHeight": line}
	found = re.fullmatch(r"font-(\w+)", body)
	if found and found.group(1) in WEIGHTS:
		return {"fontWeight": WEIGHTS[found.group(1)]}
	found = re.fullmatch(r"leading-(.+)", body)
	if found:
		line = LEADING.get(found.group(1)) or (
			length(found.group(1)) if re.fullmatch(r"\d+", found.group(1)) else None
		)
		return {"lineHeight": line} if line else None
	found = re.fullmatch(r"tracking-(\w+)", body)
	if found and found.group(1) in TRACKING:
		return {"letterSpacing": TRACKING[found.group(1)]}

	found = re.fullmatch(
		r"rounded(?:-(t|r|b|l|tl|tr|bl|br))?(?:-(none|sm|md|lg|xl|2xl|3xl|full|base))?", body
	)
	if found:
		radius = ROUNDED[found.group(2) or ""]
		if not found.group(1):
			return {"borderRadius": radius}
		return {f"border{corner}Radius": radius for corner in CORNERS[found.group(1)]}
	found = re.fullmatch(r"shadow(?:-(xs|sm|md|lg|xl|2xl|none))?", body)
	if found:
		return {"boxShadow": SHADOWS[found.group(1) or ""]}
	found = re.fullmatch(r"opacity-(\d+)", body)
	if found:
		return {"opacity": f"{int(found.group(1)) / 100:g}"}

	found = re.fullmatch(r"(?:border|ring)(?:-(x|y|t|r|b|l|s|e))?(?:-(\d+))?", body)
	if found:
		digits = found.group(2)
		width = "1px" if digits is None else "0" if int(digits) == 0 else f"{digits}px"
		names = {
			None: ("Top", "Right", "Bottom", "Left"),
			"x": ("Left", "Right"),
			"y": ("Top", "Bottom"),
		}.get(found.group(1)) or (SIDES[found.group(1)],)
		out = {"borderWidth": "0"} if found.group(1) else {}
		out.update({f"border{side}Width": width for side in names})
		out["borderStyle"] = "solid"
		return out
	found = re.fullmatch(r"divide-(x|y)(?:-(\d+))?", body)
	if found:
		digits = found.group(2)
		return {
			f"__divide_{found.group(1)}": "1px"
			if digits is None
			else "0"
			if int(digits) == 0
			else f"{digits}px"
		}

	found = re.fullmatch(r"(text|bg|border|ring|divide)-(.+)", body)
	if found:
		kind = {"text": "text", "bg": "bg", "border": "border", "ring": "border", "divide": "border"}[
			found.group(1)
		]
		rest = found.group(2)
		if found.group(1) == "border":
			rest = re.sub(
				r"^[xytrbles]-(?=[a-z])", "", rest
			)  # `border-b-default`: a colour for the side that has a width
		tint = colour(kind, rest)
		if tint is None:
			return None
		key = {"text": "color", "bg": "backgroundColor"}.get(
			found.group(1), "__divide_colour" if found.group(1) == "divide" else "borderColor"
		)
		return {key: tint}
	return None


def split_variants(cls: str) -> tuple[list[str], str]:
	"""`md:hover:bg-red-500` -> (['md', 'hover'], 'bg-red-500'), brackets and the important mark respected."""
	parts, depth, current = [], 0, ""
	for char in cls:
		if char == "[":
			depth += 1
		elif char == "]":
			depth -= 1
		if char == ":" and depth == 0:
			parts.append(current)
			current = ""
		else:
			current += char
	return parts, current.lstrip("!")


SHORTHAND = re.compile(r"^-?(?:p|m|gap|inset|rounded|border|ring)(?:-[^\s]*)?$|^size-")


def parse_classes(classes: list[str]):
	"""(the CSS of each level, the unknown classes, the classes left out for a state or a direction we do not draw).

	A level is the first screen width a class applies from (0 = every screen, 1 = `sm:`… 5 = `2xl:`)."""
	levels: dict[int, dict] = {i: {} for i in range(6)}
	dropped: list[str] = []
	ignored: list[str] = []
	ordered = sorted(classes, key=lambda c: 0 if SHORTHAND.match(split_variants(c)[1]) else 1)
	for cls in ordered:
		variants, util = split_variants(cls)
		level, skip = 0, False
		for variant in variants:
			if variant in BREAKPOINTS:
				level = max(level, BREAKPOINTS[variant])
			elif variant != "ltr":
				skip = True
		if skip:
			ignored.append(cls)
			continue
		props = utility(util)
		if props is None:
			dropped.append(cls)
			continue
		levels[level].update(props)
	for props in levels.values():
		stop = props.pop("__from", None) or props.pop("__via", None) or props.pop("__to", None)
		props.pop("__via", None)
		props.pop("__to", None)
		if (
			props.get("opacity") == "0"
		):  # the first frame of an entrance animation: a text nobody sees says nothing to a block
			del props["opacity"]
		clip_text = props.pop("__clip_text", None)
		if props.pop("__gradient", None) and stop and not clip_text and "backgroundColor" not in props:
			props["backgroundColor"] = replace(
				stop, alpha=1.0
			)  # a gradient of one colour: the button of a library is that colour
	return levels, dropped, ignored


def merged(levels: dict[int, dict], upto: int) -> dict:
	out: dict = {}
	for level in range(upto + 1):
		out.update(levels[level])
	return out


# ---------------------------------------------------------------- the design system


def difference(new: dict, old: dict) -> dict:
	"""What a narrower screen sets on top of a wider one: the keys that change, and the keys that go back to what the browser does."""
	out = {k: v for k, v in new.items() if old.get(k) != v}
	for key in old:
		if key not in new:
			out[key] = RESET_TO.get(key, "initial")
	return out


def cleaned(style: dict) -> dict:
	return {k: v for k, v in style.items() if not k.startswith("__")}


SHELL = {
	"position",
	"overflow",
	"backgroundColor",
	"color",
	"paddingTop",
	"paddingBottom",
	"paddingLeft",
	"paddingRight",
	"maxWidth",
	"marginLeft",
	"marginRight",
	"width",
}
SURFACE = {
	"backgroundColor",
	"borderWidth",
	"borderTopWidth",
	"borderRightWidth",
	"borderBottomWidth",
	"borderLeftWidth",
	"borderStyle",
	"borderColor",
	"boxShadow",
	"borderRadius",
}
BUTTON_KEEPS = {
	"marginTop",
	"marginRight",
	"marginBottom",
	"marginLeft",
	"width",
	"alignSelf",
	"flexShrink",
	"order",
}
PADDINGS = ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft")


class Importer:
	"""One component, turned into a block. A new `Importer` for each component (it counts pictures, icons and unknown classes)."""

	def __init__(self):
		self.words = capture.Words()
		self.photos = 0
		self.icons = 0
		self.dropped: Counter = Counter()
		self.ignored: Counter = Counter()

	# ------------------------------------------------------------ the component

	def block(self, markup: str, *, kind: str, block_id: str, title: str, source_note: str) -> dict:
		"""The hub's block (the body of its `publish_block`) for a component's markup. Raises `Refused` with the reason."""
		body = parse(markup)
		fold_accordions(body)
		for element in [body, *descendants(body)]:
			if any("bg-[url(" in c for c in element.classes):
				raise Refused("a photograph set as a background would be the same picture on every site")
		top = [c for c in body.children if isinstance(c, Element) and c.tag not in DROPPED_TAGS]
		if len(top) != 1:
			raise Refused(f"the component has {len(top)} elements at its root, a block is one section")
		ground, narrow, content = self.peel(top[0])
		if (
			narrow is None
		):  # a component page may give its width to the `<body>` (a column of questions: `mx-auto max-w-3xl`)
			width = merged(parse_classes(body.classes)[0], DESKTOP).get("maxWidth")
			if width and re.fullmatch(r"[\d.]+rem", str(width)) and float(str(width)[:-3]) < 70:
				narrow = width
		kids = self.children(content, ground)
		if len(kids) >= 2 and all(
			k["el"] == "details" for k in kids
		):  # an accordion that was the shell of the component
			kids = [{"el": "div", "name": "faq", "classes": ["u-faq"], "c": kids}]
		if narrow:
			wrap = {
				"el": "div",
				"name": "narrow",
				"style": {"maxWidth": narrow, "marginLeft": "auto", "marginRight": "auto", "width": "100%"},
				"c": kids,
			}
			kids = [wrap]
		if not kids:
			raise Refused("nothing is left of the component once its icons are dropped")
		tree = {
			"el": "section",
			"name": capture.family_of(kind),
			"style": {
				"backgroundColor": "{{ground.background}}",
				"width": "100%",
				"padding": SECTION_PADDING,
			},
			"m_style": {"padding": SECTION_PADDING_PHONE},
			"c": [
				{
					"el": "div",
					"name": "container",
					"style": {
						"maxWidth": "{{container}}",
						"width": "100%",
						"margin": "0 auto",
						"paddingLeft": "{{gutter}}",
						"paddingRight": "{{gutter}}",
					},
					"m_style": {"paddingLeft": "{{gutter_phone}}", "paddingRight": "{{gutter_phone}}"},
					"c": kids,
				}
			],
		}
		demote_headings(tree)
		if kind == "faq":
			group = _largest_group(tree)
			if not group or len(list(slot_nodes(group[1][0]))) < 2:
				raise Refused(
					"questions with no answers: each question of a FAQ block holds its answer (a folding question, or a title and a text)"
				)
		if kind in NEEDS_A_GROUP and not has_group(tree):
			raise Refused(
				"one card, not a section: nothing in it repeats (a block of this kind is a row or a grid of items)"
			)
		if kind == "brand-row" and self.photos < 2:
			raise Refused(
				"a row of brands without its logos (the logos are inline SVG, a block has no tag for them)"
			)
		if len(self.dropped) > MAX_UNKNOWN_CLASSES:
			raise Refused(
				f"{len(self.dropped)} classes are not understood ({', '.join(sorted(self.dropped)[:8])}…)"
			)
		if self.photos > block_format.MAX_PHOTOS:
			raise Refused(f"{self.photos} pictures, a block holds {block_format.MAX_PHOTOS} at most")
		errors, _warnings = block_format.lint(
			tree, block_id=block_id, kinds=[kind], photos=self.photos, form=False, motion="None"
		)
		if errors:
			raise Refused(errors[0])
		return {
			"id": block_id,
			"title": title,
			"kinds": [kind],
			"look": describe_layout(tree, kind, ground, self.photos),
			"photos": self.photos,
			"form": False,
			"ground": ground,
			"motion": "None",
			"notes": self.notes(source_note),
			"tree": tree,
		}

	def notes(self, source_note: str) -> str:
		said = [source_note]
		if self.icons:
			said.append(
				f"{self.icons} icon{'s' if self.icons > 1 else ''} of the source left out (a block has no tag for an icon)."
			)
		if self.dropped:
			said.append(f"Classes not drawn: {', '.join(sorted(self.dropped))}.")
		said.append(
			"It carries no words and no picture of the source, only its structure, drawn with the design system. Read it, correct its look line, then publish it."
		)
		return " ".join(said)

	# ------------------------------------------------------------ the shell of the component

	def peel(self, root: Element):
		"""(the ground, a narrow max-width of the shell, the element whose children are the content).

		A component's outer elements only say how wide it is, how much air it has and what it stands on (`mx-auto max-w-7xl px-4 py-8`, `bg-gray-900`): the
		block's own section and container say that, with the site's tokens. Peeled elements are walked while they hold one element and nothing else."""
		background, narrow = None, None

		def absorb(props: dict) -> None:
			nonlocal background, narrow
			background = background or props.get("backgroundColor")
			width = props.get("maxWidth")
			if width and re.fullmatch(r"[\d.]+rem", str(width)) and float(str(width)[:-3]) < 70:
				narrow = width

		node = root
		while True:
			levels, unknown, _ignored = parse_classes(node.classes)
			self.dropped.update(unknown)
			props = merged(levels, DESKTOP)
			kids = [c for c in node.children if isinstance(c, Element) and c.tag not in DROPPED_TAGS]
			quiet = all(isinstance(c, Element) or not c.strip() for c in node.children)
			if set(props) <= SHELL and node.tag in SHELL_TAGS and len(kids) == 1 and quiet:
				absorb(props)
				node = kids[0]
				continue
			break
		if set(props) <= SHELL and node.tag in SHELL_TAGS:
			absorb(props)  # the last shell element holds the content itself
			return ground_of(background), narrow, node
		# the last element is content: its width and its air are the block's, its other utilities are its own
		absorb({k: v for k, v in props.items() if k == "maxWidth"})
		holder = Element("div", {})
		holder.children = [node]
		holder.shell_strip = True
		return ground_of(background), narrow, holder

	# ------------------------------------------------------------ the tree

	def children(self, parent: Element, ground: str, parent_levels: dict | None = None) -> list[dict]:
		"""The nodes of an element's children, in order. `parent_levels`: the CSS of the parent, whose `space-*` and `divide-*` its children carry."""
		out: list[dict] = []
		strip = SHELL if getattr(parent, "shell_strip", False) else None
		for child in parent.children:
			if isinstance(child, str):
				if child.strip():
					out.append(self.text_node("span", clean(child), {}, ground))
				continue
			rule = self.between(parent_levels, len(out)) if out and parent_levels else {}
			node = self.element(child, ground, rule, strip=strip, fold=parent.tag == "details")
			if node is not None:
				out.append(node)
		if out:
			for key in ("style", "t_style", "m_style"):
				if key in out[0]:
					out[0][key].pop("marginTop", None)
					if not out[0][key]:
						del out[0][key]
		self.unify(out)
		return out

	@staticmethod
	def unify(kids: list[dict]) -> None:
		"""Siblings drawn the same way (the cards of a grid, the rows of a list) ask for the same words: the role most of them have, the length of the
		first one that has it. The source's placeholder texts are of any length, the block's slots are not."""
		groups: dict = {}
		for kid in kids:
			groups.setdefault(signature(kid), []).append(kid)
		for same in groups.values():
			# two paragraphs side by side are a title and a text, not a pair: only containers and the entries of a list repeat
			if len(same) < 2 or not (same[0].get("c") or same[0]["el"] == "li"):
				continue
			columns = list(zip(*[list(slot_nodes(kid)) for kid in same], strict=True))
			for column in columns:
				roles = Counter(block_format.SLOT.match(n["text"]).group(1) for n in column)
				best = max(
					roles,
					key=lambda role: (
						roles[role],
						-[block_format.SLOT.match(n["text"]).group(1) for n in column].index(role),
					),
				)
				model = next(n["text"] for n in column if block_format.SLOT.match(n["text"]).group(1) == best)
				for n in column:
					n["text"] = model
					n["name"] = best

	@staticmethod
	def between(levels: dict, index: int) -> dict:
		"""The CSS the second child onwards of a parent gets from its `space-y-*` / `divide-x`…"""
		rule: dict[int, dict] = {i: {} for i in range(6)}
		for level, props in levels.items():
			for key, value in props.items():
				if key == "__space_y":
					rule[level]["marginTop"] = value
				elif key == "__space_x":
					rule[level]["marginLeft"] = value
				elif key == "__divide_y":
					rule[level].update({"borderWidth": "0", "borderTopWidth": value, "borderStyle": "solid"})
				elif key == "__divide_x":
					rule[level].update({"borderWidth": "0", "borderLeftWidth": value, "borderStyle": "solid"})
				elif key == "__divide_colour":
					rule[level]["borderColor"] = value
		return rule

	def element(
		self, el: Element, ground: str, inherited: dict, strip=None, fold: bool = False
	) -> dict | None:
		if el.tag == "svg":
			self.icons += 1
			return None
		if el.tag in DROPPED_TAGS:
			return None
		if el.tag in REFUSED_TAGS:
			raise Refused(REFUSED_TAGS[el.tag])
		tag = RENAMED.get(el.tag, el.tag)
		if tag == "section":
			tag = "div"  # the block's own section is the only one
		if tag not in block_format.TAGS:
			raise Refused(f"`<{el.tag}>` is not a tag a block may hold")
		if "sr-only" in el.classes or self.is_decoration(el) or self.is_chrome(el):
			return None
		levels, dropped, ignored = parse_classes(el.classes)
		self.dropped.update(dropped)
		self.ignored.update(ignored)
		for level, props in (inherited or {}).items():
			levels[level] = {**props, **levels[level]}
		if strip and tag != "img" and not self.is_text_run(el):
			levels = {
				level: {k: v for k, v in props.items() if k not in strip} for level, props in levels.items()
			}

		if el.tag == "br":
			return None
		if all(merged(levels, width).get("display") == "none" for width in (DESKTOP, TABLET, PHONE)):
			return None  # hidden on every screen (the dark twin of a picture that has a light one)
		if tag != "img" and not any(isinstance(c, Element) and c.tag == "img" for c in el.children):
			# a box that clips is a box a reveal never plays under; only the box of a picture needs to clip it
			levels = {
				level: {
					k: v
					for k, v in props.items()
					if not (
						k in {"overflow", "overflowX", "overflowY"}
						and props[k] in {"hidden", "auto", "scroll"}
					)
				}
				for level, props in levels.items()
			}
		desktop = merged(levels, DESKTOP)
		parent_levels = levels
		kids_text = self.is_text_run(el)
		role = self.pattern(el, tag, desktop, kids_text)
		if tag == "details":
			# a question that folds is drawn by the site's accordion (`u-faq`): what the source gave its box, its rule and its air is not kept
			role, kids_text = "fold", False
			levels = {level: {} for level in levels}
		elif tag == "summary":
			# the question is the words of the summary, in the type of the summary or of the heading inside it
			role, kids_text = "question", True
			heading = next((c for c in descendants(el) if c.tag in HEADING_TAGS), None)
			typed = parse_classes(heading.classes)[0] if heading else {i: {} for i in range(6)}
			levels = {
				level: {k: v for k, v in {**props, **typed[level]}.items() if k in TYPE_KEYS}
				for level, props in levels.items()
			}
		surface = desktop.get("backgroundColor")
		switched = role != "button" and isinstance(surface, Colour) and surface.dark and ground != "deep"
		own_ground = "deep" if switched else ground
		node: dict = {"el": tag}
		classes: list[str] = []

		if role == "button":
			node["el"] = "a"
			node["attrs"] = {"href": "{{cta_href}}"}
			classes = ["u-btn", self.button_class(desktop, own_ground)]
			levels = {
				level: {k: v for k, v in props.items() if k in BUTTON_KEEPS}
				for level, props in levels.items()
			}
		elif role == "card":
			classes = ["u-card"]
			levels = {
				level: {
					k: v
					for k, v in props.items()
					if k not in SURFACE or (switched and k == "backgroundColor")
				}
				for level, props in levels.items()
			}
			if all(desktop.get(p) == "1.5rem" for p in PADDINGS):
				levels = {
					level: {k: v for k, v in props.items() if k not in PADDINGS}
					for level, props in levels.items()
				}

		if tag == "a" and role != "button":
			node["attrs"] = {"href": "{{cta_href}}"}
		if tag == "img":
			number = self.photos
			self.photos += 1
			if number >= block_format.MAX_PHOTOS:
				return None  # counted: the block is refused for it
			node["attrs"] = {
				"src": f"{{{{photo.{number}}}}}",
				"alt": section_recipes.slot("alt", section_recipes.ALT_GUIDANCE),
			}
			base = levels[0]
			# a picture with a height of its own and no width keeps its proportions (a logo); `h-auto max-w-full` is the picture that fills its cell
			sized = desktop.get("height") not in (None, "auto") and "width" not in desktop
			if "width" not in desktop:
				base["width"] = "auto" if sized else "100%"
			if "objectFit" not in desktop:
				base["objectFit"] = "contain" if sized else "cover"
			base.setdefault("display", "block")
		if tag == "hr":
			levels[0] = {
				"width": "100%",
				"borderWidth": "0",
				"borderTopWidth": "1px",
				"borderStyle": "solid",
				**levels[0],
			}

		text = ""
		kids: list[dict] = []
		if tag not in {"img", "hr"}:
			if kids_text:
				text = clean(text_of(el))
				self.icons += sum(1 for c in el.children if isinstance(c, Element) and c.tag == "svg")
				if not text:
					return None
			else:
				kids = self.children(el, own_ground, parent_levels)
				if not kids and any(isinstance(c, Element) for c in el.children):
					return None  # nothing left once the icons are gone: an icon's frame

		# the questions of a list are spaced and ruled by the site's accordion, what lays them out in the source is not kept
		is_faq = len(kids) >= 2 and all(k["el"] == "details" for k in kids)
		if is_faq:
			levels = {
				level: {k: v for k, v in props.items() if k not in FAQ_FLOW}
				for level, props in levels.items()
			}
		if (
			fold and role != "question"
		):  # the answer under a question keeps its type, the accordion gives it its air
			levels = {
				level: {k: v for k, v in props.items() if k in TYPE_KEYS | {"maxWidth"}}
				for level, props in levels.items()
			}
		resolved = {level: self.paint(props, own_ground, switched) for level, props in levels.items()}
		if role != "button":
			self.defaults(resolved, tag, text)
		if fold and role != "question":
			resolved[0].pop("margin", None)

		style_desktop = cleaned(merged(resolved, DESKTOP))
		tablet = cleaned(merged(resolved, TABLET))
		phone = cleaned(merged(resolved, PHONE))
		style, t_style, m_style = style_desktop, difference(tablet, style_desktop), difference(phone, tablet)

		if text:
			words = capture._range(len(text.split()))
			if role == "question":
				node["text"] = section_recipes.slot("question", f"a real question a customer asks, {words}")
			elif fold:
				node["text"] = section_recipes.slot(
					"answer", f"an answer of {words} from the business's own facts"
				)
			else:
				node["text"] = self.slot({"el": node["el"], "classes": classes, "style": style}, text)
		node["name"] = self.name(node, role, style, kids)
		if is_faq:
			classes, node["name"] = [*classes, "u-faq"], "faq"
		if classes:
			node["classes"] = classes
		if switched:
			node["ground"] = "deep"
		for key, value in (("style", style), ("t_style", t_style), ("m_style", m_style)):
			if value:
				node[key] = value
		if kids:
			node["c"] = kids
		return {
			k: node[k]
			for k in ("el", "name", "classes", "ground", "style", "t_style", "m_style", "attrs", "text", "c")
			if k in node
		}

	@staticmethod
	def is_chrome(el: Element) -> bool:
		"""The navigation of a site (a `<nav>`): a component page often draws it above its hero, the block is the section. A `<header>` that held only
		the navigation is empty once it is gone and goes with it; one that holds the hero's words stays."""
		return el.tag == "nav"

	@staticmethod
	def is_decoration(el: Element) -> bool:
		"""A glow, a beam, a mask: an element that is there to be looked at and says nothing (`data-slot="glow"`, `aria-hidden`, or an absolute box with no
		word and no picture in it)."""
		if (
			el.attrs.get("data-slot") in {"glow", "beam", "layout-lines"}
			or el.attrs.get("aria-hidden") == "true"
		):
			return True
		if (
			"absolute" in el.classes
			and not clean(text_of(el))
			and not any(c.tag == "img" for c in descendants(el))
		):
			# an empty box laid over its parent (a veil, a glow), not the small dot of a timeline
			return any(
				c in {"w-full", "h-full", "size-full", "pointer-events-none"} or c.startswith("inset-")
				for c in el.classes
			)
		return False

	def is_text_run(self, el: Element) -> bool:
		"""Whether an element holds words and inline things only (a paragraph with a `<strong>`), so that it is one text, not a group."""
		if el.tag in {"img", "hr", "br"}:
			return False
		words = False
		for child in el.children:
			if isinstance(child, str):
				words = words or bool(child.strip())
				continue
			if child.tag not in INLINE or self.looks_like_button(child):
				return False
			if child.tag != "svg" and not self.is_text_run(child) and child.tag != "br":
				return False
			words = words or bool(clean(text_of(child)))
		return words

	def looks_like_button(self, el: Element) -> bool:
		if el.tag not in {"a", "button"}:
			return False
		levels, _d, _i = parse_classes(el.classes)
		props = merged(levels, DESKTOP)
		padded = any(k.startswith("padding") for k in props)
		return (
			padded
			and ("backgroundColor" in props or any(k.startswith("border") for k in props))
			and self.is_text_run(el)
		)

	def pattern(self, el: Element, tag: str, desktop: dict, is_text: bool) -> str | None:
		if tag == "a" and is_text and self.looks_like_button(el):
			return "button"
		holds = any(isinstance(c, Element) and c.tag != "svg" for c in el.children) or bool(
			clean(text_of(el))
		)
		if (
			holds
			and tag in {"div", "article", "li", "blockquote", "figure", "a"}
			and "borderRadius" in desktop
		):
			bordered = all(
				str(desktop.get(f"border{side}Width", "0")) != "0"
				for side in ("Top", "Right", "Bottom", "Left")
			)
			if bordered or "boxShadow" in desktop:
				return "card"
		return None

	@staticmethod
	def button_class(desktop: dict, ground: str) -> str:
		background = desktop.get("backgroundColor")
		if isinstance(background, Colour) and background.family != "transparent" and background.alpha >= 0.9:
			if background.light and ground != "deep":
				return "u-btn--outline"  # a pale button beside the main one is the quiet one
			return "u-btn--secondary" if ground == "deep" else "u-btn--primary"
		return "u-btn--outline"

	@staticmethod
	def paint(props: dict, ground: str, switched: bool) -> dict:
		"""The CSS of a level with every colour turned into the token of the role it plays on this ground."""
		out = {}
		for key, value in props.items():
			if isinstance(value, Colour):
				if key == "backgroundColor" and switched and value.dark:
					out[key] = "{{ground.background}}"
				else:
					out[key] = resolve_colour(value, ground)
			else:
				out[key] = value
		if (
			any(k.startswith("border") and k.endswith("Width") for k in out)
			and "borderColor" not in out
			and "__divide_colour" not in out
		):
			out["borderColor"] = "{{ground.hair}}"
		return out

	def defaults(self, resolved: dict, tag: str, text: str) -> None:
		"""A text node is drawn with the site's fonts and the ink of its ground, its margins are its own."""
		base = resolved[0]
		if text or tag in TEXT_TAGS:
			heading = tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
			base.setdefault("fontFamily", "{{font_heading}}" if heading else "{{font_body}}")
			if not any("color" in props for props in resolved.values()):
				base["color"] = "{{ground.ink}}"
		if tag in {"ul", "ol"}:
			base.setdefault("listStyleType", "none")
			base.setdefault("paddingLeft", "0")
		if tag in RESET_MARGIN:
			resolved[0] = {"margin": "0", **base}

	def slot(self, node: dict, text: str) -> str:
		plain = capture._plain(text)
		if FIGURE_TEXT.match(plain) and capture._size(node["style"]) >= 1.75:
			return section_recipes.slot(
				"figure", "one number in digits, a quantity the material gives, never a year, never invented"
			)
		if node["el"] == "a" and not any(c.startswith("u-btn") for c in node["classes"]):
			return section_recipes.slot("caption", capture._range(len(plain.split())))
		return self.words.slot(node, text)

	def text_node(self, tag: str, text: str, style: dict, ground: str) -> dict:
		node = {"el": tag, "style": {"fontFamily": "{{font_body}}", "color": "{{ground.ink}}", **style}}
		node["text"] = self.slot({"el": tag, "classes": [], "style": node["style"]}, text)
		node["name"] = "text"
		return {k: node[k] for k in ("el", "name", "style", "text")}

	@staticmethod
	def name(node: dict, role: str | None, style: dict, kids: list[dict]) -> str:
		"""The name the Builder shows for the node in its layers."""
		slot = block_format.SLOT.match(node.get("text") or "")
		if slot:
			return slot.group(1)
		el = node["el"]
		if el == "img":
			return "photo"
		if el == "hr":
			return "rule"
		if role == "button":
			return "button"
		if role == "card":
			return "card"
		if role == "fold":
			return "question"
		if el == "div" and kids and kids[0].get("name") in {"heading", "item-title"}:
			return "head"
		display = style.get("display")
		if display in {"grid", "inline-grid"}:
			return "grid"
		if display in {"flex", "inline-flex"}:
			return "column" if style.get("flexDirection") == "column" else "row"
		return {"ul": "list", "ol": "list", "li": "entry", "figure": "figure", "blockquote": "quote"}.get(
			el, "box" if el == "div" else el
		)


def signature(node: dict) -> tuple:
	"""What a node is made of, without its words: two nodes with the same signature are drawn the same way."""
	return (node["el"], tuple(node.get("classes") or ()), tuple(signature(c) for c in node.get("c") or ()))


def slot_nodes(node: dict):
	"""The nodes of a tree that ask for words, in reading order."""
	if block_format.SLOT.match(node.get("text") or ""):
		yield node
	for child in node.get("c") or []:
		yield from slot_nodes(child)


# what a kind of section is for, said the way the plan's own catalogue says it: the plan reads one line per block and picks by it
SUITS = {
	"hero": "the first screen of a page",
	"cta": "an invitation to act, a closing band",
	"feature-grid": "what the business offers, at a glance",
	"figures": "proof in numbers",
	"testimonials": "what clients say",
	"team": "the people behind the business",
	"pricing": "plans or fees side by side",
	"faq": "practical questions, a reference page",
	"gallery": "pictures that carry the section",
	"cards": "articles, projects or products",
	"product-row": "products in a row",
	"two-column": "words beside a photograph",
	"steps": "how it works, in order",
}
ROLE_NOUN = {
	"item-title": "a title",
	"item-text": "a text",
	"text": "a text",
	"caption": "a short line",
	"label": "a small label",
	"figure": "a figure",
	"numeral": "a numeral",
	"button": "a button",
	"question": "a question",
	"answer": "an answer",
	"lead": "a text",
	"heading": "a title",
	"quote": "a quotation",
}


def _walk(node: dict, inherited: str = "left"):
	"""(node, the text alignment it inherits) for each node of a tree, in reading order."""
	align = str((node.get("style") or {}).get("textAlign") or inherited)
	yield node, align
	for child in node.get("c") or []:
		yield from _walk(child, align)


def _largest_group(node: dict):
	"""The biggest set of children drawn the same way under one node (the cards of a grid, the entries of a list), as (parent, kids); None when nothing repeats."""
	best = None
	groups: dict = {}
	for kid in node.get("c") or []:
		if kid.get("c") or kid["el"] == "li":
			groups.setdefault(signature(kid), []).append(kid)
	for kids in groups.values():
		if len(kids) >= 2 and (best is None or len(kids) > len(best[1])):
			best = (node, kids)
	for kid in node.get("c") or []:
		below = _largest_group(kid)
		if below and (best is None or len(below[1]) > len(best[1])):
			best = below
	return best


def describe_layout(tree: dict, kind: str, ground: str, photos: int) -> str:
	"""A line for the plan, from the structure only (nothing of the business, nothing of the source): how the section is laid out and what it suits.
	The plan chooses a block by reading it, so a line that says only `a band` leaves the plan with the recipes it already knows."""
	nodes = list(_walk(tree))
	roles = Counter(
		block_format.SLOT.match(n["text"]).group(1)
		for n, _a in nodes
		if block_format.SLOT.match(n.get("text") or "")
	)
	heading = next(((n, a) for n, a in nodes if (n.get("name") == "heading")), None)
	big_head = heading is not None and capture._size(heading[0].get("style") or {}) >= 3.5
	opening = ""
	if heading:
		opening = f"a {'centred' if heading[1] == 'center' else 'left-aligned'} {'large headline' if big_head else 'heading'}"
		if roles.get("lead") or roles.get("text"):
			opening += " and a short text"
	group = _largest_group(tree)
	body = ""
	if group:
		parent, kids = group
		first = kids[0]
		count = len(kids)
		cls = {c for n, _a in _walk(first) for c in n.get("classes") or []}
		if first["el"] == "details":
			noun, shape = "folding questions", ""
		else:
			pill = any(
				n["el"] == "img" and "pill" in str((n.get("style") or {}).get("borderRadius", ""))
				for n, _a in _walk(first)
			)
			noun = (
				("round portraits" if kind == "team" else "cards")
				if pill
				else "cards"
				if "u-card" in cls or "u-card" in (first.get("classes") or [])
				else "entries"
				if first["el"] == "li"
				else "items"
			)
			held = [
				ROLE_NOUN[r]
				for r in dict.fromkeys(block_format.SLOT.match(n["text"]).group(1) for n in slot_nodes(first))
				if r in ROLE_NOUN
			]
			if any(n["el"] == "img" for n, _a in _walk(first)):
				if not pill:
					held.insert(0, "a photograph")
				elif kind != "team":
					held.insert(0, "a round photograph")
			held = list(dict.fromkeys(held[:4]))
			shape = (
				", each holding " + (", ".join(held[:-1]) + " and " + held[-1] if len(held) > 1 else held[0])
				if held
				else ""
			)
		columns = re.search(r"repeat\((\d+)", str((parent.get("style") or {}).get("gridTemplateColumns", "")))
		body = (
			f"{count} {noun}"
			+ (
				" in one column"
				if noun == "folding questions"
				else f" in {columns.group(1)} columns"
				if columns and noun != "round portraits"
				else " side by side"
				if parent.get("style", {}).get("display") in {"grid", "flex"}
				else ""
			)
			+ shape
		)
	inside = {
		id(n) for kid in (group[1] if group else []) for n, _a in _walk(kid)
	}  # what the items of the group hold is said by the group
	buttons = [n for n, _a in nodes if "u-btn" in (n.get("classes") or []) and id(n) not in inside]
	extras = []
	if buttons:
		outlined = sum("u-btn--outline" in (b.get("classes") or []) for b in buttons)
		if len(buttons) >= 2 and outlined:
			extras.append("a button and a quieter one in outline")
		elif len(buttons) >= 2:
			extras.append(f"{len(buttons)} buttons")
		else:
			extras.append("a button")
	figures = roles.get("figure", 0)
	if figures and not group:
		extras.append(f"{figures} large figures")
	if photos and not any(n["el"] == "img" for kid in (group[1] if group else []) for n, _a in _walk(kid)):
		extras.append("a photograph" if photos == 1 else f"{photos} photographs")
	parts = [p for p in [opening, body] if p]
	line = " over ".join(parts) if opening and body else (opening or body or "a single band")
	if extras:
		line += ", with " + " and ".join(extras)
	ground_phrase = {"plain": "on the plain ground", "tint": "on a tinted ground", "deep": "on a deep band"}[
		ground
	]
	suits = SUITS.get(kind)
	return f"{line}; {ground_phrase}" + (f"; for {suits}." if suits else ".")


# the kinds of section that are a row or a grid of items: a component that is one card is not one
NEEDS_A_GROUP = {"cards", "product-row"}


def has_group(node: dict) -> bool:
	"""Whether some node of a tree holds two or more children drawn the same way (the cards of a grid, the entries of a list)."""
	kids = node.get("c") or []
	seen: set = set()
	for kid in kids:
		sig = signature(kid)
		if (kid.get("c") or kid["el"] == "li") and sig in seen:
			return True
		seen.add(sig)
	return any(has_group(kid) for kid in kids)


def demote_headings(node: dict) -> None:
	"""A heading that is repeated (the title of each card) is an `item-title`: a section has one `heading`."""
	kids = node.get("c") or []
	groups: dict = {}
	for kid in kids:
		groups.setdefault(signature(kid), []).append(kid)
	for same in groups.values():
		if len(same) >= 2:
			for kid in same:
				for n in slot_nodes(kid):
					if n["text"].startswith("WRITE heading:"):
						n["text"] = n["text"].replace("WRITE heading:", "WRITE item-title:", 1)
						n["name"] = "item-title"
	for kid in kids:
		demote_headings(kid)


def without_duplicates(made: dict[str, dict], refused: dict[str, str]) -> None:
	"""Variants that differ only by what the design system replaces (a box, a rule, a colour) come out the same: the first is kept, the others are
	said to be the same block."""
	seen: dict[str, str] = {}
	for label in list(made):
		print_ = capture.fingerprint(made[label]["tree"])
		if print_ in seen:
			refused[label] = f"the same block as {seen[print_]} once the design system is applied"
			del made[label]
		else:
			seen[print_] = label


PUSH_WAIT = 30  # seconds between two tries when the hub says it is asked too often
PUSH_TRIES = 8


def push_all(made: dict[str, dict]) -> dict[str, str]:
	"""Sends each block to the hub as a draft, one line of what happened per block. The hub limits how often a publisher may ask (HTTP 429): the block
	is tried again after a wait, so that a long import is not half sent."""
	import time

	sent: dict[str, str] = {}
	for label, block in made.items():
		line = ""
		for _try in range(PUSH_TRIES):
			line = capture.push_block(block)
			if "429" not in line:
				break
			time.sleep(PUSH_WAIT)
		sent[label] = line
	return sent


def import_markup(markup: str, *, kind: str, block_id: str, title: str, source_note: str) -> dict:
	"""The block of one component's markup. Raises `Refused` with the reason."""
	return Importer().block(markup, kind=kind, block_id=block_id, title=title, source_note=source_note)


# ---------------------------------------------------------------- HyperUI


def hyperui_id(category: str, number: int, kind: str) -> str:
	return f"{capture.family_of(kind)}.hu-{category}-{number}"


def hyperui_note(category: str, number: int, source: dict = HYPERUI) -> str:
	return (
		f"Imported from {source['name']} (examples/marketing/{category}/{number}.html at {source['ref'][:10]}), {source['licence']} licence, "
		f"Copyright (c) {source['holder']}, {source['url']}."
	)


def import_hyperui_markup(category: str, number: int, markup: str) -> dict:
	kind = HYPERUI_KINDS[category]
	title = f"{kind.replace('-', ' ').capitalize()} {number} ({HYPERUI['name']})"
	return import_markup(
		markup,
		kind=kind,
		block_id=hyperui_id(category, number, kind),
		title=title,
		source_note=hyperui_note(category, number),
	)


def fetch_hyperui(category: str, number: int) -> str:
	import requests

	response = requests.get(
		HYPERUI["raw"].format(ref=HYPERUI["ref"], category=category, number=number), timeout=30
	)
	response.raise_for_status()
	return response.text


def import_hyperui(categories=None, push: bool = False) -> dict:
	"""For `bench execute`: the HyperUI marketing components that can be blocks, and why the others cannot; with `push` they go to the hub as drafts."""
	made: dict[str, dict] = {}
	refused: dict[str, str] = {}
	for category in categories or HYPERUI_KINDS:
		for number in range(1, HYPERUI_COUNT[category] + 1):
			label = f"{category}/{number}"
			try:
				block = import_hyperui_markup(category, number, fetch_hyperui(category, number))
			except Refused as e:
				refused[label] = str(e)
				continue
			except Exception as e:
				refused[label] = f"not read ({type(e).__name__})"
				continue
			made[label] = block
	without_duplicates(made, refused)
	sent = push_all(made) if push else {}
	return {"blocks": {label: block["id"] for label, block in made.items()}, "refused": refused, "sent": sent}


# ---------------------------------------------------------------- Flowbite

FLOWBITE = {
	"name": "Flowbite",
	"url": "https://github.com/themesberg/flowbite",
	"licence": "MIT",
	"holder": "Bergside Inc.",
	"ref": "232ebdb33a9e37b31b293b9988d89b862ee121e5",
	"raw": "https://raw.githubusercontent.com/themesberg/flowbite/{ref}/content/components/{component}.md",
}
# the components of Flowbite that are a section of a site (the others are the pieces of an application: a modal, a dropdown, a table), and the
# kind of section each one is. Its marketing blocks are a paid product and are not here.
FLOWBITE_KINDS = {"jumbotron": "hero", "accordion": "faq", "timeline": "steps", "gallery": "gallery"}
# a page of the documentation holds its examples between two shortcodes, each under a `##` title
FLOWBITE_EXAMPLE = re.compile(
	r"\{\{<\s*example\b[^>]*>\}\}[ \t]*\n(.*?)\n[ \t]*\{\{<\s*/example\s*>\}\}", re.DOTALL
)
FLOWBITE_TITLE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
FLOWBITE_SHORTCODE = re.compile(r"\{\{<.*?>\}\}|\{\{%.*?%\}\}", re.DOTALL)


def flowbite_examples(markdown: str) -> list[tuple[str, str]]:
	"""(title, markup) of each example of a Flowbite component page: the title is the `##` heading above it, the markup has no shortcode left."""
	found = []
	for match in FLOWBITE_EXAMPLE.finditer(markdown):
		titles = FLOWBITE_TITLE.findall(markdown[: match.start()])
		found.append((titles[-1] if titles else "", FLOWBITE_SHORTCODE.sub("", match.group(1))))
	return found


def flowbite_id(component: str, number: int, kind: str) -> str:
	return f"{capture.family_of(kind)}.fb-{component}-{number}"


def flowbite_note(component: str, number: int, title: str, source: dict = FLOWBITE) -> str:
	return (
		f"Imported from {source['name']} (content/components/{component}.md, example {number}, \u00ab {title} \u00bb, at {source['ref'][:10]}), "
		f"{source['licence']} licence, Copyright (c) {source['holder']}, {source['url']}."
	)


def import_flowbite_markup(component: str, number: int, title: str, markup: str) -> dict:
	kind = FLOWBITE_KINDS[component]
	return import_markup(
		markup,
		kind=kind,
		block_id=flowbite_id(component, number, kind),
		title=f"{kind.replace('-', ' ').capitalize()} {number} (Flowbite)",
		source_note=flowbite_note(component, number, title),
	)


def fetch_flowbite(component: str) -> str:
	import requests

	response = requests.get(FLOWBITE["raw"].format(ref=FLOWBITE["ref"], component=component), timeout=30)
	response.raise_for_status()
	return response.text


def import_flowbite(components=None, push: bool = False) -> dict:
	"""For `bench execute`: the examples of Flowbite's section components that can be blocks, and why the others cannot; with `push` they go to the
	hub as drafts."""
	made: dict[str, dict] = {}
	refused: dict[str, str] = {}
	for component in components or FLOWBITE_KINDS:
		try:
			examples = flowbite_examples(fetch_flowbite(component))
		except Exception as e:
			refused[component] = f"not read ({type(e).__name__})"
			continue
		for number, (title, markup) in enumerate(examples, start=1):
			label = f"{component}/{number}"
			try:
				made[label] = import_flowbite_markup(component, number, title, markup)
			except Refused as e:
				refused[label] = f"{title}: {e}"
			except Exception as e:
				refused[label] = f"{title}: not read ({type(e).__name__})"
	without_duplicates(made, refused)
	sent = push_all(made) if push else {}
	return {"blocks": {label: block["id"] for label, block in made.items()}, "refused": refused, "sent": sent}


# ---------------------------------------------------------------- launch-ui

LAUNCH_UI = {
	"name": "launch-ui",
	"url": "https://github.com/launch-ui/launch-ui",
	"licence": "MIT",
	"holder": "Mikolaj Dobrucki",
	"ref": "b0d4d5bce91d13523450416ce1797109076b2787",
}
# the sections of launch-ui that are a section of a site (its navbar and its footer are the chrome of a site, not one of its sections)
LAUNCH_UI_KINDS = {
	"hero": "hero",
	"cta": "cta",
	"items": "feature-grid",
	"faq": "faq",
	"pricing": "pricing",
	"stats": "figures",
	"logos": "brand-row",
}


def launch_ui_note(section: str, source: dict = LAUNCH_UI) -> str:
	return (
		f"Imported from {source['name']} (components/sections/{section}/default.tsx at {source['ref'][:10]}, its components run as written and "
		f"rendered to static HTML, scripts/import-launch-ui), {source['licence']} licence, Copyright (c) 2024 {source['holder']}, {source['url']}."
	)


def import_launch_ui_markup(section: str, markup: str) -> dict:
	kind = LAUNCH_UI_KINDS[section]
	return import_markup(
		markup,
		kind=kind,
		block_id=f"{capture.family_of(kind)}.lu-{section}",
		title=f"{kind.replace('-', ' ').capitalize()} (Launch UI)",
		source_note=launch_ui_note(section),
	)


def import_launch_ui(folder: str, sections=None, push: bool = False) -> dict:
	"""For `bench execute`: the sections of launch-ui, rendered to HTML in `folder` (scripts/import-launch-ui/render.mjs, one `<section>.html` each),
	that can be blocks, and why the others cannot; with `push` they go to the hub as drafts."""
	import os

	made: dict[str, dict] = {}
	refused: dict[str, str] = {}
	for section in sections or LAUNCH_UI_KINDS:
		path = os.path.join(folder, f"{section}.html")
		try:
			with open(path, encoding="utf-8") as f:
				made[section] = import_launch_ui_markup(section, f.read())
		except FileNotFoundError:
			refused[section] = "not rendered (no HTML for it in the folder)"
		except Refused as e:
			refused[section] = str(e)
		except Exception as e:
			refused[section] = f"not read ({type(e).__name__})"
	without_duplicates(made, refused)
	sent = push_all(made) if push else {}
	return {"blocks": {label: block["id"] for label, block in made.items()}, "refused": refused, "sent": sent}


# ---------------------------------------------------------------- Meraki UI

MERAKI = {
	"name": "Meraki UI",
	"url": "https://github.com/merakiuilabs/merakiui",
	"licence": "MIT",
	"holder": "Khatab Wedaa",
	"ref": "fe0472efe93f6cd275424ecbdfa7f6cb8da6f908",
	"raw": "https://raw.githubusercontent.com/merakiuilabs/merakiui/{ref}/components/{category}/{name}.html",
}
# a category of Meraki UI's components, the kind of section it is, and its files (pinned to the commit above)
MERAKI_KINDS = {
	"heros": "hero",
	"features": "feature-grid",
	"faq": "faq",
	"cta": "cta",
	"pricing": "pricing",
	"teams": "team",
	"testimonials": "testimonials",
	"portfolio": "gallery",
	"blog": "cards",
}
MERAKI_FILES = {
	"heros": [
		"BackgroundImage",
		"CenterContent",
		"CenterContentWithTrustedBy",
		"ComingSoon",
		"E-commerce",
		"Image",
		"ImageWithNewsletter",
		"NewsletterForm",
		"Pattern",
		"SideImage",
		"Slide",
	],
	"features": ["Cards", "Centered", "GrdiList", "GridListWithImage", "Media", "Simple", "TrustedBy"],
	"faq": ["Cards", "Centered", "Collapse", "CollapseWithSideLinks", "Grid"],
	"cta": ["Card", "Centered", "Form", "Grid", "Image", "Simple"],
	"pricing": [
		"Centered",
		"Checkbox",
		"CheckboxWithDetails",
		"Navigation",
		"Popular",
		"SideBySide",
		"Simple",
	],
	"teams": ["Background", "Cards", "Cards2x2", "Filter", "GridList", "SideBySide", "Simple"],
	"testimonials": [
		"Card",
		"Centered",
		"Centered2",
		"FullPage",
		"FullPageCards",
		"Single",
		"Single2",
		"Slider",
	],
	"portfolio": ["Cards", "Centered", "Filter", "HoverEffect", "SideLinks"],
	"blog": ["Cards", "Centered", "Grid", "RecentPosts", "SinglePost", "SinglePostWithRecent"],
}


def meraki_slug(name: str) -> str:
	"""`CenterContentWithTrustedBy` -> `center-content-with-trusted-by`, `E-commerce` -> `e-commerce`."""
	return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", name).lower()


def meraki_id(category: str, name: str, kind: str) -> str:
	return f"{capture.family_of(kind)}.mk-{category}-{meraki_slug(name)}"


def meraki_note(category: str, name: str, source: dict = MERAKI) -> str:
	return (
		f"Imported from {source['name']} (components/{category}/{name}.html at {source['ref'][:10]}), {source['licence']} licence, "
		f"Copyright (c) 2021 {source['holder']}, {source['url']}."
	)


def import_meraki_markup(category: str, name: str, markup: str) -> dict:
	kind = MERAKI_KINDS[category]
	return import_markup(
		markup,
		kind=kind,
		block_id=meraki_id(category, name, kind),
		title=f"{kind.replace('-', ' ').capitalize()}, {meraki_slug(name).replace('-', ' ')} (Meraki UI)",
		source_note=meraki_note(category, name),
	)


def fetch_meraki(category: str, name: str) -> str:
	import requests

	response = requests.get(MERAKI["raw"].format(ref=MERAKI["ref"], category=category, name=name), timeout=30)
	response.raise_for_status()
	return response.text


def import_meraki(categories=None, push: bool = False) -> dict:
	"""For `bench execute`: the section components of Meraki UI that can be blocks, and why the others cannot; with `push` they go to the hub as drafts."""
	made: dict[str, dict] = {}
	refused: dict[str, str] = {}
	for category in categories or MERAKI_KINDS:
		for name in MERAKI_FILES[category]:
			label = f"{category}/{name}"
			try:
				made[label] = import_meraki_markup(category, name, fetch_meraki(category, name))
			except Refused as e:
				refused[label] = str(e)
			except Exception as e:
				refused[label] = f"not read ({type(e).__name__})"
	without_duplicates(made, refused)
	sent = push_all(made) if push else {}
	return {"blocks": {label: block["id"] for label, block in made.items()}, "refused": refused, "sent": sent}
