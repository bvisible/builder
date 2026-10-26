# //// Neoffice — added file (no upstream equivalent): the dividers between the sections of a generated page.
"""A page that is a stack of straight-edged bands reads as a template. What separates a site made by a designer from one made by a form is
how its sections meet: a wave, a ridge of mountains, a hill, a slope, a torn edge. The page writer used to draw those itself, one SVG per
page, in a different style on each, and badly (a row of identical triangles, a zigzag thin as a hair). Here the SITE draws them, one style
for all its pages, chosen by the design brief (`section_divider`) or, when the brief says nothing, by the words of its art direction.

What is built, between two consecutive sections of a page (the children of the page root):
- two sections with different flat grounds: a band that is the ground of the first, with the second one rising into it as a shape of
  several translucent layers (depth), alternately mirrored so two dividers of a page are never twins;
- two sections with the same flat ground: only a fine line in the accent, a ridge that separates without cutting;
- a section whose ground is a photograph or a gradient (a hero): the shape overlaps its foot, which gets the room it needs, so a photograph
  also ends in a wave and not in a ruler;
- anything else (two photographs, a section that overlaps its neighbour on purpose): left alone.

Every shape is generated from a seed (the page, the position), so a site never repeats a divider and a rebuild draws the same ones. A
divider is a block of its own (`nora-divider`) that a second run removes and draws again; it is never text, always aria-hidden, and it
follows the tokens of the site because it is filled with the very value of the ground it meets. The divider an older page writer drew
by itself (a wide, flat SVG with no text) is removed when a style is applied."""

import hashlib
import math
import random
import re
import uuid

from builder.site_ai.nora.contrast import composite, parse_color

STYLES = ("wave", "hills", "curve", "tilt", "peaks", "torn")
OFF = "none"
VALID = (*STYLES, OFF)

MARK = "nora-divider"
ROOM = "nora-divider-room"
WIDTH, HEIGHT = 1200, 100
#: the fill runs this far past the band, over the section it meets: a band that ends on a fraction of a pixel leaves a hairline
SEAM = 6

#: (lowest px, vw, highest px) of the band a style draws: it grows with the screen and stops where it would start to dominate
SIZES = {
	"wave": (28, 6.5, 92),
	"hills": (30, 7, 100),
	"curve": (24, 5.5, 80),
	"tilt": (22, 5, 72),
	"peaks": (34, 8, 112),
	"torn": (14, 2.6, 34),
}
LINE_SIZE = (22, 3.6, 46)
#: a fine line is drawn at most this many times on a page: more than that is a ruled notebook
MAX_LINES = 3

SYNONYMS = {
	"waves": "wave", "wavy": "wave", "vague": "wave", "vagues": "wave",
	"hill": "hills", "dunes": "hills", "dune": "hills", "colline": "hills", "collines": "hills",
	"arc": "curve", "curved": "curve", "round": "curve", "courbe": "curve",
	"diagonal": "tilt", "slope": "tilt", "slant": "tilt", "slanted": "tilt", "angle": "tilt", "angled": "tilt",
	"mountain": "peaks", "mountains": "peaks", "ridge": "peaks", "ridges": "peaks", "alpine": "peaks", "montagne": "peaks", "montagnes": "peaks",
	"peak": "peaks", "skyline": "peaks",
	"paper": "torn", "ripped": "torn", "rough": "torn", "deckle": "torn",
	"off": OFF, "flat": OFF, "straight": OFF, "no": OFF, "aucun": OFF, "droite": OFF, "droites": OFF,
}

#: what the art direction says, when the brief names no style: the style whose words it uses most
WORDS = (
	("peaks", r"mountain|montagne|alpine|alpin|alps?\b|peaks?\b|ridge|summit|sommet|glacier|berg|montagna|cime"),
	("wave", r"waves?\b|vagues?\b|ocean|océan|sea\b|mer\b|lake|lac\b|water|\beau\b|swim|flow|fluid|coast|côte|wellness|spa\b|marine|nautical|onde"),
	("hills", r"hills?\b|collines?|vineyards?|vignes?|vignoble|fields?\b|champs?\b|garden|jardin|farm|ferme|meadow|pré\b|countryside|campagne|organic|organique|natural|naturel|botanic|florist|fleur"),
	("torn", r"paper|papier|print|imprim|craft|artisan|hand-?made|fait main|bakery|boulanger|torn|déchir|rustic|rustique|letterpress|vintage|retro|rétro"),
	("tilt", r"diagonal|angular|angle|geometric|géométri|architect|industrial|industriel|sharp|tech\b|fintech|dynamic|dynamique|motion|speed|vitesse"),
)
DEFAULT = "curve"


