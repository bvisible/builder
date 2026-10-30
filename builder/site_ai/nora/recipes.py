# //// Neoffice — added file (no upstream equivalent): section recipes, structures the plan proposes and the writer adapts.
"""A library of section compositions, with slots for the copy and for the photographs.

Why it exists (2026-10-21). Measured on the builds of the local model: the pages are clean and sparse, a heading over one short
line, interior pages with a single photograph or none, a home thinner than the floor the brief states. The writer was asked
to design every section of every page from prose, which a model of this size does worst. A recipe gives it the STRUCTURE of a
section that is known to render well (grid, widths, phone fallbacks, the classes of the site's design system, the site's own
colour and type handles) and leaves it the part that makes a site its own: the words, the accent, the ornament, the order.

What a recipe is NOT. It is never imposed and never chosen by the code when the plan has made a choice:
  - the plan (the model that designs the site) picks a recipe by id for a section, or leaves the section free, and says in the
    section's `layout` what it changes (reverse the columns, the ground, the proportions);
  - each family offers several variants that differ in STRUCTURE, not in colour, so two sites do not share a skeleton;
  - the writer is told the structure is a starting point it adapts, and that the plan's adaptations win over it.
The code never picks a recipe for a section the plan left free, whatever the plan did elsewhere: a plan that never answered the field
(one written before the catalogue existed, kept two days, a model that ignored it) gives pages written as they always were. The only
thing the code changes is a structure the plan named on more than MAX_REPEATS pages (`pick`).

A recipe renders as the writer's own YAML: the same elements and classes, the handles of the site (no hex, no pixel size that
is not a literal), `m_style` on every grid. Its slots are texts that start with `WRITE <role>:` followed by the guidance (length,
role): the writer replaces each with its own words. A slot left in a page is asked for again, and one that is still there at the
end is removed (`scrub_unfilled`): "WRITE heading: …" is never published.

No model is called here."""

import hashlib
import re
from dataclasses import dataclass, field

import yaml

from builder.site_ai.nora.contrast import luminance
from builder.site_ai.nora.hero import DARK, _hex, _mix, _resolve, _rgba

# the alt text of a photograph is also the prompt of the image generator when the photograph is made after the build: a scene, not a caption
# //// Neoffice — and never a screen, a sign, a map, a document or a portrait (2026-10-26): the site keeps those from the image job
# //// (placeholders.must_not_be_drawn, a picture of them states something false), and a card whose alt named a screen lost its photograph
# //// Neoffice — and never a person (2026-10-26): a generated face is nobody. A one-person business showed "a technician at his desk" and "a man
# //// and a woman at a laptop" as if they were the owner and a client, and a visitor takes each for true. The photographs show the PLACE (the
# //// town, the valley, the region around the business), its premises, tools and products; a person only in a photograph the client gave.
ALT_GUIDANCE = (
	"a photographic description of the scene, 10 to 20 words, in the site's language: the subject, the setting, the light, "
	"specific to this business (its place and the region around it, its dishes, its tools and products); never the name of the business, no text in the picture, "
	"never a person (no face, nobody at work, not the owner, a team or a client: nobody who exists is in a generated photograph), "
	"and never a screen, a sign, a map, a document or a portrait (they are not drawn: show the place, the region, the hands and the tools instead)"
)
# a recipe is drawn on at most this many pages of a site, but for the kinds a site repeats on purpose: the opening of every interior page
# (the plan says "all interior pages open with the SAME shape") and the closing band
MAX_REPEATS = 2
REPEATED_ON_PURPOSE = ("statement", "intro", "cta")
SLOT = re.compile(r"^\s*WRITE\s+[\w-]+\s*:")
ACCENT_ROLES = ("heading", "quote")
GROUNDS = ("plain", "tint", "deep")


# ---------------------------------------------------------------- the YAML of a recipe


class _Flow(dict):
	"""A mapping written on one line, as the writer's own style objects are."""


class _FlowList(list):
	pass


class _Dumper(yaml.SafeDumper):
	def ignore_aliases(self, data):
		return True


_Dumper.add_representer(
	_Flow, lambda d, data: d.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)
)
_Dumper.add_representer(
	_FlowList, lambda d, data: d.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
)


def flow(**kw) -> _Flow:
	return _Flow(kw)


def to_yaml(node: dict) -> str:
	"""The node as a list item of the writer's YAML (`- el: section ...`)."""
	return yaml.dump(
		[node], Dumper=_Dumper, sort_keys=False, width=10**6, allow_unicode=True, default_flow_style=False
	).rstrip()


def el(
	tag, name=None, classes=None, style=None, m_style=None, attrs=None, text=None, c=None, t_style=None
) -> dict:
	node = {"el": tag}
	if name:
		node["name"] = name
	if classes:
		node["classes"] = _FlowList(classes)
	if style:
		node["style"] = style
	if t_style:
		node["t_style"] = t_style
	if m_style:
		node["m_style"] = m_style
	if attrs:
		node["attrs"] = attrs
	if text is not None:
		node["text"] = text
	if c:
		node["c"] = c
	return node


def slot(role: str, guidance: str) -> str:
	return f"WRITE {role}: {guidance}"


# ---------------------------------------------------------------- the look of a site


class Look:
	"""The colours and the type of a site, as a recipe writes them: handles only, and rgba() tints derived from them."""

	def __init__(self, handles: dict, palette: dict | None = None):
		palette = palette or {}
		self.primary = handles.get("primary") or "currentColor"
		self.secondary = handles.get("secondary") or self.primary
		self.background = handles.get("background") or "transparent"
		self.text = handles.get("text") or "currentColor"
		self.font_heading = handles.get("font-heading") or "inherit"
		self.font_body = handles.get("font-body") or "inherit"
		self.container = handles.get("container") or "1200px"
		self.gutter = handles.get("gutter") or "48px"
		self.gutter_phone = handles.get("gutter-phone") or "24px"
		p, s, b, t = (_resolve(handles, palette, k) for k in ("primary", "secondary", "background", "text"))
		s = s or p
		self.muted = _rgba(t, 0.72) if t else "rgba(0,0,0,0.65)"
		self.hair = _rgba(t, 0.16) if t else "rgba(0,0,0,0.12)"
		self.tint = _rgba(p or s, 0.08) if (p or s) else "rgba(0,0,0,0.04)"
		self.frame = _rgba(s, 0.35) if s else "rgba(0,0,0,0.12)"
		# a deep band: the primary when it is dark, else the ink when it is dark, else a deep shade of the primary
		if p and luminance(p) <= DARK:
			self.deep = self.primary
		elif t and luminance(t) <= DARK:
			self.deep = self.text
		else:
			self.deep = _hex(_mix(p, (0, 0, 0), 0.55)) if p else "#1a1a1a"
		self.ink_on_deep = self.background if (b is None or luminance(b) > DARK) else self.text
		deep_ink = (
			_resolve({"x": self.ink_on_deep}, palette, "x") if self.ink_on_deep.startswith("var(") else None
		)
		self.deep_muted = (
			_rgba(deep_ink or b or (255, 255, 255, 1), 0.8) if (deep_ink or b) else "rgba(255,255,255,0.8)"
		)
		self.deep_hair = (
			_rgba(deep_ink or b or (255, 255, 255, 1), 0.25) if (deep_ink or b) else "rgba(255,255,255,0.25)"
		)


@dataclass
class Ground:
	name: str
	bg: dict
	ink: str
	muted: str
	hair: str
	accent: str
	button: str


def ground_of(look: Look, name: str) -> Ground:
	if name == "deep":
		return Ground(
			"deep",
			{"backgroundColor": look.deep},
			look.ink_on_deep,
			look.deep_muted,
			look.deep_hair,
			look.secondary,
			"u-btn--secondary",
		)
	if name == "tint":
		return Ground(
			"tint",
			{"backgroundColor": look.tint},
			look.text,
			look.muted,
			look.hair,
			look.secondary,
			"u-btn--primary",
		)
	return Ground(
		"plain",
		{"backgroundColor": look.background},
		look.text,
		look.muted,
		look.hair,
		look.secondary,
		"u-btn--primary",
	)


@dataclass
class Ctx:
	look: Look
	ground: Ground
	photos: list[str]
	cta_href: str = "/contact"
	component: str = ""
	flip: bool = False


# ---------------------------------------------------------------- the parts of a section


def section(
	c: Ctx, name: str, children: list, pad: str = "6rem 0", m_pad: str = "4rem 0", extra: dict | None = None
) -> dict:
	return el(
		"section",
		name=name,
		style=flow(**c.ground.bg, width="100%", padding=pad, **(extra or {})),
		m_style=flow(padding=m_pad),
		c=children,
	)


def container(
	c: Ctx, children: list, name: str | None = None, extra: dict | None = None, m_extra: dict | None = None
) -> dict:
	k = c.look
	return el(
		"div",
		name=name,
		style=flow(
			maxWidth=k.container,
			width="100%",
			margin="0 auto",
			paddingLeft=k.gutter,
			paddingRight=k.gutter,
			**(extra or {}),
		),
		m_style=flow(paddingLeft=k.gutter_phone, paddingRight=k.gutter_phone, **(m_extra or {})),
		c=children,
	)


def label(c: Ctx, guidance: str, color: str | None = None, align: str | None = None) -> dict:
	k = c.look
	extra = {"textAlign": align} if align else {}
	return el(
		"p",
		name="label",
		style=flow(
			fontFamily=k.font_body,
			fontSize="0.75rem",
			fontWeight="700",
			letterSpacing="0.3em",
			textTransform="uppercase",
			color=color or c.ground.accent,
			margin="0 0 1.25rem",
			**extra,
		),
		text=slot("label", guidance),
	)


def heading(
	c: Ctx,
	guidance: str,
	tag: str = "h2",
	maxw: str = "40rem",
	align: str | None = None,
	size: str = "3rem",
	m_size: str = "1.75rem",
) -> dict:
	k = c.look
	extra = {"textAlign": align} if align else {}
	return el(
		tag,
		name="heading",
		style=flow(
			fontFamily=k.font_heading,
			fontSize=size,
			fontWeight="700",
			lineHeight="1.15",
			color=c.ground.ink,
			margin="0 0 1.25rem",
			maxWidth=maxw,
			**extra,
		),
		m_style=flow(fontSize=m_size),
		text=slot("heading", guidance),
	)