def normalise(value: str | None) -> str:
	"""A style of the list, or "" when the value names none."""
	word = re.sub(r"[^a-zà-ÿ ]", "", str(value or "").lower()).strip()
	if word in VALID:
		return word
	if word in SYNONYMS:
		return SYNONYMS[word]
	for token in word.split():
		if token in VALID:
			return token
		if token in SYNONYMS:
			return SYNONYMS[token]
	return ""


def style_for(value: str | None, *texts: str) -> str:
	"""The style of a site: what its brief says, else the one its art direction speaks of, else a sober curve."""
	named = normalise(value)
	if named:
		return named
	text = " ".join(t for t in texts if t).lower()
	scores = {style: len(re.findall(pattern, text)) for style, pattern in WORDS}
	best = max(scores.values()) if scores else 0
	if best:
		return next(style for style, _ in WORDS if scores[style] == best)
	return DEFAULT


def site_palette(prefix: str) -> dict[str, str]:
	"""Every colour token of the site (`<prefix>-primary`, `-tint`, `-surface`…), not only the five the build's own palette holds: a
	section laid on `var(--<prefix>-tint)` is a flat ground too."""
	import frappe

	try:
		rows = frappe.get_all("Builder Token", filters={"name": ["like", f"{prefix}-%"]}, fields=["name", "value"], limit_page_length=0)
	except Exception:
		return {}
	return {row.name: row.value for row in rows if row.value}


def _rng(seed: str) -> random.Random:
	return random.Random(int(hashlib.sha1(seed.encode()).hexdigest()[:12], 16))


# ---- the edges: lists of (x, y) in a 1200 x 100 box, y growing downward; the shape is what lies BELOW the edge ----


def _clamp(y: float) -> float:
	return max(2.0, min(HEIGHT - 2.0, y))


def _waves(rng: random.Random, base: float, amp: float, cycles: float, steps: int = 60) -> list[tuple[float, float]]:
	one, two = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
	points = []
	for i in range(steps + 1):
		t = i / steps
		y = base + amp * (0.72 * math.sin(2 * math.pi * cycles * t + one) + 0.28 * math.sin(2 * math.pi * cycles * 2.3 * t + two))
		points.append((t * WIDTH, _clamp(y)))
	return points


def _humps(rng: random.Random, base: float, amp: float, count: int) -> list[tuple[float, float]]:
	return [(i * WIDTH / (count - 1), _clamp(base + rng.uniform(-amp, amp))) for i in range(count)]


def _skyline(rng: random.Random, floor: float, rise: float, peaks: int, steps: int = 120) -> list[tuple[float, float]]:
	"""A ridge: steep cones of random height and width, the valleys between them never flat (a gentle swell), the slopes made uneven by
	a wandering of their height and a small tremor, so no two peaks are cut from the same pattern."""
	xs = sorted(rng.uniform(0.04, 0.96) for _ in range(peaks))
	heights = [rng.uniform(0.42, 1.0) for _ in range(peaks)]
	slopes = [rng.uniform(8.0, 15.0) for _ in range(peaks)]
	wander = [rng.uniform(-0.16, 0.16) for _ in range(25)]
	swell_phase = rng.uniform(0, 2 * math.pi)
	points = []
	for i in range(steps + 1):
		t = i / steps
		cone = max(h - s * abs(t - x) for x, h, s in zip(xs, heights, slopes, strict=True))
		swell = 0.14 + 0.1 * math.sin(2 * math.pi * 2.2 * t + swell_phase)
		slot = t * 24
		slow = wander[int(slot)] * (1 - slot % 1) + wander[min(24, int(slot) + 1)] * (slot % 1)
		elevation = max(swell, cone * (1 + slow)) + rng.uniform(-0.012, 0.012)
		points.append((t * WIDTH, _clamp(floor - rise * elevation)))
	return points