def paragraph(
	c: Ctx,
	role: str,
	guidance: str,
	maxw: str = "34rem",
	align: str | None = None,
	lead: bool = False,
	margin: str = "0 0 1.25rem",
) -> dict:
	k = c.look
	extra = {"textAlign": align} if align else {}
	return el(
		"p",
		name=role,
		style=flow(
			fontFamily=k.font_body,
			fontSize="1.25rem" if lead else "1.0625rem",
			lineHeight="1.7",
			color=c.ground.ink if lead else c.ground.muted,
			margin=margin,
			maxWidth=maxw,
			**extra,
		),
		text=slot(role, guidance),
	)


def button(
	c: Ctx, guidance: str = "a short invitation, 2 to 4 words", ghost: bool = False, align: str | None = None
) -> dict:
	variant = "u-btn--ghost" if ghost else c.ground.button
	style = flow(alignSelf=align) if align else None
	return el(
		"a",
		name="button",
		classes=["u-btn", variant],
		attrs=flow(href=c.cta_href),
		style=style,
		text=slot("button", guidance),
	)


def photo(
	c: Ctx, index: int, ratio: str, name: str = "photo", m_ratio: str | None = None, extra: dict | None = None
) -> dict:
	src = c.photos[index] if index < len(c.photos) else ""
	return el(
		"img",
		name=name,
		classes=["u-media"],
		attrs=flow(src=src, alt=slot("alt", ALT_GUIDANCE)),
		style=flow(width="100%", aspectRatio=ratio, objectFit="cover", display="block", **(extra or {})),
		m_style=flow(aspectRatio=m_ratio) if m_ratio else None,
	)


def rule(c: Ctx, width: str = "100%", color: str | None = None, margin: str = "0") -> dict:
	return el(
		"hr",
		name="rule",
		style=flow(
			border="none", height="1px", width=width, backgroundColor=color or c.ground.hair, margin=margin
		),
	)


def column(c: Ctx, children: list, name: str, align: str = "flex-start", extra: dict | None = None) -> dict:
	return el(
		"div",
		name=name,
		style=flow(display="flex", flexDirection="column", alignItems=align, **(extra or {})),
		c=children,
	)


def pair(
	c: Ctx,
	cols: str,
	children: list,
	name: str = "pair",
	gap: str = "4rem",
	align: str = "center",
	extra: dict | None = None,
) -> dict:
	return el(
		"div",
		name=name,
		style=flow(display="grid", gridTemplateColumns=cols, gap=gap, alignItems=align, **(extra or {})),
		# a narrow column of a pair (a heading beside a list) is starved on a tablet: the pair stacks there too (measured at 768 px)
		t_style=flow(gridTemplateColumns="1fr", gap="2.5rem"),
		m_style=flow(gridTemplateColumns="1fr", gap="2rem"),
		c=children,
	)


# ---------------------------------------------------------------- the registry


@dataclass(frozen=True)
class Recipe:
	id: str
	kinds: tuple
	look: str  # shown to the plan: how it looks and what it suits
	build: object = field(compare=False, repr=False)
	photos: int = 0
	form: bool = False  # needs a live component (the contact form) to carry
	ground: str = (
		"plain"  # the ground it asks for when the plan does not say ("plain" alternates with a tint)
	)
	# //// Neoffice — how much the section moves (2026-10-30, the motion layer of theme_variables.html): None, Calm (things appear and count) or
	# //// Brisk (things drift without end). It is offered only to a site whose own motion_style is at least as lively; the recipes written in code do not move.
	motion: str = "None"

	@property
	def family(self) -> str:
		return self.id.split(".")[0]


REGISTRY: dict[str, Recipe] = {}


def recipe(id: str, kinds: tuple, look: str, photos: int = 0, form: bool = False, ground: str = "plain"):
	def register(fn):
		REGISTRY[id] = Recipe(id, kinds, look, fn, photos, form, ground)
		return fn

	return register


# the recipes are written as one element per line, so that a structure reads like the page it draws: the formatter leaves them
# fmt: off
# ---------------------------------------------------------------- two-column and story


@recipe(
	"two-column.framed", ("two-column", "story"),
	"words beside one photograph that carries a hard offset frame in the secondary colour; the classic editorial pair, calm and warm",
	photos=1,
)
def _two_framed(c: Ctx) -> dict:
	k = c.look
	copy = column(c, [
		label(c, "2 to 4 words naming the subject"),
		heading(c, "4 to 8 words, one accent word", maxw="34rem"),
		paragraph(c, "lead", "one sentence of 20 to 30 words saying what this is about", lead=True),
		paragraph(c, "text", "two or three sentences, 40 to 60 words, from the business's own facts"),
		button(c, ghost=True),
	], "copy")
	frame = el("div", name="frame", style=flow(boxShadow=f"14px 14px 0 0 {k.frame}"), m_style=flow(boxShadow=f"8px 8px 0 0 {k.frame}"), c=[photo(c, 0, "4/3")])
	kids = [frame, copy] if c.flip else [copy, frame]
	return section(c, "pair-framed", [container(c, [pair(c, "7fr 5fr" if c.flip else "5fr 7fr", kids)])])


@recipe(
	"two-column.portrait", ("two-column", "story"),
	"a tall portrait photograph and a narrow column of words opened by an index numeral and a short rule; reads like a magazine page",
	photos=1,
)
def _two_portrait(c: Ctx) -> dict:
	k = c.look
	opener = [
		el("span", name="numeral", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.35em", color=c.ground.ink, whiteSpace="nowrap"), text=slot("numeral", "an index numeral such as 01 or 02")),
		el("hr", name="rule", style=flow(backgroundColor=k.secondary, border="none", height="1px", width="3rem", margin="0.75rem 0 1.25rem")),
	]
	copy = column(c, [
		*opener,
		heading(c, "4 to 8 words, one accent word", maxw="30rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 20 to 30 words", maxw="30rem", lead=True),
		paragraph(c, "text", "three sentences, 50 to 70 words, concrete and specific", maxw="30rem"),
		paragraph(c, "note", "a short closing line in italics, 8 to 14 words, the way a person would say it", maxw="30rem", margin="0"),
	], "copy")
	image = photo(c, 0, "4/5", m_ratio="4/3")
	kids = [image, copy] if c.flip else [copy, image]
	return section(c, "pair-portrait", [container(c, [pair(c, "5fr 4fr" if c.flip else "4fr 5fr", kids, gap="5rem")])], pad="7rem 0")


@recipe(
	"two-column.halves", ("two-column", "story"),
	"two edge-to-edge halves, a deep brand band with the words and a photograph filling the other half to the edge; no container, strong rhythm",
	photos=1, ground="deep",
)
def _two_halves(c: Ctx) -> dict:
	k = c.look
	deep = ground_of(k, "deep")
	band = el(
		"div", name="band",
		style=flow(**deep.bg, display="flex", flexDirection="column", justifyContent="center", alignItems="flex-start", padding="5rem 4rem"),
		m_style=flow(padding="3rem 1.5rem"),
		c=[
			el("p", name="label", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.3em", textTransform="uppercase", color=deep.accent, margin="0 0 1.25rem"), text=slot("label", "2 to 4 words")),
			el("h2", name="heading", style=flow(fontFamily=k.font_heading, fontSize="2.75rem", fontWeight="700", lineHeight="1.15", color=deep.ink, margin="0 0 1.25rem", maxWidth="30rem"), m_style=flow(fontSize="1.75rem"), text=slot("heading", "4 to 8 words, one accent word")),
			el("p", name="text", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.7", color=deep.muted, margin="0 0 1.5rem", maxWidth="28rem"), text=slot("text", "two or three sentences, 40 to 60 words")),
			el("a", name="button", classes=["u-btn", "u-btn--secondary"], attrs=flow(href=c.cta_href), text=slot("button", "a short invitation, 2 to 4 words")),
		],
	)
	image = el("img", name="photo", attrs=flow(src=c.photos[0] if c.photos else "", alt=slot("alt", ALT_GUIDANCE)), style=flow(width="100%", height="100%", minHeight="30rem", objectFit="cover", display="block"), m_style=flow(minHeight="16rem", height="16rem"))
	kids = [image, band] if c.flip else [band, image]
	halves = el("div", name="halves", style=flow(display="grid", gridTemplateColumns="1fr 1fr", alignItems="stretch"), t_style=flow(gridTemplateColumns="1fr"), m_style=flow(gridTemplateColumns="1fr"), c=kids)
	return el("section", name="pair-halves", style=flow(width="100%", backgroundColor=k.background), c=[halves])


# ---------------------------------------------------------------- gallery


@recipe(
	"gallery.mosaic", ("gallery",),
	"four photographs in a mosaic of unequal tiles, one large and three smaller; the pictures carry the section, the words only introduce it",
	photos=4,
)
def _gallery_mosaic(c: Ctx) -> dict:
	tiles = [
		photo(c, 0, "1/1", name="tile-large", extra={"height": "100%"}),
		photo(c, 1, "4/3", name="tile-wide", extra={"height": "100%"}),
		photo(c, 2, "1/1", name="tile-a", extra={"height": "100%"}),
		photo(c, 3, "1/1", name="tile-b", extra={"height": "100%"}),
	]
	spans = [("span 6", "span 2"), ("span 6", "span 1"), ("span 3", "span 1"), ("span 3", "span 1")]
	for tile, (col, row) in zip(tiles, spans, strict=False):
		tile["style"] = flow(**tile["style"], gridColumn=col, gridRow=row)
		tile["m_style"] = flow(gridColumn="span 2" if col == "span 6" else "span 1", gridRow="span 1")
	grid = el(
		"div", name="mosaic",
		style=flow(display="grid", gridTemplateColumns="repeat(12, 1fr)", gridAutoRows="14rem", gap="1rem"),
		m_style=flow(gridTemplateColumns="1fr 1fr", gridAutoRows="11rem", gap="0.75rem"), c=tiles,
	)
	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="36rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words introducing the pictures", margin="0 0 2.5rem"),
	], "head")
	return section(c, "gallery-mosaic", [container(c, [head, grid])])