def _torn_edge(rng: random.Random, base: float, amp: float, steps: int = 130) -> list[tuple[float, float]]:
	points, y = [], base
	for i in range(steps + 1):
		y += rng.uniform(-amp, amp) * 0.55
		y = base + (y - base) * 0.82
		spike = rng.uniform(-amp, amp) * 1.6 if rng.random() < 0.05 else 0.0
		points.append((i * WIDTH / steps, _clamp(y + spike + rng.uniform(-amp, amp) * 0.25)))
	return points


def _arc(rng: random.Random, convex: bool, lift: float = 0.0) -> list[tuple[float, float]]:
	"""One broad, shallow arc, the middle bulging up (convex) or dipping (concave): a parabola, so the ends meet the edges gently."""
	depth = rng.uniform(0.5, 0.72) * HEIGHT
	steps = 30
	points = []
	for i in range(steps + 1):
		t = 2 * i / steps - 1
		bow = 1 - t * t
		y = HEIGHT * 0.94 - depth * bow if convex else HEIGHT * 0.22 + depth * (1 - bow) * 0.95
		points.append((i * WIDTH / steps, _clamp(y - lift)))
	return points


def _slope(rises_right: bool, lift: float = 0.0) -> list[tuple[float, float]]:
	low, high = max(0.0, HEIGHT * 0.94 - lift), max(0.0, HEIGHT * 0.06 - lift)
	return [(0.0, low if rises_right else high), (float(WIDTH), high if rises_right else low)]


def _smooth(points: list[tuple[float, float]]) -> str:
	"""A Catmull-Rom curve through the points, as cubic Béziers (a wave is a curve, not 60 corners)."""
	d = [f"M{points[0][0]:.0f},{points[0][1]:.1f}"]
	for i in range(len(points) - 1):
		p0 = points[max(i - 1, 0)]
		p1, p2 = points[i], points[i + 1]
		p3 = points[min(i + 2, len(points) - 1)]
		c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
		c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
		d.append(f"C{c1[0]:.0f},{c1[1]:.1f} {c2[0]:.0f},{c2[1]:.1f} {p2[0]:.0f},{p2[1]:.1f}")
	return " ".join(d)


def _polyline(points: list[tuple[float, float]]) -> str:
	return "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in points)


def layers(style: str, seed: str, lines: bool = False) -> list[tuple[str, float, bool]]:
	"""The edges of a style, back to front: (path of the edge, opacity of the layer, whether a fine ridge line is drawn along it).
	`lines` asks for the edges only: the fine line of a boundary between two sections of one ground."""
	rng = _rng(f"{style}:{seed}")
	if style == "wave":
		count = rng.uniform(1.1, 2.0)
		edges = [(_smooth(_waves(rng, base * HEIGHT, amp * HEIGHT, count * k)), opacity, False)
			for base, amp, k, opacity in ((0.30, 0.21, 0.8, 0.22), (0.5, 0.23, 1.0, 0.5), (0.72, 0.23, 1.2, 1.0))]
	elif style == "hills":
		edges = [(_smooth(_humps(rng, base * HEIGHT, amp * HEIGHT, n)), opacity, False)
			for base, amp, n, opacity in ((0.38, 0.30, 5, 0.32), (0.7, 0.27, 6, 1.0))]
	elif style == "peaks":
		edges = [(_polyline(_skyline(rng, floor * HEIGHT, rise * HEIGHT, n)), opacity, ridge)
			for floor, rise, n, opacity, ridge in ((0.76, 0.66, 4, 0.2, True), (0.9, 0.62, 5, 0.45, True), (1.0, 0.5, 6, 1.0, False))]
	elif style == "torn":
		edges = [(_polyline(_torn_edge(rng, HEIGHT * 0.56, HEIGHT * 0.2)), 1.0, False)]
	elif style == "curve":
		convex = rng.random() < 0.5
		state = rng.getstate()
		edges = [(_smooth(_arc(rng, convex, HEIGHT * 0.16)), 0.28, False)]
		rng.setstate(state)
		edges.append((_smooth(_arc(rng, convex)), 1.0, False))
	else:  # tilt
		rises = rng.random() < 0.5
		edges = [(_polyline(_slope(rises, HEIGHT * 0.2)), 0.28, False), (_polyline(_slope(rises)), 1.0, False)]
	if lines:
		kept = edges[-2:] if style in ("wave", "peaks") else edges[-1:]
		return [(d, 0.5 if i == len(kept) - 1 else 0.28, False) for i, (d, _, _) in enumerate(kept)]
	return edges


def band_size(style: str, lines: bool = False) -> str:
	low, vw, high = LINE_SIZE if lines else SIZES[style]
	return f"clamp({low}px, {vw}vw, {high}px)"


def svg(style: str, seed: str, paint: str, flip_y: bool = False, lines: bool = False) -> str:
	"""The drawing. `paint` is the CSS value of the ground that rises (or of the accent, for a line): a hex, or the var() of a token."""
	body = []
	for edge, opacity, ridge in layers(style, seed, lines):
		if lines:
			body.append(f'<path d="{edge}" fill="none" style="stroke:{paint}" stroke-width="1.25" stroke-opacity="{opacity}" vector-effect="non-scaling-stroke"/>')
			continue
		body.append(f'<path d="{edge} L{WIDTH},{HEIGHT + SEAM} L0,{HEIGHT + SEAM} Z" style="fill:{paint}" fill-opacity="{opacity}"/>')
		if ridge:
			body.append(f'<path d="{edge}" fill="none" style="stroke:{paint}" stroke-width="1" stroke-opacity="0.6" vector-effect="non-scaling-stroke"/>')
	group = f'<g transform="matrix(1 0 0 -1 0 {HEIGHT})">' if flip_y else "<g>"
	return (
		f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" preserveAspectRatio="none" aria-hidden="true" focusable="false" '
		f'style="display:block;width:100%;height:100%;overflow:visible">{group}{"".join(body)}</g></svg>'
	)


# ---- the page: which boundaries get a divider, and of what kind ----


def _walk(block: dict, depth: int = 0):
	yield block, depth
	for child in block.get("children") or []:
		yield from _walk(child, depth + 1)


def _classes(block: dict) -> list[str]:
	value = block.get("classes") or []
	return list(value) if isinstance(value, list) else str(value).split()


def _covers(block: dict) -> bool:
	"""A photograph, a gradient or an overlay laid over its parent: the section is not a flat ground."""
	styles = block.get("baseStyles") or {}
	if styles.get("position") != "absolute":
		return False
	if block.get("element") == "img" or styles.get("objectFit"):
		return True
	raw = f"{styles.get('backgroundImage') or ''} {styles.get('background') or ''}".strip()
	return bool(raw) and raw != "none" and parse_color(raw, {}) is None


def _hex(color: tuple) -> str:
	return "#{:02x}{:02x}{:02x}".format(*(round(c) for c in color[:3]))


def ground(section: dict, palette: dict, page_ground: str) -> tuple[str, str]:
	"""("plain", the CSS value of its flat ground) or ("picture", ""): a section laid on a photograph, a gradient or a covering overlay.
	A translucent tint (the recipes' `rgba(brand, 0.08)`) is a flat ground: the colour it makes over the page. A token of the site's own
	that nothing defines (the writer invents `--<prefix>-tint`) paints nothing, so the page shows through: the page ground."""
	styles = section.get("baseStyles") or {}
	image = f"{styles.get('backgroundImage') or ''}"
	background = str(styles.get("backgroundColor") or styles.get("background") or "").strip()
	if (image and image != "none") or "gradient" in background or "url(" in background:
		return "picture", ""
	if any(_covers(child) for child, depth in _walk(section) if 0 < depth <= 4):
		return "picture", ""
	under = parse_color(page_ground, palette)
	if under is None:
		return "picture", ""
	if not background:
		return "plain", page_ground
	color = parse_color(background, palette)
	if color is None:
		named = re.match(r"^var\(\s*--([A-Za-z0-9_-]+)\s*\)$", background)
		own = {name.split("-")[0] for name in palette}
		if named and named.group(1).split("-")[0] in own:
			return "plain", page_ground
		return "picture", ""
	if color[3] == 0:
		return "plain", page_ground
	if color[3] >= 0.99:
		return "plain", background
	return "plain", _hex(composite(color, (under[0], under[1], under[2], 1.0)))