@recipe(
	"gallery.captions", ("gallery",),
	"three tall photographs in a row, the middle one set lower, each with a short caption beneath; quiet and generous",
	photos=3,
)
def _gallery_captions(c: Ctx) -> dict:
	k = c.look

	def item(i, lower=False):
		return el("div", name="item", style=flow(display="flex", flexDirection="column", **({"marginTop": "3rem"} if lower else {})), m_style=flow(marginTop="0"), c=[
			photo(c, i, "3/4", m_ratio="4/3"),
			el("h3", name="caption", style=flow(fontFamily=k.font_heading, fontSize="1.375rem", fontWeight="700", color=c.ground.ink, margin="1.25rem 0 0.4rem"), text=slot("item-title", "2 to 4 words naming what the photograph shows")),
			el("p", name="caption-text", style=flow(fontFamily=k.font_body, fontSize="1rem", lineHeight="1.6", color=c.ground.muted, margin="0"), text=slot("item-text", "one line of 10 to 16 words")),
		])

	grid = el("div", name="row", classes=["u-grid", "u-grid--3"], style=flow(alignItems="start"), c=[item(0), item(1, lower=True), item(2)])
	head = column(c, [
		label(c, "2 to 4 words"),
		heading(c, "3 to 7 words, one accent word", maxw="34rem"),
	], "head", extra={"marginBottom": "2.5rem"})
	return section(c, "gallery-captions", [container(c, [head, grid])])


@recipe(
	"gallery.feature", ("gallery",),
	"one large photograph with its caption laid over a veil, and a strip of three small ones under it; a first look and then the detail",
	photos=4, ground="tint",
)
def _gallery_feature(c: Ctx) -> dict:
	k = c.look
	big = el(
		"div", name="feature", classes=["u-over-image", "u-over-image--bottom"],
		style=flow(position="relative", minHeight="26rem", display="flex", alignItems="flex-end", overflow="hidden"),
		m_style=flow(minHeight="18rem"),
		c=[
			el("img", name="photo", attrs=flow(src=c.photos[0] if c.photos else "", alt=slot("alt", ALT_GUIDANCE)), style=flow(position="absolute", inset="0", width="100%", height="100%", objectFit="cover")),
			el("div", name="caption", style=flow(position="relative", padding="2rem 2.5rem", maxWidth="34rem", textShadow="0 1px 14px rgba(0,0,0,0.5)"), m_style=flow(padding="1.25rem"), c=[
				el("h3", name="caption-title", style=flow(fontFamily=k.font_heading, fontSize="2rem", fontWeight="700", lineHeight="1.2", color=k.background, margin="0 0 0.5rem"), m_style=flow(fontSize="1.5rem"), text=slot("item-title", "3 to 6 words naming the place or the dish")),
				el("p", name="caption-text", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.6", color=k.background, margin="0"), text=slot("item-text", "one sentence of 12 to 20 words")),
			]),
		],
	)
	strip = el("div", name="strip", classes=["u-grid", "u-grid--3"], style=flow(marginTop="1.25rem"), c=[photo(c, i, "4/3", name="thumb") for i in (1, 2, 3)])
	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="36rem")], "head", extra={"marginBottom": "2rem"})
	return section(c, "gallery-feature", [container(c, [head, big, strip])])


# ---------------------------------------------------------------- pricing


def _price_row(c: Ctx) -> dict:
	k = c.look
	return el(
		"div", name="row",
		style=flow(display="flex", justifyContent="space-between", alignItems="baseline", gap="2rem", padding="1.25rem 0", borderBottom=f"1px solid {c.ground.hair}"),
		m_style=flow(flexDirection="column", gap="0.35rem", alignItems="flex-start"),
		c=[
			column(c, [
				el("h3", name="item-name", style=flow(fontFamily=k.font_heading, fontSize="1.375rem", fontWeight="700", color=c.ground.ink, margin="0 0 0.3rem"), text=slot("item-title", "the name of the dish, the service or the offer, as the material gives it")),
				el("p", name="item-text", style=flow(fontFamily=k.font_body, fontSize="1rem", lineHeight="1.6", color=c.ground.muted, margin="0", maxWidth="34rem"), text=slot("item-text", "one line of 8 to 16 words saying what it is")),
			], "item-copy"),
			el("span", name="price", style=flow(fontFamily=k.font_heading, fontSize="1.375rem", fontWeight="700", color=c.ground.ink, whiteSpace="nowrap"), text=slot("price", "the price exactly as the material gives it, never invented")),
		],
	)


@recipe(
	"pricing.ledger", ("pricing",),
	"a ruled price list, name and line on the left, price on the right, hairlines between; precise and quiet (a menu, a fee schedule)",
)
def _pricing_ledger(c: Ctx) -> dict:
	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="30rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words saying how the prices are set", margin="0"),
	], "head")
	rows = el("div", name="ledger", c=[_price_row(c) for _ in range(5)])
	return section(c, "pricing-ledger", [container(c, [pair(c, "4fr 8fr", [head, rows], align="start", gap="5rem")])])


@recipe(
	"pricing.tiers", ("pricing",),
	"two or three offers side by side as cards, the recommended one lifted on a deep fill; for plans with a clear difference between them",
)
def _pricing_tiers(c: Ctx) -> dict:
	k = c.look
	deep = ground_of(k, "deep")

	def card(featured: bool):
		g = deep if featured else c.ground
		style = flow(display="flex", flexDirection="column", alignItems="flex-start", padding="2.5rem 2rem", height="100%", **(deep.bg if featured else {}))
		return el("div", name="tier", classes=["u-card"], style=style, c=[
			el("h3", name="tier-name", style=flow(fontFamily=k.font_heading, fontSize="1.5rem", fontWeight="700", color=g.ink, margin="0 0 0.75rem"), text=slot("item-title", "the name of the offer")),
			el("p", name="price", style=flow(fontFamily=k.font_heading, fontSize="2.75rem", fontWeight="700", lineHeight="1.1", color=g.ink, margin="0 0 0.25rem"), text=slot("price", "the price exactly as the material gives it, never invented")),
			el("p", name="price-note", style=flow(fontFamily=k.font_body, fontSize="0.9375rem", color=g.muted if featured else c.ground.muted, margin="0 0 1.5rem"), text=slot("note", "what the price covers, 4 to 8 words")),
			el("p", name="includes", style=flow(fontFamily=k.font_body, fontSize="1rem", lineHeight="1.7", color=g.muted if featured else c.ground.muted, margin="0 0 2rem"), text=slot("item-text", "two or three things included, in one sentence of 15 to 25 words")),
			el("a", name="button", classes=["u-btn", "u-btn--secondary" if featured else "u-btn--outline"], attrs=flow(href=c.cta_href), style=flow(marginTop="auto"), text=slot("button", "2 to 4 words")),
		])

	grid = el("div", name="tiers", classes=["u-grid", "u-grid--3"], style=flow(alignItems="stretch"), c=[card(False), card(True), card(False)])
	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="34rem", align="center", size="2.75rem")], "head", align="center", extra={"marginBottom": "3rem"})
	return section(c, "pricing-tiers", [container(c, [head, grid])])


@recipe(
	"pricing.featured", ("pricing",),
	"one featured offer large on a deep band on one side and the other offers as a compact ruled list on the other; a clear first choice",
)
def _pricing_featured(c: Ctx) -> dict:
	k = c.look
	deep = ground_of(k, "deep")
	main = el("div", name="featured", classes=["u-card"], style=flow(**deep.bg, padding="3rem 2.5rem", display="flex", flexDirection="column", alignItems="flex-start"), m_style=flow(padding="2rem 1.5rem"), c=[
		el("p", name="label", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.3em", textTransform="uppercase", color=deep.accent, margin="0 0 1rem"), text=slot("label", "2 to 3 words such as the favourite")),
		el("h3", name="tier-name", style=flow(fontFamily=k.font_heading, fontSize="2.25rem", fontWeight="700", lineHeight="1.15", color=deep.ink, margin="0 0 0.75rem"), text=slot("item-title", "the name of the featured offer")),
		el("p", name="price", style=flow(fontFamily=k.font_heading, fontSize="3.5rem", fontWeight="700", lineHeight="1.05", color=deep.ink, margin="0 0 1rem"), m_style=flow(fontSize="2.5rem"), text=slot("price", "the price exactly as the material gives it, never invented")),
		el("p", name="includes", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.7", color=deep.muted, margin="0 0 1.75rem", maxWidth="26rem"), text=slot("item-text", "what it includes, 25 to 40 words")),
		el("a", name="button", classes=["u-btn", "u-btn--secondary"], attrs=flow(href=c.cta_href), text=slot("button", "2 to 4 words")),
	])
	others = column(c, [
		heading(c, "3 to 6 words, one accent word", maxw="24rem", size="2.25rem", m_size="1.625rem"),
		el("div", name="ledger", style=flow(width="100%"), c=[_price_row(c) for _ in range(3)]),
	], "others", extra={"width": "100%"})
	return section(c, "pricing-featured", [container(c, [pair(c, "6fr 6fr", [main, others], align="start", gap="4rem")])])


# ---------------------------------------------------------------- faq


def _faq_item(c: Ctx) -> dict:
	k = c.look
	return el("details", name="question", c=[
		el("summary", name="question-text", style=flow(fontFamily=k.font_heading, fontSize="1.25rem", fontWeight="700", color=c.ground.ink), text=slot("question", "a real question a customer asks, 5 to 12 words")),
		el("p", name="answer", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.7", color=c.ground.muted, margin="0.75rem 0 0", maxWidth="44rem"), text=slot("answer", "an answer of 25 to 45 words from the business's own facts")),
	])


@recipe(
	"faq.side", ("faq",),
	"the heading and a short note on the left, the folding questions on the right; a calm reference page",
)
def _faq_side(c: Ctx) -> dict:
	head = column(c, [
		label(c, "2 to 4 words"),
		heading(c, "3 to 7 words, one accent word", maxw="22rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words saying how to reach the business for anything not answered here", maxw="22rem", margin="0"),
	], "head")
	faq = el("div", name="faq", classes=["u-faq"], c=[_faq_item(c) for _ in range(5)])
	return section(c, "faq-side", [container(c, [pair(c, "4fr 8fr", [head, faq], align="start", gap="5rem")])])


@recipe(
	"faq.centred", ("faq",),
	"a centred heading over one narrow column of folding questions; sober, for a short list",
)
def _faq_centred(c: Ctx) -> dict:
	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="34rem", align="center", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words", maxw="34rem", align="center", margin="0 0 2.5rem"),
	], "head", align="center")
	faq = el("div", name="faq", classes=["u-faq"], style=flow(maxWidth="48rem", width="100%", margin="0 auto"), c=[_faq_item(c) for _ in range(5)])
	return section(c, "faq-centred", [container(c, [head, faq])])


@recipe(
	"faq.two-up", ("faq",),
	"two columns of folding questions side by side on a tinted ground, a short heading above; dense and practical",
	ground="tint",
)
def _faq_two(c: Ctx) -> dict:
	cols = pair(c, "1fr 1fr", [
		el("div", name="faq-left", classes=["u-faq"], c=[_faq_item(c) for _ in range(3)]),
		el("div", name="faq-right", classes=["u-faq"], c=[_faq_item(c) for _ in range(3)]),
	], gap="3rem", align="start")
	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="34rem", size="2.75rem")], "head", extra={"marginBottom": "2.5rem"})
	return section(c, "faq-two-up", [container(c, [head, cols])])