def _same(a: str, b: str, palette: dict) -> bool:
	ca, cb = parse_color(a, palette), parse_color(b, palette)
	if ca is None or cb is None:
		return a.strip() == b.strip()
	return max(abs(ca[i] - cb[i]) for i in range(3)) < 7


def _split(value: str) -> list[str]:
	"""The words of a CSS shorthand, a clamp() or a var() staying whole."""
	words, depth, current = [], 0, ""
	for char in str(value):
		if char == "(":
			depth += 1
		elif char == ")":
			depth -= 1
		if char.isspace() and depth == 0:
			if current:
				words.append(current)
			current = ""
		else:
			current += char
	if current:
		words.append(current)
	return words


def _expand_padding(styles: dict) -> None:
	if "padding" not in styles:
		return
	words = _split(styles.pop("padding")) or ["0"]
	top, right, bottom, left = {1: (0, 0, 0, 0), 2: (0, 1, 0, 1), 3: (0, 1, 2, 1)}.get(len(words), (0, 1, 2, 3))
	for side, index in (("Top", top), ("Right", right), ("Bottom", bottom), ("Left", left)):
		styles.setdefault(f"padding{side}", words[index])


def _add_room(section: dict, side: str, amount: str) -> bool:
	"""Room for the shape that overlaps the foot (or the head) of a section: its padding grows by the height of the band, on every
	screen size the page styles (a phone's own padding would otherwise win)."""
	if ROOM + side in _classes(section):
		return False
	for key in ("baseStyles", "tabletStyles", "mobileStyles"):
		styles = section.get(key)
		if key != "baseStyles" and not (isinstance(styles, dict) and any(k in styles for k in ("padding", f"padding{side}"))):
			continue
		styles = section.setdefault(key, {})
		_expand_padding(styles)
		current = str(styles.get(f"padding{side}") or "").strip()
		styles[f"padding{side}"] = amount if current in ("", "0", "0px", "0rem", "0em") else f"calc({current} + {amount})"
	section["classes"] = [*_classes(section), ROOM + side]
	return True


def _is_divider(block: dict) -> bool:
	return MARK in _classes(block)


def _viewbox(html: str) -> tuple[float, float] | None:
	found = re.search(r'viewBox\s*=\s*["\']\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', html, re.I)
	return (float(found.group(1)), float(found.group(2))) if found else None


def is_drawn_divider(block: dict) -> bool:
	"""A wide, flat drawing with no text: what an older page writer drew between two sections. An icon is square and a small flourish
	under a heading is narrow: both stay."""
	html = block.get("innerHTML")
	if _is_divider(block) or block.get("children") or not isinstance(html, str) or not html.lstrip().lower().startswith("<svg") or "<text" in html.lower():
		return False
	box = _viewbox(html)
	return bool(box) and box[0] >= 400 and box[1] > 0 and box[0] / box[1] >= 10


def _drop(parent: dict) -> int:
	"""Remove the drawn dividers under a block, and the wrapper a divider leaves empty (the writer put its drawing in a band of its own)."""
	kept, dropped = [], 0
	for child in parent.get("children") or []:
		if is_drawn_divider(child):
			dropped += 1
			continue
		found = _drop(child)
		dropped += found
		if found and not child.get("children") and not str(child.get("innerHTML") or "").strip():
			continue
		kept.append(child)
	if "children" in parent:
		parent["children"] = kept
	return dropped


def _band(style: str, seed: str, index: int, kind: str, shown: str, behind: str, lines: bool) -> dict:
	"""The divider block. kind: "between" (a band of the first ground), "over-foot" (laid over the foot of the section above),
	"over-head" (laid over the head of the section below)."""
	size = band_size(style, lines)
	styles = {"position": "relative", "zIndex": "2", "width": "100%", "height": size, "lineHeight": "0", "pointerEvents": "none"}
	if kind == "between":
		styles["backgroundColor"] = behind
		styles["marginTop"], styles["marginBottom"] = "-1px", "-1px"
	elif kind == "over-foot":
		styles["marginTop"], styles["marginBottom"] = f"calc(-1 * {size})", "-1px"
	else:
		styles["marginTop"], styles["marginBottom"] = "-1px", f"calc(-1 * {size})"
	if index % 2:
		styles["transform"] = "scaleX(-1)"
	return {
		"blockId": uuid.uuid4().hex[:10],
		"element": "div",
		"blockName": "section-divider",
		"classes": [MARK],
		"attributes": {"aria-hidden": "true"},
		"baseStyles": styles,
		"innerHTML": svg(style, seed, shown, flip_y=kind == "over-head", lines=lines),
		"children": [],
	}


def chrome_grounds(config, prefix: str, is_home: bool) -> tuple[str, str]:
	"""(the ground of the band above the page, the ground of the footer below it) as CSS values, "" where the chrome shows none or one that
	cannot be told (a photograph, a tint): the top of an interior page when the site draws a band over a plain or solid fill, the footer
	whenever it has a colour. `config` is the site's chrome (a Document or a dict)."""
	get = config.get if hasattr(config, "get") else (lambda key, default=None: default)
	top = ""
	if not is_home and (get("page_header_template") or "Standard") in ("Minimal", "Standard", "Centered", "Split"):
		fill = get("page_header_background") or "None"
		if fill == "None":
			top = f"var(--{prefix}-background)"
		elif fill == "Solid" and get("page_header_bg_color"):
			top = str(get("page_header_bg_color"))
	return top, str(get("footer_bg_color") or "")


def apply_dividers(blocks: list, palette: dict, style: str, seed: str = "", accent: str = "", top: str = "", bottom: str = "") -> list[str]:
	"""Draw the dividers of a page, in place. `style` is one of STYLES (OFF or anything else does nothing), `seed` names the page, `accent`
	is the CSS colour of a fine line between two sections of the same ground ("" draws none), `top` and `bottom` are the grounds of what the
	page sits between (the band under the site header, the footer): the page then also meets them in a shape. Returns one line per edit."""
	if style not in STYLES or not blocks or not isinstance(blocks[0], dict):
		return []
	root = blocks[0]
	edits = []
	dropped = _drop(root)
	if dropped:
		edits.append(f"{dropped} divider drawn by the writer removed")
	root["children"] = [c for c in root.get("children") or [] if not _is_divider(c)]
	sections = root["children"]
	if not sections:
		return edits
	page_ground = str((root.get("baseStyles") or {}).get("backgroundColor") or "#ffffff")
	# the sections, with what sits above and below the page as two grounds of their own: (index in sections or None, ground)
	ring = [(None, ("plain", top))] if top and parse_color(top, palette) else []
	ring += [(i, ground(s, palette, page_ground) if s.get("element") == "section" else ("other", "")) for i, s in enumerate(sections)]
	if bottom and parse_color(bottom, palette):
		ring.append((None, ("plain", bottom)))
	lines_drawn = 0
	plan = []
	for n in range(len(ring) - 1):
		(i, (ka, ca)), (j, (kb, cb)) = ring[n], ring[n + 1]
		after = 0 if i is None else i + 1
		if "other" in (ka, kb) or (j is not None and str((sections[j].get("baseStyles") or {}).get("marginTop") or "").strip().startswith("-")):
			continue
		if ka == "plain" and kb == "plain":
			if not _same(ca, cb, palette):
				plan.append((after, i, j, "between", cb, ca, False))
			elif accent and i is not None and j is not None and lines_drawn < MAX_LINES:
				lines_drawn += 1
				plan.append((after, i, j, "between", accent, ca, True))
		elif kb == "plain":
			plan.append((after, i, j, "over-foot", cb, "", False))
		elif ka == "plain":
			plan.append((after, i, j, "over-head", ca, "", False))
	for after, i, j, kind, shown, behind, lines in reversed(plan):
		band = _band(style, f"{seed}:{after}", after, kind, shown, behind, lines)
		if kind == "over-foot" and i is not None:
			_add_room(sections[i], "Bottom", band_size(style))
		elif kind == "over-head" and j is not None:
			_add_room(sections[j], "Top", band_size(style))
		sections.insert(after, band)
		place = "above the page" if i is None else "below the page" if j is None else f"after section {i + 1}"
		edits.append(f"{style} {'line' if lines else kind} {place}")
	return edits