# ---------------------------------------------------------------- figures


def _figure(c: Ctx, g: Ground, size: str = "4rem", align: str = "flex-start") -> dict:
	k = c.look
	return column(c, [
		el("p", name="figure", style=flow(fontFamily=k.font_heading, fontSize=size, fontWeight="700", lineHeight="1", color=g.ink, margin="0 0 0.5rem"), m_style=flow(fontSize="3rem"), text=slot("figure", "a figure the material gives, such as a year, a count or a distance, never invented")),
		el("p", name="figure-label", style=flow(fontFamily=k.font_body, fontSize="1rem", lineHeight="1.5", color=g.muted, margin="0", maxWidth="16rem"), text=slot("figure-label", "what the figure counts, 2 to 6 words")),
	], "figure-item", align=align)


@recipe(
	"figures.band", ("figures",),
	"three or four large numerals on a deep brand band, short and tall-lettered; proof at a glance between two quiet sections",
	ground="deep",
)
def _figures_band(c: Ctx) -> dict:
	deep = Ctx(c.look, ground_of(c.look, "deep"), c.photos, c.cta_href, c.component, c.flip)
	grid = el("div", name="figures", classes=["u-grid", "u-grid--3"], c=[_figure(deep, deep.ground) for _ in range(3)])
	return section(deep, "figures-band", [container(deep, [grid])], pad="5rem 0", m_pad="3rem 0")


@recipe(
	"figures.ledger", ("figures",),
	"a heading and a sentence on the left, the figures on the right as ruled rows, the numeral beside its meaning; for a business that can be measured",
)
def _figures_ledger(c: Ctx) -> dict:
	k = c.look

	def row():
		return el("div", name="row", style=flow(display="flex", alignItems="baseline", gap="2rem", padding="1.25rem 0", borderBottom=f"1px solid {c.ground.hair}"), m_style=flow(gap="1rem"), c=[
			el("p", name="figure", style=flow(fontFamily=k.font_heading, fontSize="3rem", fontWeight="700", lineHeight="1", color=c.ground.ink, margin="0", minWidth="9rem"), m_style=flow(fontSize="2.25rem", minWidth="6rem"), text=slot("figure", "a figure the material gives, never invented")),
			el("p", name="figure-label", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.5", color=c.ground.muted, margin="0"), text=slot("figure-label", "what the figure counts, 3 to 8 words")),
		])

	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="24rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words", maxw="24rem", margin="0"),
	], "head")
	return section(c, "figures-ledger", [container(c, [pair(c, "5fr 7fr", [head, el("div", name="ledger", c=[row() for _ in range(3)])], align="start", gap="5rem")])])


@recipe(
	"figures.statements", ("figures",),
	"oversized numerals each opening a short statement, in a row on a tinted ground; the figure is the headline of its own sentence",
	ground="tint",
)
def _figures_statements(c: Ctx) -> dict:
	k = c.look

	def item():
		return column(c, [
			el("p", name="figure", style=flow(fontFamily=k.font_heading, fontSize="5.5rem", fontWeight="700", lineHeight="0.95", color=c.ground.ink, margin="0 0 1rem"), m_style=flow(fontSize="4rem"), text=slot("figure", "a figure the material gives, never invented")),
			rule(c, width="3rem", color=k.secondary, margin="0 0 1rem"),
			el("p", name="statement", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.65", color=c.ground.muted, margin="0", maxWidth="18rem"), text=slot("item-text", "one sentence of 12 to 20 words saying what the figure means")),
		], "figure-item")

	grid = el("div", name="figures", classes=["u-grid", "u-grid--3"], c=[item() for _ in range(3)])
	return section(c, "figures-statements", [container(c, [grid])])


# ---------------------------------------------------------------- testimonials


def _who(c: Ctx, g: Ground) -> list:
	k = c.look
	return [
		el("p", name="who", style=flow(fontFamily=k.font_body, fontSize="1rem", fontWeight="700", color=g.ink, margin="0"), text=slot("who", "the name as the material gives it")),
		el("p", name="who-role", style=flow(fontFamily=k.font_body, fontSize="0.9375rem", color=g.muted, margin="0"), text=slot("note", "the role or the place, 2 to 5 words")),
	]


@recipe(
	"testimonials.statement", ("testimonials",),
	"one quotation set large as a statement with a short rule and its author, a second smaller one beside it; the voice of a single customer",
)
def _testimonials_statement(c: Ctx) -> dict:
	k = c.look
	main = column(c, [
		el("span", name="mark", style=flow(fontFamily=k.font_heading, fontSize="5rem", lineHeight="0.6", color=k.secondary, display="block", margin="0 0 1rem"), text="“"),
		el("p", name="quote", style=flow(fontFamily=k.font_heading, fontSize="2.25rem", lineHeight="1.3", fontWeight="700", color=c.ground.ink, margin="0 0 1.75rem", maxWidth="40rem"), m_style=flow(fontSize="1.5rem"), text=slot("quote", "the quotation as the material gives it, 20 to 40 words, one accent word")),
		rule(c, width="3rem", color=k.secondary, margin="0 0 1rem"),
		*_who(c, c.ground),
	], "main")
	side = column(c, [
		el("p", name="quote-small", style=flow(fontFamily=k.font_body, fontSize="1.125rem", lineHeight="1.7", color=c.ground.muted, margin="0 0 1rem", fontStyle="italic"), text=slot("quote", "a second quotation as the material gives it, 15 to 30 words")),
		*_who(c, c.ground),
	], "side", extra={"paddingTop": "3rem", "borderTop": f"1px solid {c.ground.hair}"})
	return section(c, "testimonials-statement", [container(c, [pair(c, "8fr 4fr", [main, side], align="start", gap="5rem")])])


@recipe(
	"testimonials.cards", ("testimonials",),
	"three quotations on cards at different heights, each with its author; a chorus of voices",
	ground="tint",
)
def _testimonials_cards(c: Ctx) -> dict:
	k = c.look

	def card(lower=False):
		return el("div", name="testimonial", classes=["u-card"], style=flow(padding="2rem", display="flex", flexDirection="column", **({"marginTop": "2.5rem"} if lower else {})), m_style=flow(marginTop="0"), c=[
			el("span", name="mark", style=flow(fontFamily=k.font_heading, fontSize="3rem", lineHeight="0.8", color=k.secondary, display="block", margin="0 0 0.75rem"), text="“"),
			el("p", name="quote", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.7", color=c.ground.ink, margin="0 0 1.5rem"), text=slot("quote", "the quotation as the material gives it, 20 to 35 words")),
			*_who(c, c.ground),
		])

	grid = el("div", name="testimonials", classes=["u-grid", "u-grid--3"], style=flow(alignItems="start"), c=[card(), card(True), card()])
	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="34rem", size="2.75rem")], "head", extra={"marginBottom": "2.5rem"})
	return section(c, "testimonials-cards", [container(c, [head, grid])])


@recipe(
	"testimonials.ledger", ("testimonials",),
	"quotations in ruled rows, the words large on the left and who says it small on the right; editorial and unhurried",
)
def _testimonials_ledger(c: Ctx) -> dict:
	k = c.look

	def row():
		return el("div", name="testimonial", style=flow(display="grid", gridTemplateColumns="8fr 3fr", gap="3rem", alignItems="baseline", padding="2rem 0", borderBottom=f"1px solid {c.ground.hair}"), m_style=flow(gridTemplateColumns="1fr", gap="1rem"), c=[
			el("p", name="quote", style=flow(fontFamily=k.font_heading, fontSize="1.625rem", lineHeight="1.4", color=c.ground.ink, margin="0"), m_style=flow(fontSize="1.25rem"), text=slot("quote", "the quotation as the material gives it, 15 to 30 words")),
			column(c, _who(c, c.ground), "author"),
		])

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="34rem", size="2.75rem")], "head", extra={"marginBottom": "1.5rem"})
	return section(c, "testimonials-ledger", [container(c, [head, el("div", name="quotes", c=[row() for _ in range(3)])])])


# ---------------------------------------------------------------- contact


def _detail(c: Ctx, g: Ground, label_guidance: str, value_guidance: str) -> dict:
	k = c.look
	return column(c, [
		el("p", name="detail-label", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.25em", textTransform="uppercase", color=g.accent, margin="0 0 0.35rem"), text=slot("detail-label", label_guidance)),
		el("p", name="detail-value", style=flow(fontFamily=k.font_body, fontSize="1.125rem", lineHeight="1.6", color=g.ink, margin="0"), text=slot("detail-value", value_guidance)),
	], "detail", extra={"paddingBottom": "1.25rem", "marginBottom": "1.25rem", "borderBottom": f"1px solid {g.hair}", "width": "100%"})


def _include(c: Ctx) -> dict:
	return el("div", name="form", text="{% include \"" + c.component + "\" %}")


DETAILS = [
	("the address", "the address exactly as BUSINESS DATA gives it; leave this row out when it gives none"),
	("the phone or the e-mail", "the phone number or the e-mail exactly as BUSINESS DATA gives it; leave this row out when it gives none"),
	("the opening hours", "the opening hours exactly as BUSINESS DATA gives them; leave this row out when it gives none"),
]


@recipe(
	"contact.split", ("contact-form", "contact-details"),
	"the details on the left, the form in a card on the right; the usual contact page, but with the words of the business",
	form=True,
)
def _contact_split(c: Ctx) -> dict:
	left = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="26rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words inviting the visitor to write or call", maxw="26rem", margin="0 0 2rem"),
		*[_detail(c, c.ground, *d) for d in DETAILS],
	], "details")
	card = el("div", name="form-card", classes=["u-card"], style=flow(padding="2.5rem", width="100%"), m_style=flow(padding="1.5rem"), c=[_include(c)])
	kids = [card, left] if c.flip else [left, card]
	return section(c, "contact-split", [container(c, [pair(c, "7fr 5fr" if c.flip else "5fr 7fr", kids, align="start", gap="5rem")])])


@recipe(
	"contact.stacked", ("contact-form",),
	"a centred invitation above one narrow form card, the details in a row of columns beneath; the form comes first",
	form=True, ground="tint",
)
def _contact_stacked(c: Ctx) -> dict:
	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="34rem", align="center", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words inviting the visitor to write", maxw="34rem", align="center", margin="0 0 2rem"),
	], "head", align="center")
	card = el("div", name="form-card", classes=["u-card"], style=flow(padding="2.5rem", maxWidth="44rem", width="100%", margin="0 auto"), m_style=flow(padding="1.5rem"), c=[_include(c)])
	details = el("div", name="details", classes=["u-grid", "u-grid--3"], style=flow(marginTop="3.5rem"), c=[_detail(c, c.ground, *d) for d in DETAILS])
	return section(c, "contact-stacked", [container(c, [head, card, details])])


@recipe(
	"contact.band", ("contact-details",),
	"a deep band with the phone or the e-mail set large as the call to action and the address and hours in a row beneath; for a business people call",
	ground="deep",
)
def _contact_band(c: Ctx) -> dict:
	k = c.look
	deep = Ctx(k, ground_of(k, "deep"), c.photos, c.cta_href, c.component, c.flip)
	head = column(deep, [
		label(deep, "2 to 4 words such as write or call us"),
		el("p", name="big-line", style=flow(fontFamily=k.font_heading, fontSize="3.5rem", fontWeight="700", lineHeight="1.1", color=deep.ground.ink, margin="0 0 1.5rem", maxWidth="40rem"), m_style=flow(fontSize="2.25rem"), text=slot("heading", "the phone number or the e-mail as BUSINESS DATA gives it, set as the headline; a short invitation when it gives neither")),
		el("a", name="button", classes=["u-btn", "u-btn--secondary"], attrs=flow(href=deep.cta_href), text=slot("button", "2 to 4 words")),
	], "head")
	row = el("div", name="details", classes=["u-grid", "u-grid--3"], style=flow(marginTop="3.5rem", paddingTop="2rem", borderTop=f"1px solid {deep.ground.hair}"), c=[
		column(deep, [
			el("p", name="detail-label", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.25em", textTransform="uppercase", color=deep.ground.accent, margin="0 0 0.35rem"), text=slot("detail-label", d[0])),
			el("p", name="detail-value", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.6", color=deep.ground.muted, margin="0"), text=slot("detail-value", d[1])),
		], "detail")
		for d in DETAILS
	])
	return section(deep, "contact-band", [container(deep, [head, row])])


# ---------------------------------------------------------------- feature-grid and cards


def _numeral(c: Ctx, guidance: str = "an index numeral such as 01, 02, 03") -> dict:
	k = c.look
	return el("span", name="numeral", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.35em", color=c.ground.accent, margin="0 0 1rem", whiteSpace="nowrap"), text=slot("numeral", guidance))


def _item_copy(c: Ctx, title_guidance: str, text_guidance: str, g: Ground | None = None, maxw: str = "24rem", size: str = "1.5rem") -> list:
	k, g = c.look, g or c.ground
	return [
		el("h3", name="item-title", style=flow(fontFamily=k.font_heading, fontSize=size, fontWeight="700", lineHeight="1.25", color=g.ink, margin="0 0 0.75rem"), text=slot("item-title", title_guidance)),
		el("p", name="item-text", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.65", color=g.muted, margin="0", maxWidth=maxw), text=slot("item-text", text_guidance)),
	]


TITLE = "3 to 6 words naming the offer, the reason or the service"
TEXT = "one or two sentences, 20 to 35 words, concrete and from the business's own facts"


@recipe(
	"features.ruled", ("feature-grid", "cards"),
	"three columns separated from the heading by a hairline, each with an index numeral, a heading and a line; no cards, no icons, calm and typographic",
)
def _features_ruled(c: Ctx) -> dict:
	def item():
		return column(c, [_numeral(c), *_item_copy(c, TITLE, TEXT)], "item", extra={"borderTop": f"1px solid {c.ground.hair}", "paddingTop": "1.5rem"})

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="36rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "features-ruled", [container(c, [head, el("div", name="features", classes=["u-grid", "u-grid--3"], c=[item() for _ in range(3)])])])


@recipe(
	"features.list", ("feature-grid", "cards"),
	"a heading and a sentence on the left, the offers as ruled rows on the right, a numeral beside each title and its line; reads like a table of contents",
)
def _features_list(c: Ctx) -> dict:
	def row():
		return el("div", name="row", style=flow(display="flex", gap="2rem", padding="1.5rem 0", borderBottom=f"1px solid {c.ground.hair}"), m_style=flow(gap="1rem"), c=[
			el("span", name="numeral", style=flow(fontFamily=c.look.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.25em", color=c.ground.accent, minWidth="2.5rem", paddingTop="0.45rem", whiteSpace="nowrap"), text=slot("numeral", "an index numeral such as 01, 02, 03")),
			column(c, _item_copy(c, TITLE, TEXT, maxw="36rem"), "row-copy"),
		])

	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="24rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words", maxw="24rem", margin="0"),
	], "head")
	return section(c, "features-list", [container(c, [pair(c, "4fr 8fr", [head, el("div", name="rows", c=[row() for _ in range(4)])], align="start", gap="5rem")])])


@recipe(
	"features.tiles", ("feature-grid", "cards"),
	"a two-by-two set of tiles, the first filled with the deep brand colour and the others softly tinted; each tile a short heading and a line",
)
def _features_tiles(c: Ctx) -> dict:
	k = c.look
	deep = ground_of(k, "deep")

	def tile(first: bool):
		g = deep if first else ground_of(k, "tint" if c.ground.name == "plain" else "plain")
		return el("div", name="tile", classes=["u-card"], style=flow(**g.bg, padding="2.5rem 2.25rem", display="flex", flexDirection="column", alignItems="flex-start", minHeight="14rem"), m_style=flow(padding="1.75rem 1.5rem", minHeight="0"), c=[
			el("span", name="numeral", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.35em", color=g.accent, margin="0 0 1rem"), text=slot("numeral", "an index numeral such as 01, 02, 03")),
			*_item_copy(c, TITLE, TEXT, g, maxw="26rem"),
		])

	grid = el("div", name="tiles", classes=["u-grid", "u-grid--2"], c=[tile(True), tile(False), tile(False), tile(False)])
	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="36rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "features-tiles", [container(c, [head, grid])])


@recipe(
	"features.photo-cards", ("feature-grid", "cards"),
	"three cards, each with a photograph on top and a heading and a line below; for offers that have to be seen",
	photos=3,
)
def _features_photo_cards(c: Ctx) -> dict:
	def card(i):
		return el("div", name="card", classes=["u-card"], style=flow(overflow="hidden", display="flex", flexDirection="column"), c=[
			photo(c, i, "4/3", name="card-photo"),
			el("div", name="card-copy", style=flow(padding="1.75rem 1.75rem 2rem"), m_style=flow(padding="1.25rem"), c=_item_copy(c, TITLE, TEXT, maxw="26rem", size="1.375rem")),
		])

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="36rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "features-photo-cards", [container(c, [head, el("div", name="cards", classes=["u-grid", "u-grid--3"], c=[card(0), card(1), card(2)])])])


# ---------------------------------------------------------------- statement and intro


@recipe(
	"statement.centred", ("statement", "intro"),
	"one or two sentences set large and centred under a small label, closed by a short rule; a quiet, confident opening",
)
def _statement_centred(c: Ctx) -> dict:
	k = c.look
	body_ = column(c, [
		label(c, "2 to 4 words", align="center"),
		heading(c, "one or two sentences, 15 to 28 words, one accent word, never the title of the page", maxw="46rem", align="center", size="2.75rem"),
		rule(c, width="3rem", color=k.secondary, margin="0.5rem 0 1.5rem"),
		paragraph(c, "text", "two sentences, 30 to 50 words, that say what the business does and for whom", maxw="38rem", align="center", margin="0"),
	], "statement", align="center")
	return section(c, "statement-centred", [container(c, [body_])], pad="6.5rem 0")


@recipe(
	"statement.columns", ("statement", "intro"),
	"a large heading on the left and two columns of running text on the right; an editorial introduction",
)
def _statement_columns(c: Ctx) -> dict:
	k = c.look
	head = column(c, [label(c, "2 to 4 words"), heading(c, "4 to 9 words, one accent word, never the title of the page", maxw="26rem", size="3rem")], "head")
	text = el(
		"div", name="columns",
		style=flow(columnCount="2", columnGap="3rem", fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.75", color=c.ground.muted),
		m_style=flow(columnCount="1"),
		c=[
			el("p", name="text", style=flow(margin="0 0 1.25rem"), text=slot("text", "three sentences, 45 to 70 words")),
			el("p", name="text", style=flow(margin="0"), text=slot("text", "three sentences, 45 to 70 words")),
		],
	)
	return section(c, "statement-columns", [container(c, [pair(c, "5fr 7fr", [head, text], align="start", gap="5rem")])], pad="5.5rem 0")


@recipe(
	"statement.manifesto", ("statement", "intro"),
	"an oversized opening sentence set to the left under a hairline, a short signature line beneath; a manifesto, left-aligned and tall",
	ground="tint",
)
def _statement_manifesto(c: Ctx) -> dict:
	k = c.look
	body_ = column(c, [
		rule(c, width="100%", margin="0 0 2.5rem"),
		heading(c, "one sentence of 14 to 24 words, one accent word, never the title of the page", maxw="52rem", size="3.5rem", m_size="2rem"),
		paragraph(c, "text", "one or two sentences, 20 to 40 words, that carry on from the heading", maxw="36rem", margin="1rem 0 1.5rem"),
		el("p", name="signature", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.3em", textTransform="uppercase", color=c.ground.accent, margin="0"), text=slot("label", "a signature such as the name of the house and its place")),
	], "statement")
	return section(c, "statement-manifesto", [container(c, [body_])], pad="7rem 0")


# ---------------------------------------------------------------- cta


@recipe(
	"cta.band", ("cta",),
	"a deep brand band, a centred heading, one sentence and one button; the closing line of a page",
	ground="deep",
)
def _cta_band(c: Ctx) -> dict:
	k = c.look
	deep = Ctx(k, ground_of(k, "deep"), c.photos, c.cta_href, c.component, c.flip)
	body_ = column(deep, [
		heading(deep, "4 to 9 words, one accent word", maxw="40rem", align="center", size="2.75rem"),
		paragraph(deep, "text", "one sentence of 15 to 28 words", maxw="34rem", align="center", margin="0 0 2rem"),
		button(deep, "a direct invitation, 2 to 4 words"),
	], "closing", align="center")
	return section(deep, "cta-band", [container(deep, [body_])], pad="5.5rem 0", m_pad="3.5rem 0")


@recipe(
	"cta.split", ("cta",),
	"the invitation on the left and its buttons on the right in one tinted row, under a hairline; a short, businesslike close",
	ground="tint",
)
def _cta_split(c: Ctx) -> dict:
	left = column(c, [
		heading(c, "4 to 9 words, one accent word", maxw="32rem", size="2.5rem", m_size="1.75rem"),
		paragraph(c, "text", "one sentence of 15 to 28 words", maxw="32rem", margin="0"),
	], "invitation")
	right = el("div", name="buttons", style=flow(display="flex", gap="1rem", justifyContent="flex-end", flexWrap="wrap"), m_style=flow(justifyContent="flex-start"), c=[
		button(c, "a direct invitation, 2 to 4 words"),
		button(c, "a second, softer action, 2 to 4 words", ghost=True),
	])
	return section(c, "cta-split", [container(c, [pair(c, "7fr 5fr", [left, right], gap="3rem")])], pad="4.5rem 0", m_pad="3rem 0")


@recipe(
	"cta.card", ("cta",),
	"a centred card on the page ground with a heading, a sentence and two buttons side by side; the invitation as an object",
)
def _cta_card(c: Ctx) -> dict:
	card = el("div", name="closing-card", classes=["u-card"], style=flow(padding="3.5rem 3rem", maxWidth="52rem", margin="0 auto", display="flex", flexDirection="column", alignItems="center"), m_style=flow(padding="2rem 1.25rem"), c=[
		heading(c, "4 to 9 words, one accent word", maxw="36rem", align="center", size="2.5rem", m_size="1.75rem"),
		paragraph(c, "text", "one sentence of 15 to 28 words", maxw="34rem", align="center", margin="0 0 2rem"),
		el("div", name="buttons", style=flow(display="flex", gap="1rem", justifyContent="center", flexWrap="wrap"), c=[
			button(c, "a direct invitation, 2 to 4 words"),
			button(c, "a second, softer action, 2 to 4 words", ghost=True),
		]),
	])
	return section(c, "cta-card", [container(c, [card])], pad="5rem 0", m_pad="3rem 0")


# ---------------------------------------------------------------- steps


@recipe(
	"steps.numbered", ("steps",),
	"steps in a row, each opened by a large numeral and a short rule, then a heading and a line; the way the work goes, at a glance",
)
def _steps_numbered(c: Ctx) -> dict:
	k = c.look

	def step():
		return column(c, [
			el("p", name="numeral", style=flow(fontFamily=k.font_heading, fontSize="3.5rem", fontWeight="700", lineHeight="1", color=c.ground.accent, margin="0 0 1rem"), text=slot("numeral", "the step number, 01, 02, 03")),
			rule(c, width="3rem", color=c.ground.hair, margin="0 0 1.25rem"),
			*_item_copy(c, "2 to 5 words naming the step", TEXT),
		], "step")

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="36rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "steps-numbered", [container(c, [head, el("div", name="steps", classes=["u-grid", "u-grid--3"], c=[step() for _ in range(3)])])])


@recipe(
	"steps.timeline", ("steps",),
	"a heading on the left and a vertical line of steps on the right, a numeral and its text hung on the line; for a process with an order",
)
def _steps_timeline(c: Ctx) -> dict:
	k = c.look

	def step():
		return el("div", name="step", style=flow(display="grid", gridTemplateColumns="4.5rem 1fr", gap="1.5rem", paddingBottom="2.25rem"), m_style=flow(gridTemplateColumns="3.25rem 1fr", gap="1rem"), c=[
			el("p", name="numeral", style=flow(fontFamily=k.font_heading, fontSize="2.5rem", fontWeight="700", lineHeight="1", color=c.ground.accent, margin="0"), m_style=flow(fontSize="1.75rem"), text=slot("numeral", "the step number, 01, 02, 03")),
			el("div", name="step-copy", style=flow(borderLeft=f"1px solid {c.ground.hair}", paddingLeft="2rem"), m_style=flow(paddingLeft="1rem"), c=_item_copy(c, "2 to 5 words naming the step", TEXT, maxw="34rem")),
		])

	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="22rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words", maxw="22rem", margin="0"),
	], "head")
	return section(c, "steps-timeline", [container(c, [pair(c, "4fr 8fr", [head, el("div", name="timeline", c=[step() for _ in range(4)])], align="start", gap="5rem")])])


@recipe(
	"steps.cards", ("steps",),
	"steps on cards, each with a round numeral badge in the primary colour, a heading and a line; friendly and easy to scan",
	ground="tint",
)
def _steps_cards(c: Ctx) -> dict:
	k = c.look

	def card():
		return el("div", name="step", classes=["u-card"], style=flow(padding="2rem", display="flex", flexDirection="column", alignItems="flex-start"), c=[
			el("span", name="badge", style=flow(display="flex", alignItems="center", justifyContent="center", width="2.75rem", height="2.75rem", borderRadius="50%", backgroundColor=k.primary, color=k.background, fontFamily=k.font_heading, fontSize="1.125rem", fontWeight="700", margin="0 0 1.25rem"), text=slot("numeral", "the step number, 1, 2, 3")),
			*_item_copy(c, "2 to 5 words naming the step", TEXT, size="1.375rem"),
		])

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="36rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "steps-cards", [container(c, [head, el("div", name="steps", classes=["u-grid", "u-grid--3"], c=[card() for _ in range(3)])])])


# ---------------------------------------------------------------- team


@recipe(
	"team.rows", ("team",),
	"the people as ruled rows, the name and the role on the left and a short line about each on the right; no photographs needed",
)
def _team_rows(c: Ctx) -> dict:
	k = c.look

	def row():
		return el("div", name="person", style=flow(display="grid", gridTemplateColumns="1fr 2fr", gap="2rem", padding="1.75rem 0", borderBottom=f"1px solid {c.ground.hair}", alignItems="baseline"), m_style=flow(gridTemplateColumns="1fr", gap="0.75rem"), c=[
			column(c, [
				el("h3", name="person-name", style=flow(fontFamily=k.font_heading, fontSize="1.5rem", fontWeight="700", color=c.ground.ink, margin="0 0 0.3rem"), text=slot("who", "the name exactly as the material gives it, never invented")),
				el("p", name="person-role", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.25em", textTransform="uppercase", color=c.ground.accent, margin="0"), text=slot("note", "the role, 1 to 4 words")),
			], "person-id"),
			el("p", name="person-text", style=flow(fontFamily=k.font_body, fontSize="1.0625rem", lineHeight="1.65", color=c.ground.muted, margin="0", maxWidth="36rem"), text=slot("item-text", "one or two sentences, 20 to 35 words, from the material only")),
		])

	head = column(c, [
		heading(c, "3 to 7 words, one accent word", maxw="24rem", size="2.75rem"),
		paragraph(c, "lead", "one sentence of 15 to 25 words", maxw="24rem", margin="0"),
	], "head")
	return section(c, "team-rows", [container(c, [pair(c, "4fr 8fr", [head, el("div", name="people", c=[row() for _ in range(3)])], align="start", gap="5rem")])])


@recipe(
	"team.monograms", ("team",),
	"the people as round monograms of their initials in the brand colours, a name, a role and a line under each; warm without photographs",
)
def _team_monograms(c: Ctx) -> dict:
	k = c.look

	def person():
		return column(c, [
			el("span", name="monogram", style=flow(display="flex", alignItems="center", justifyContent="center", width="5.5rem", height="5.5rem", borderRadius="50%", backgroundColor=k.primary, color=k.background, fontFamily=k.font_heading, fontSize="1.75rem", fontWeight="700", margin="0 0 1.25rem"), text=slot("initials", "the initials of the person's name, two letters")),
			el("h3", name="person-name", style=flow(fontFamily=k.font_heading, fontSize="1.375rem", fontWeight="700", color=c.ground.ink, margin="0 0 0.25rem"), text=slot("who", "the name exactly as the material gives it, never invented")),
			el("p", name="person-role", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.25em", textTransform="uppercase", color=c.ground.accent, margin="0 0 0.75rem"), text=slot("note", "the role, 1 to 4 words")),
			el("p", name="person-text", style=flow(fontFamily=k.font_body, fontSize="1rem", lineHeight="1.6", color=c.ground.muted, margin="0", maxWidth="20rem"), text=slot("item-text", "one sentence, 15 to 25 words, from the material only")),
		], "person")

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="34rem", size="2.75rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "team-monograms", [container(c, [head, el("div", name="people", classes=["u-grid", "u-grid--3"], c=[person() for _ in range(3)])])])


@recipe(
	"team.portraits", ("team",),
	"portrait photographs of the people in a row, the name and the role beneath each; the face is the point",
	photos=3,
)
def _team_portraits(c: Ctx) -> dict:
	k = c.look

	def person(i):
		return column(c, [
			photo(c, i, "4/5", name="portrait"),
			el("h3", name="person-name", style=flow(fontFamily=k.font_heading, fontSize="1.375rem", fontWeight="700", color=c.ground.ink, margin="1.25rem 0 0.25rem"), text=slot("who", "the name exactly as the material gives it, never invented")),
			el("p", name="person-role", style=flow(fontFamily=k.font_body, fontSize="0.75rem", fontWeight="700", letterSpacing="0.25em", textTransform="uppercase", color=c.ground.accent, margin="0 0 0.75rem"), text=slot("note", "the role, 1 to 4 words")),
			el("p", name="person-text", style=flow(fontFamily=k.font_body, fontSize="1rem", lineHeight="1.6", color=c.ground.muted, margin="0", maxWidth="22rem"), text=slot("item-text", "one sentence, 15 to 25 words, from the material only")),
		], "person", extra={"width": "100%"})

	head = column(c, [heading(c, "3 to 7 words, one accent word", maxw="34rem", size="2.75rem")], "head", extra={"marginBottom": "3rem"})
	return section(c, "team-portraits", [container(c, [head, el("div", name="people", classes=["u-grid", "u-grid--3"], c=[person(0), person(1), person(2)])])])


# fmt: on

# ---------------------------------------------------------------- recipes that need what the business gave

# A band of figures and a wall of quotations show FACTS. Offered a figures recipe, the local plan put a figures section on five pages of a
# site whose material gave one number, and the writer filled them with "100 %" and "48 h" (invented facts left on the published pages,
# 2026-10-21). These families are offered to the plan, and drawn, only when the material the business gave holds what they show.
NUMBER_WORDS = re.compile(
	r"\b(?:deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quinze|vingt|trente|quarante|cinquante|soixante|cent|mille"
	r"|two|three|four|five|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|hundred|thousand"
	r"|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|zwanzig|dreissig|hundert|tausend)\b",
	re.IGNORECASE,
)
QUOTE_WORDS = re.compile(
	r"témoign|\bavis\b|testimon|\breviews?\b|citation|bewertung|zitat|\bquotes?\b|\bretours? clients?\b",
	re.IGNORECASE,
)
MIN_FIGURES = 2


def material_figures(text: str) -> int:
	"""How many distinct figures (digits or number words) the material holds."""
	text = text or ""
	return len(set(re.findall(r"\d+(?:[.,]\d+)?", text)) | {w.lower() for w in NUMBER_WORDS.findall(text)})


def figures_given(material: str | None) -> bool:
	return material is None or material_figures(material) >= MIN_FIGURES


def quotes_given(material: str | None) -> bool:
	return material is None or bool(QUOTE_WORDS.search(material or ""))


GATES = {"figures": figures_given, "testimonials": quotes_given}


def withheld_families(material: str | None) -> set[str]:
	"""The families the business gave nothing for (`material` None = no gate, as in the showcase and the tests)."""
	return {family for family, given in GATES.items() if not given(material)}


def site_material(site: dict) -> str:
	"""What the business gave, as one text: its activity, its positioning, its categories and its brands."""
	parts = [
		site.get("activity"),
		site.get("differentiators"),
		" ".join(site.get("categories") or []),
		" ".join(site.get("brands") or []),
	]
	return " ".join(str(p) for p in parts if p)


# ---------------------------------------------------------------- the catalogue the plan reads


def enabled(conf=None) -> bool:
	"""Whether recipes are in use (`nora_section_recipes`, on unless switched off in site_config)."""
	try:
		import frappe

		conf = conf if conf is not None else frappe.conf
		return str(conf.get("nora_section_recipes", 1)).strip().lower() not in ("0", "false", "no", "off")
	except Exception:
		return True


MOTION_RANK = {"None": 0, "Calm": 1, "Brisk": 2}


def moves_within(r: Recipe, motion: str) -> bool:
	"""Whether a site of this `motion_style` may draw the recipe: a section moves no more than its site does. An unknown style allows everything
	(`Brisk`, what a caller that does not say gets), an unknown recipe motion counts as lively."""
	return MOTION_RANK.get(r.motion, 2) <= MOTION_RANK.get(motion, 2)


def recipes_for(kind: str, has_component: bool = True, motion: str = "Brisk") -> list[Recipe]:
	return [r for r in REGISTRY.values() if kind in r.kinds and (has_component or not r.form) and moves_within(r, motion)]


def eligible_kinds() -> set[str]:
	return {k for r in REGISTRY.values() for k in r.kinds}


def catalogue_lines(seed: str = "", material: str | None = None, motion: str = "Brisk") -> list[str]:
	"""The lines of the plan's prompt that offer the recipes. With a `seed` (the site's name) the variants of each family come in an order
	of the site's own: a model reading a list leans on its first entries, and with one order for every site the first variant of a
	family would be the one every site draws (measured: the same closing band on every page of two sites, 2026-10-21)."""
	lines = [
		"SECTION RECIPES (optional). For a section of one of these kinds you may set `recipe` to one id below when its look serves the "
		"concept; otherwise leave `recipe` empty and design the section yourself, in `layout`, as you would without a catalogue. A recipe is a "
		"starting structure the writer adapts, not a template: say in `layout` what you change (reverse the columns, the ground, the proportions, "
		"an ornament, a different order). Choose for the concept and the rhythm of the page: never the same recipe twice on a page, and do not "
		"give every page the same variants: apart from what the site repeats on purpose (the opening of every interior page, the closing band), a recipe is "
		"drawn on at most two pages of the site, because the variants of a family differ in structure and are there to make this site look unlike another. "
		f"A photograph the client did not give is generated, which is slow: the whole site can afford about {image_budget()} of them, so spend them where the "
		"photograph is the point of the section, and prefer a recipe with fewer photographs elsewhere.",
	]
	by_family: dict[str, list[Recipe]] = {}
	for r in REGISTRY.values():
		if moves_within(r, motion):
			by_family.setdefault(r.family, []).append(r)
	held_back = withheld_families(material)
	for family, recipes in by_family.items():
		if family in held_back:
			continue
		if seed:
			recipes = sorted(recipes, key=lambda r: _seed(seed, r.id))
		kinds = "/".join(sorted({k for r in recipes for k in r.kinds}))
		lines.append(f"- for kind {kinds}:")
		for r in recipes:
			needs = []
			if r.photos:
				needs.append(f"{r.photos} photograph{'s' if r.photos > 1 else ''}")
			if r.form:
				needs.append("the live form as its component")
			if r.motion != "None":
				needs.append("moves, and rests where motion is off")
			lines.append(f"    {r.id}: {r.look}" + (f" ({'; '.join(needs)})" if needs else ""))
	return lines


# ---------------------------------------------------------------- what the page brief says


@dataclass
class Use:
	recipe: Recipe
	yaml: str
	photos: list[str]
	fallback: bool = False


def _seed(*parts) -> int:
	return int(hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:8], 16)


def pick(section, seed: str, taken: dict, motion: str = "Brisk") -> tuple[Recipe | None, bool]:
	"""The recipe for a plan section and whether the code changed the plan's pick: the plan's own pick when it is a recipe of the section's
	kind that the section can carry (another variant of the same family when the plan named it on too many pages of the site); the plan's
	silence stays silence, a free section."""
	has_component = bool((getattr(section, "component", "") or "").strip())
	named = (getattr(section, "recipe", "") or "").strip()
	candidates = recipes_for(section.kind, has_component, motion)
	if named:
		r = REGISTRY.get(named)
		if r and section.kind in r.kinds and (has_component or not r.form) and moves_within(r, motion):
			# past MAX_REPEATS pages the same structure is a pattern, not a choice (the local planner kept the first variant of a family it was
			# offered on four pages of five, whatever the catalogue said): the later pages get another variant of the SAME family, drawn by the site
			if section.kind not in REPEATED_ON_PURPOSE and taken.get(r.id, 0) >= MAX_REPEATS:
				others = [c for c in candidates if c.id != r.id and taken.get(c.id, 0) < MAX_REPEATS]
				if others:
					start = _seed(seed, section.kind, "repeat") % len(others)
					ordered = others[start:] + others[:start]
					return min(ordered, key=lambda c: taken.get(c.id, 0)), True
			return r, False
	return None, False


def allocate_photos(recipe_: Recipe, section_photos: list[str], pool: list[str], mint) -> list[str]:
	"""The photographs for a recipe's slots: the ones the plan gave the section, then the page's own that nobody claimed, then
	placeholders the site fills after the build (`mint(index)` makes one)."""
	urls = list(section_photos)[: recipe_.photos]
	while len(urls) < recipe_.photos and pool:
		urls.append(pool.pop(0))
	while len(urls) < recipe_.photos:
		urls.append(mint(len(urls)))
	return urls


def render(
	r: Recipe,
	look: Look,
	ground: str,
	photos: list[str],
	cta_href: str,
	component: str = "",
	flip: bool = False,
	sample: str | None = None,
) -> str:
	"""The recipe as the writer's YAML; with `sample` (a language) its slots hold sample copy, as the showcase page and the tests need."""
	name = ground if ground in GROUNDS else r.ground
	ctx = Ctx(look, ground_of(look, name), photos, cta_href, component, flip)
	node = r.build(ctx)
	if sample:
		fill_node(node, sample)
	return to_yaml(node)


# a photograph the client did not give is generated, a minute each and one message of a quota every instance shares: a site spends
# at most this many on its recipes (a recipe that would need more is left out and its section is written freely)
IMAGE_BUDGET = 8


def image_budget(conf=None) -> int:
	"""The generated photographs a site may spend on its recipes: `nora_recipe_images` in site_config, else IMAGE_BUDGET."""
	try:
		import frappe

		conf = conf if conf is not None else frappe.conf
		return max(0, int(conf.get("nora_recipe_images", IMAGE_BUDGET)))
	except Exception:
		return IMAGE_BUDGET


def uses_for_page(
	planned_page,
	*,
	handles: dict,
	palette: dict | None,
	page_photos: list[str],
	mint,
	cta_href: str,
	seed: str,
	taken: dict | None = None,
	budget: dict | None = None,
	left_out: list | None = None,
	material: str | None = None,
	skip_kinds=("hero",),
	motion: str = "Brisk",
) -> dict[int, Use]:
	"""{section index: Use} for the sections of a planned page that carry a recipe. `taken` counts the recipes already used on the
	site, so that the same structure is not drawn on every page; `budget` ({"left": n}) the generated
	photographs the site may still spend, and `left_out` collects the recipes dropped for want of one."""
	taken = taken if taken is not None else {}
	budget = budget if budget is not None else {"left": image_budget()}
	look = Look(handles, palette)
	held_back = withheld_families(material)
	pool = list(page_photos)
	for s in planned_page.sections:
		for url in getattr(s, "photos", None) or []:
			if url in pool:
				pool.remove(url)
	out: dict[int, Use] = {}
	used_here: set[str] = set()
	for i, s in enumerate(planned_page.sections):
		if s.kind in skip_kinds:
			continue
		r, by_code = pick(s, f"{seed}|{planned_page.route}|{i}", taken, motion)
		if r is None or r.id in used_here or r.family in held_back:
			continue
		missing = max(0, r.photos - len(getattr(s, "photos", None) or []) - len(pool))
		if missing > budget["left"]:
			if left_out is not None:
				left_out.append(r.id)
			continue
		budget["left"] -= missing
		used_here.add(r.id)
		taken[r.id] = taken.get(r.id, 0) + 1
		# the ground alternates plain and tint down the page unless the recipe asks for its own
		ground = r.ground if r.ground != "plain" else ("tint" if len(out) % 2 else "plain")
		photos = allocate_photos(
			r,
			list(getattr(s, "photos", None) or []),
			pool,
			lambda n, s=s, i=i: mint(f"{planned_page.title}, {(s.purpose or s.kind)[:50]}", n),
		)
		component = (getattr(s, "component", "") or "").strip()
		flip = bool(_seed(seed, planned_page.route, i, "flip") % 2)
		out[i] = Use(r, render(r, look, ground, photos, cta_href, component, flip), photos, by_code)
	return out


def accent_markup(handles: dict) -> str:
	return f'<em style="font-style: italic; color: {handles.get("secondary") or "inherit"}">word</em>'


def brief_lines(uses: dict[int, Use], handles: dict, language: str) -> list[str]:
	"""The page brief's block that gives the structures: one fenced YAML per section, introduced by what the writer may do with it."""
	if not uses:
		return []
	numbers = ", ".join(str(i + 1) for i in sorted(uses))
	lines = [
		f"STARTING STRUCTURES for section {numbers} of the list above (the plan chose them for the concept; they are a starting point you ADAPT, not a template to "
		"copy): each is a section in your YAML format with the site's own handles and the phone fallbacks already written. A text that starts with `WRITE <role>:` is a "
		f"slot: replace the WHOLE text with your own words in {language}, following the role and the length it names (a heading's accent word is wrapped as "
		f"{accent_markup(handles)}); never leave a `WRITE` text in the page. A photograph's src is the one given: keep it, even when it is a placeholder address (the site generates or places the real photograph after the build); never replace it with a plain block or a label, and write its alt as a photographic scene. You may change what makes the section "
		"yours: the proportions, the ground, the order of the inner elements, an ornament, a kicker or an index numeral, the number of items (add or remove rows and cards, "
		"alike) and the copy; the adaptations the plan states win over the structure where they differ. Keep the grid, the classes and the `m_style` fallbacks working. The site draws the page title above an interior page: a heading that only repeats it is removed, so write the section's own.",
	]
	# //// Neoffice — what the writer must not undo in a section that moves (2026-10-30, the motion layer of theme_variables.html)
	if any(u.recipe.motion != "None" for u in uses.values()):
		lines.append(
			"A class that begins `u-reveal`, `u-marquee` or `u-count` is a movement the site draws: keep it on its element. In a strip of words "
			"(`u-marquee__group`) write ONE group of words, the site repeats it by itself; a figure that counts (`u-count`) holds one number written "
			"in digits (a quantity, never a year)."
		)
	for i in sorted(uses):
		lines.append(f"Section {i + 1} ({uses[i].recipe.id}):\n{uses[i].yaml}")
	return lines


# ---------------------------------------------------------------- slots left in a page


def _slot_texts(block: dict):
	text = block.get("innerHTML")
	if isinstance(text, str) and SLOT.match(text):
		yield "innerHTML", text
	for key, value in (block.get("attributes") or {}).items():
		if isinstance(value, str) and SLOT.match(value):
			yield f"attributes.{key}", value


def unfilled_slots(blocks: list) -> list[str]:
	""" "name (tag)" of every block of the page that still carries a `WRITE <role>:` text."""
	from builder.site_ai.nora.layout import _walk

	found = []
	for block in _walk(blocks):
		for _where, text in _slot_texts(block):
			role = re.match(r"^\s*WRITE\s+([\w-]+)", text).group(1)
			found.append(f"{block.get('blockName') or block.get('element') or 'unnamed'} ({role})")
	return found


def scrub_unfilled(blocks: list) -> int:
	"""Removes what `unfilled_slots` found: a text block is dropped, an attribute is emptied. Returns the number of slots removed."""
	from builder.site_ai.nora.layout import _walk

	removed = 0
	for block in _walk(blocks):
		kids = block.get("children")
		if isinstance(kids, list):
			keep = []
			for child in kids:
				if (
					isinstance(child, dict)
					and isinstance(child.get("innerHTML"), str)
					and SLOT.match(child["innerHTML"])
					and not child.get("children")
				):
					removed += 1
					continue
				keep.append(child)
			if len(keep) != len(kids):
				block["children"] = keep
		attrs = block.get("attributes")
		if isinstance(attrs, dict):
			for key, value in list(attrs.items()):
				if isinstance(value, str) and SLOT.match(value):
					attrs[key] = ""
					removed += 1
	return removed


# ---------------------------------------------------------------- pictures the writer made up

FOREIGN = re.compile(r"^(?:https?:)?//", re.IGNORECASE)


def replace_invented_pictures(blocks: list, offered, make) -> list[str]:
	"""Given a photograph slot, a writer of this size replaced its placeholder with an address it remembered or made up
	(images.unsplash.com/photo-..., picsum.photos/seed/...): ids that may be gone, never the photograph of this business (2026-10-21).
	An <img> that points to a foreign host and was not offered to the page is given a placeholder again (`make(alt)` makes one), which
	the site fills with a generated photograph from the alt text; with `make` None, or when it returns None (a page that carries no
	photograph, a legal one; a site that has spent its generated photographs) the picture is taken out. Local files, data URIs and the placeholders themselves are never touched. Returns one line per edit."""
	from builder.site_ai.nora.layout import _walk

	allowed = set(offered or ())
	edits = []
	for block in _walk(blocks):
		kids = block.get("children")
		if not isinstance(kids, list):
			continue
		kept = []
		for child in kids:
			attrs = child.get("attributes") if isinstance(child, dict) else None
			src = str((attrs or {}).get("src") or "").strip()
			if (
				isinstance(child, dict)
				and str(child.get("element") or "").lower() == "img"
				and src
				and FOREIGN.match(src)
				and "placehold.co" not in src
				and src not in allowed
			):
				placeholder = make(str(attrs.get("alt") or "")) if make else None
				if placeholder is None:
					edits.append(f"picture address made up, taken out: {src[:70]}")
					continue
				attrs["src"] = placeholder
				edits.append(f"picture address made up, back to a placeholder: {src[:70]}")
			kept.append(child)
		if len(kept) != len(kids):
			block["children"] = kept
	return edits


# ---------------------------------------------------------------- sample copy (the showcase and the tests)

SAMPLES = {
	"fr": {
		"label": "Notre maison",
		"heading": 'Une table qui a du <em style="font-style: italic">caractère</em>',
		"lead": "Une phrase qui dit ce que fait la maison, simplement et sans détour.",
		"text": "Deux ou trois phrases concrètes sur ce que l'on fait, pour qui, et ce qui change pour la personne qui nous fait confiance, écrites avec les faits de l'entreprise.",
		"note": "Dit comme on le dit à quelqu'un qu'on connaît.",
		"link": "En savoir plus",
		"button": "Nous écrire",
		"alt": "Une photographie du lieu",
		"item-title": "Un nom court",
		"item-text": "Une ligne qui précise de quoi il s'agit, en une phrase.",
		"price": "CHF 28",
		"quote": "Une phrase de client, simple et vraie, qui dit pourquoi il revient.",
		"who": "Prénom Nom",
		"numeral": "01",
		"initials": "AB",
		"figure": "25",
		"figure-label": "années d'expérience",
		"question": "Une question que posent vraiment les clients ?",
		"answer": "Une réponse claire en deux phrases, tirée des faits de l'entreprise, sans détour ni promesse en l'air.",
		"detail-label": "Adresse",
		"detail-value": "Rue du Exemple 1, 1950 Sion",
	},
	"en": {
		"label": "Our house",
		"heading": 'A table with <em style="font-style: italic">character</em>',
		"lead": "One sentence on what the house does, plainly.",
		"text": "Two or three concrete sentences on what we do, for whom, and what changes for the person who trusts us, written from the facts of the business.",
		"note": "Said the way you say it to someone you know.",
		"link": "Learn more",
		"button": "Write to us",
		"alt": "A photograph of the place",
		"item-title": "A short name",
		"item-text": "One line saying what it is, in a sentence.",
		"price": "CHF 28",
		"quote": "A customer's sentence, simple and true, saying why they come back.",
		"who": "First Last",
		"numeral": "01",
		"initials": "AB",
		"figure": "25",
		"figure-label": "years of experience",
		"question": "A question customers really ask?",
		"answer": "A clear answer in two sentences, from the facts of the business, with no empty promise.",
		"detail-label": "Address",
		"detail-value": "1 Example Street, 1950 Sion",
	},
}


def fill_node(node, language: str = "fr") -> None:
	"""Puts sample copy in place of every slot of a recipe's node, in place."""
	table = SAMPLES.get((language or "fr")[:2].lower(), SAMPLES["fr"])

	def sample(text: str) -> str:
		role = re.match(r"^\s*WRITE\s+([\w-]+)", text).group(1)
		return table.get(role) or table["text"]

	def visit(value):
		if isinstance(value, dict):
			for key, item in value.items():
				if isinstance(item, str) and SLOT.match(item):
					value[key] = sample(item)
				else:
					visit(item)
		elif isinstance(value, list):
			for index, item in enumerate(value):
				if isinstance(item, str) and SLOT.match(item):
					value[index] = sample(item)
				else:
					visit(item)

	visit(node)
