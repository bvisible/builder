# //// Neoffice — added file (no upstream equivalent): legibility repair of generated blocks.
"""Text that cannot be read on its background, fixed mechanically after the model
wrote the page.

The model picks a token for a band's background and a text colour for what sits
on it, but it knows the tokens by their role (primary, secondary, background,
text), not by their luminance. A cream secondary under white copy, the invisible
CTA band of neoffice-maintenance #281, is the failure this repairs: every block
that sets a text colour, or inherits one onto a new background, is checked
against the WCAG ratio and rewritten to the palette colour that reads best there.

Pure functions: no frappe, so the rules are unit-testable and the brief prompt can
reuse the luminance reading (palette_roles).
"""

from __future__ import annotations

import copy
import re

HEX = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
RGB = re.compile(r"^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$")
VAR = re.compile(r"^var\(\s*--([A-Za-z0-9_-]+)\s*(?:,\s*(.+?)\s*)?\)$")
NAMED = {"white": (255.0, 255.0, 255.0, 1.0), "black": (0.0, 0.0, 0.0, 1.0), "transparent": (0.0, 0.0, 0.0, 0.0)}

#: WCAG threshold for large text and UI components; the brief validator uses the
#: same bar for the primary colour, so the two rules agree on what "readable" is.
MIN_RATIO = 3.0

Color = tuple[float, float, float, float]


def parse_color(value: str | None, palette: dict[str, str]) -> Color | None:
    """(r, g, b, a) with channels in 0..255 and alpha in 0..1, or None when the
    value is not a flat colour (an image, a gradient, an unknown variable)."""
    value = (value or "").strip()
    if not value:
        return None
    m = VAR.match(value)
    if m:
        name, fallback = m.group(1), m.group(2)
        if name in palette:
            return parse_color(palette[name], palette)
        return parse_color(fallback, palette) if fallback else None
    if value.lower() in NAMED:
        return NAMED[value.lower()]
    m = HEX.match(value)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (float(r), float(g), float(b), a)
    m = RGB.match(value)
    if m:
        r, g, b = (min(255.0, float(x)) for x in m.groups()[:3])
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, max(0.0, min(1.0, a)))
    return None


def composite(fg: Color, bg: Color) -> Color:
    """fg laid over an opaque bg, as the eye sees it."""
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1.0)


def luminance(color: Color) -> float:
    def channel(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in color[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(c1: Color, c2: Color) -> float:
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def palette_roles(palette: dict[str, str]) -> str:
    """One line for the page brief: which handles are light, which are dark, so the
    model stops putting white copy on a cream 'secondary'."""
    parts = []
    for name, value in palette.items():
        parsed = parse_color(value, palette)
        if parsed is None:
            continue
        lum = luminance(parsed)
        if lum <= 0.2:
            role = "DARK, light text on it"
        elif lum <= 0.4:
            role = "MID, an accent: white text on it is borderline, never a text band"
        else:
            role = "LIGHT, dark text on it, never white"
        parts.append(f"var(--{name}) = {value} ({role})")
    return "; ".join(parts)


def _has_text(block: dict) -> bool:
    # //// Neoffice — added check (40dc4a09 "fix(contrast): a data-bound heading is text, and
    # //// frappe's cards read on a dark site"): a repeater's template carries its text through
    # //// a binding, not innerHTML, so the walker skipped it and left light text on white.
    # a repeater's template carries its text through a binding, not in innerHTML: the
    # trust cards of a reseller site's home kept light text on white (2026-09-09)
    if any((d or {}).get("property") == "innerHTML" for d in block.get("dynamicValues") or []):
        return True
    html = block.get("innerHTML") or ""
    if not isinstance(html, str):
        html = str(html)
    if html and not html.lstrip().lower().startswith("<svg"):
        if re.sub(r"<[^>]+>", "", html).strip():
            return True
    return any(_has_text(c) for c in block.get("children") or [])


def _covers_parent(block: dict) -> bool:
    """A photo or an overlay laid over its parent: an absolutely positioned image,
    a gradient, an image background. What sits next to it is read on that
    photo, not on the parent's colour."""
    styles = block.get("baseStyles") or {}
    if styles.get("position") != "absolute":
        return False
    if block.get("element") == "img" or styles.get("objectFit"):
        return True
    raw = styles.get("backgroundImage") or styles.get("background") or ""
    return bool(raw) and parse_color(raw, {}) is None


def _classes(block: dict) -> list[str]:
    classes = block.get("classes") or []
    return classes if isinstance(classes, list) else str(classes).split()


def best_text(bg: Color, palette: dict[str, str], minimum: float = MIN_RATIO) -> tuple[str, Color]:
    """The palette text or background handle that reads best on bg; a literal
    white or near-black only when neither handle reaches the bar."""
    candidates: list[tuple[str, Color]] = []
    for name, value in palette.items():
        if name.endswith(("-text", "-background")):
            parsed = parse_color(value, palette)
            if parsed is not None and parsed[3] == 1.0:
                candidates.append((f"var(--{name})", parsed))
    handles = sorted(candidates, key=lambda c: contrast(c[1], bg), reverse=True)
    if handles and contrast(handles[0][1], bg) >= minimum:
        return handles[0]
    literals = [("#ffffff", NAMED["white"]), ("#111111", (17.0, 17.0, 17.0, 1.0))]
    return max(literals, key=lambda c: contrast(c[1], bg))


def _mix(color: Color, target: Color, share: float) -> Color:
    return (
        color[0] * (1 - share) + target[0] * share,
        color[1] * (1 - share) + target[1] * share,
        color[2] * (1 - share) + target[2] * share,
        1.0,
    )


def accent_shade(handle: str, fg: Color, bg: Color, minimum: float = MIN_RATIO) -> tuple[str, Color] | None:
    """A deeper (or lighter) shade of an accent that still points at its token:
    color-mix() keeps the retheme live, the kicker keeps the brand hue. Tried in
    10% steps up to 70%; None when even that does not read."""
    towards, name = (NAMED["black"], "black") if luminance(bg) > 0.18 else (NAMED["white"], "white")
    for pct in range(10, 71, 10):
        mixed = _mix(fg, towards, pct / 100)
        if contrast(mixed, bg) >= minimum:
            return f"color-mix(in srgb, {handle} {100 - pct}%, {name})", mixed
    return None


def repair_contrast(blocks: list[dict], palette: dict[str, str], minimum: float = MIN_RATIO) -> list[str]:
    """Rewrite, in place, every text colour that falls under the ratio on its
    resolved background. Returns one line per fix. `palette` maps token ids
    (without the leading dashes) to their values."""
    fixes: list[str] = []
    # //// Neoffice — a card's surface as the theme draws it: the chrome's --surface-color IS the
    # //// site's background colour, so a card is dark on a dark site. Judged against white, an
    # //// address in dark ink on a dark card passed on a reseller site's contact page (2026-09-13).
    palette = dict(palette)
    palette.setdefault("surface", next((v for k, v in palette.items() if k.endswith("-background")), "") or "#ffffff")
    default_bg = next((parse_color(v, palette) for k, v in palette.items() if k.endswith("-background")), None) or NAMED["white"]
    default_fg = next((parse_color(v, palette) for k, v in palette.items() if k.endswith("-text")), None) or (26.0, 26.0, 26.0, 1.0)
    for block in blocks or []:
        _walk(block, default_bg, default_fg, palette, minimum, fixes)
    return fixes


def _walk(block: dict, bg: Color | None, fg: Color | None, palette: dict[str, str], minimum: float, fixes: list[str]) -> None:
    styles = block.get("baseStyles") or {}
    # //// Neoffice — lettering filled with a photograph (a transparent text colour over a background
    # //// clipped to the letters) reads only where the picture is light behind every letter: the
    # //// brand tiles of a black site showed a name in near-black on black (2026-09-14). The letters
    # //// take the ink their band reads in, and the picture stays in its tile.
    if _photo_lettering(styles):
        for key in LETTERING_KEYS:
            styles.pop(key, None)
        ink = best_text(bg, palette, minimum)[0] if bg is not None else "#ffffff"
        styles["color"] = ink
        block["baseStyles"] = styles
        fixes.append(f"{block.get('blockName') or block.get('element') or 'block'}: photo lettering -> {ink}")
    if any(c.startswith("u-over-image") for c in _classes(block)):
        # copy laid over a photo: the photo decides, not a flat colour
        bg = None
    raw_bg = styles.get("backgroundColor") or styles.get("background")
    if not raw_bg and any(c == "u-card" or c.startswith("u-card--") for c in _classes(block)):
        # //// Neoffice — added branch (e1e04aa0 "fix(contrast): a card wears the chrome's
        # //// surface, and frappe pages read on a dark site"): a u-card with no background of
        # //// its own still needs a surface colour to judge its text against.
        # a card wears the chrome's surface, not the section behind it: the trust cards of a
        # reseller site's dark home kept the site's light text on their white face (2026-09-09).
        # That surface is the site's background colour unless the palette names one (see
        # repair_contrast): white on a light site, dark on a dark one.
        raw_bg = palette.get("surface") or "#ffffff"
    if raw_bg:
        parsed = parse_color(raw_bg, palette)
        if parsed is None:
            bg = None  # an image or a gradient: nothing below can be judged
        elif parsed[3] >= 1.0:
            bg = parsed
        else:
            bg = composite(parsed, bg) if bg is not None else None
    if styles.get("backgroundImage"):
        bg = None
    children = block.get("children") or []
    if any(_covers_parent(child) for child in children):
        # a section built as photo + overlay + copy: the copy reads on the photo
        bg = None
    if "color" in styles:
        fg = parse_color(styles.get("color"), palette)
    if bg is not None and fg is not None and _has_text(block):
        seen = composite(fg, bg) if fg[3] < 1.0 else fg
        ratio = contrast(seen, bg)
        if ratio < minimum:
            replacement, value = best_text(bg, palette, minimum)
            raw_fg = (styles.get("color") or "").strip()
            m = VAR.match(raw_fg)
            if m and ratio >= 2.0 and m.group(1) in palette and m.group(1).endswith(("-primary", "-secondary")):
                # a brand accent on a kicker or a label: deepen it, do not flatten it
                shade = accent_shade(raw_fg, fg, bg, minimum)
                if shade:
                    replacement, value = shade
            styles["color"] = replacement
            block["baseStyles"] = styles
            fg = value
            fixes.append(f"{block.get('blockName') or block.get('element') or 'block'}: {ratio:.1f}:1 -> {replacement}")
    for child in children:
        _walk(child, bg, fg, palette, minimum, fixes)


# //// Neoffice — see _walk: the keys that paint letters with a picture
LETTERING_KEYS = (
    "background", "backgroundImage", "backgroundClip", "WebkitBackgroundClip", "webkitBackgroundClip",
    "WebkitTextFillColor", "webkitTextFillColor", "backgroundSize", "backgroundPosition", "backgroundRepeat",
)
TRANSPARENT = re.compile(r"^(?:transparent|rgba\([^)]*,\s*0(?:\.0+)?\s*\))$", re.I)


def _photo_lettering(styles: dict) -> bool:
    """Letters painted with a picture: a transparent text colour over a background clipped to the text."""
    color = str(styles.get("color") or "").strip()
    fill = str(styles.get("WebkitTextFillColor") or styles.get("webkitTextFillColor") or "").strip()
    if not (TRANSPARENT.match(color) or TRANSPARENT.match(fill)):
        return False
    clip = " ".join(str(styles.get(k) or "") for k in ("backgroundClip", "WebkitBackgroundClip", "webkitBackgroundClip")).lower()
    return "text" in clip or "url(" in f"{styles.get('background') or ''}{styles.get('backgroundImage') or ''}"


# //// Neoffice — a layer laid over a photograph is a veil, never a wall (2026-09-14): a contact page
# //// covered its photograph with an opaque black layer, and the section showed a black rectangle where
# //// the client's picture was. The layer keeps its hue and becomes a gradient scrim.
SCRIM_TOP, SCRIM_BOTTOM = 0.12, 0.62
ZERO = ("0", "0px", "0%")


def _shows_picture(block: dict) -> bool:
    styles = block.get("baseStyles") or {}
    if str(block.get("element") or "").lower() == "img" or styles.get("objectFit"):
        return True
    return "url(" in f"{styles.get('backgroundImage') or ''}{styles.get('background') or ''}"


def _spans_parent(styles: dict) -> bool:
    if str(styles.get("inset") or "").strip() in ZERO:
        return True
    offsets = [str(styles.get(k) or "").strip() for k in ("top", "right", "bottom", "left")]
    if all(o in ZERO for o in offsets):
        return True
    return offsets[0] in ZERO and offsets[3] in ZERO and str(styles.get("width") or "") == "100%" and str(styles.get("height") or "") == "100%"


def repair_opaque_overlays(blocks: list[dict], palette: dict[str, str]) -> list[str]:
    """Turns an opaque, text-free layer spread over a photograph into a gradient scrim of its own
    hue. A layer with a blend mode is a deliberate effect and is left alone. Returns one line per fix."""
    fixes: list[str] = []

    def walk(block) -> None:
        if not isinstance(block, dict):
            return
        children = [c for c in block.get("children") or [] if isinstance(c, dict)]
        if _shows_picture(block) or any(_shows_picture(c) for c in children):
            for child in children:
                styles = child.get("baseStyles") or {}
                if styles.get("position") != "absolute" or styles.get("mixBlendMode") or not _spans_parent(styles):
                    continue
                if _shows_picture(child) or _has_text(child):
                    continue
                raw = styles.get("backgroundColor") or styles.get("background")
                color = parse_color(raw, palette) if raw else None
                try:
                    opacity = float(styles.get("opacity") or 1)
                except (TypeError, ValueError):
                    opacity = 1.0
                if color is None or color[3] * opacity < 0.9:
                    continue
                r, g, b = (round(v) for v in color[:3])
                styles.pop("backgroundColor", None)
                styles["background"] = f"linear-gradient(to top, rgba({r},{g},{b},{SCRIM_BOTTOM}), rgba({r},{g},{b},{SCRIM_TOP}))"
                child["baseStyles"] = styles
                fixes.append(f"{child.get('blockName') or 'overlay'}: opaque layer over a photo -> scrim")
        for child in children:
            walk(child)

    for block in blocks or []:
        walk(block)
    return fixes


# //// Neoffice — copy laid on a photograph gets the design system's scrim (2026-09-14): the photo cards of
# //// a black-and-white site put white titles straight on light street photographs, with no veil, and two
# //// of five read as nothing. The card takes u-over-image (--bottom: its copy sits low), whose ::after
# //// scrim sits between the picture and the copy (theme_variables.html).
VEILED = ("u-over-image",)


def _covering_picture(block: dict) -> bool:
    styles = block.get("baseStyles") or {}
    return _shows_picture(block) and styles.get("position") == "absolute" and (_spans_parent(styles) or bool(styles.get("objectFit")))


def _has_covering_picture(block: dict, depth: int = 0) -> bool:
    """Whether the block, or a descendant, lays a picture across it: a scrim makes sense over that."""
    if depth > 8 or not isinstance(block, dict):
        return False
    if _shows_picture(block):
        return True
    return any(_covering_picture(c) or _has_covering_picture(c, depth + 1) for c in block.get("children") or [] if isinstance(c, dict))


def _veil(block: dict) -> bool:
    """An absolute layer with a translucent or gradient fill: a scrim the model drew itself."""
    styles = block.get("baseStyles") or {}
    if styles.get("position") != "absolute" or _has_text(block) or _shows_picture(block):
        return False
    raw = str(styles.get("background") or styles.get("backgroundColor") or "")
    return "gradient" in raw or ("rgba(" in raw and not raw.strip().endswith(", 1)"))


def veil_copy_on_photos(blocks: list[dict]) -> list[str]:
    """Gives u-over-image u-over-image--bottom to a block that lays a picture across itself and
    copy over it without any scrim. Returns one line per block."""
    fixes: list[str] = []

    def walk(block) -> None:
        if not isinstance(block, dict):
            return
        children = [c for c in block.get("children") or [] if isinstance(c, dict)]
        classes = _classes(block)
        # //// Neoffice — a tile painting its picture as its OWN background counts too (2026-09-18):
        # //// a home's category tiles carried their captions straight on bright photographs
        # //// ("SNOWBOARD" white on a pale sky, 1.6:1 measured), with no scrim, because the
        # //// picture was the tile's backgroundImage and not a child.
        pictured = any(_covering_picture(c) for c in children) or (_shows_picture(block) and str(block.get("element") or "").lower() != "img")
        if (
            not any(c.startswith(VEILED) for c in classes)
            and pictured
            and any(_has_text(c) and not _covering_picture(c) for c in children)
            and not any(_veil(c) for c in children)
        ):
            block["classes"] = [*classes, "u-over-image", "u-over-image--bottom"]
            fixes.append(f"{block.get('blockName') or block.get('element') or 'block'}: copy on a photo gets the scrim")
        for child in children:
            walk(child)

    for block in blocks or []:
        walk(block)
    return fixes



# //// Neoffice ▼▼▼ — added (2026-09-15): copy inside a scrim reads on the scrim.
SCRIM_INK = "#ffffff"
SCRIM_MIN_RATIO = 3.0


def read_over_photos(blocks: list[dict], palette: dict[str, str]) -> list[str]:
    """Inside a section carrying the design system's scrim, copy reads on the scrim.

    The scrim darkens the picture so white copy reads over it (veil_copy_on_photos). A hero
    whose heading was written white therefore read, while its "Shop now" link, which declared no
    colour at all, inherited the page's near-black ink and was invisible on the photograph under
    it (2026-09-15). repair_contrast could not see either of them: a section wearing a photograph
    has no background colour to judge against, its picture being an absolutely-positioned child.

    So the SECTION is given the reading ink, and everything in it inherits — except a block that
    paints its own opaque background, which is a card sitting on the picture: that one is given a
    colour that reads on its own fill instead, and is not walked into. A block that declares a
    colour of its own keeps it when it reads on the scrim, and takes the ink when it does not.
    Returns one line per repair."""
    # the scrim is a dark wash: judged against black, which is what the copy sits on at its worst
    scrim = (0.0, 0.0, 0.0, 1.0)
    fixes: list[str] = []

    def label(block: dict) -> str:
        text = re.sub(r"<[^>]+>", " ", str(block.get("innerHTML") or ""))
        return " ".join(text.split())[:40] or (block.get("element") or "block")

    def own_background(block: dict) -> Color | None:
        styles = block.get("baseStyles") or {}
        raw = str(styles.get("backgroundColor") or styles.get("background") or "")
        if not raw or raw.strip().lower() in ("transparent", "none", "inherit") or "gradient" in raw:
            return None
        colour = parse_color(raw, palette)
        return colour if colour is not None and (len(colour) < 4 or colour[3] >= 0.9) else None

    def set_ink(block: dict, value: str, why: str) -> None:
        styles = block.get("baseStyles") or {}
        if str(styles.get("color") or "") == value:
            return
        styles["color"] = value
        block["baseStyles"] = styles
        fixes.append(f"'{label(block)}': {why} -> {value}")

    def repair(block: dict) -> None:
        if _covering_picture(block) or _veil(block):
            return
        background = own_background(block)
        if background is not None:
            # a card sitting on the picture: it reads on its own fill, not on the scrim
            if not (block.get("baseStyles") or {}).get("color"):
                handle, _colour = best_text(background, palette)
                set_ink(block, handle, "a card on a photograph takes a colour that reads on itself")
            return
        colour = parse_color((block.get("baseStyles") or {}).get("color"), palette)
        if colour is not None and contrast(colour, scrim) < SCRIM_MIN_RATIO:
            set_ink(block, SCRIM_INK, "dark copy on a scrim")
        for child in block.get("children") or []:
            if isinstance(child, dict):
                repair(child)

    def unveil(block: dict) -> None:
        # //// Neoffice — a veil with no picture under it is no veil (2026-09-17): a brands page
        # //// carried u-over-image on a section that showed no photograph, so this very rule
        # //// painted its heading white on the page's light ground, at write time and again at
        # //// every render — and the measured repair could never win against it. The classes go,
        # //// and the white ink they earned goes with them.
        block["classes"] = [c for c in _classes(block) if not c.startswith(VEILED[0])]
        fixes.append(f"'{label(block)}': a veil with no picture under it is removed")

        def clear(node: dict) -> None:
            styles = node.get("baseStyles") or {}
            if str(styles.get("color") or "").strip().lower() in (SCRIM_INK, "#fff", "white"):
                styles.pop("color", None)
                node["baseStyles"] = styles
            for child in node.get("children") or []:
                if isinstance(child, dict) and not own_background(child):
                    clear(child)

        clear(block)

    def walk(block) -> None:
        if not isinstance(block, dict):
            return
        if any(c.startswith(VEILED[0]) for c in _classes(block)):
            if not _has_covering_picture(block):
                unveil(block)
                for child in block.get("children") or []:
                    walk(child)
                return
            colour = parse_color((block.get("baseStyles") or {}).get("color"), palette)
            if colour is None or contrast(colour, scrim) < SCRIM_MIN_RATIO:
                set_ink(block, SCRIM_INK, "copy inside a scrim inherits the page's ink")
            for child in block.get("children") or []:
                if isinstance(child, dict):
                    repair(child)
            return
        for child in block.get("children") or []:
            walk(child)

    for block in blocks or []:
        walk(block)
    return fixes


def scrim_ink_for_render(blocks):
	"""The blocks a page renders, with dark copy inside a scrim given the reading ink.

	//// Neoffice — added 2026-09-15, the render half of read_over_photos. The build repairs a
	page as it writes it, but a page written before the rule — or edited by hand since — keeps a
	black "Shop now" on a photograph for ever. `blocks` as stored (JSON text) or parsed; returned
	untouched when nothing changes, and on any error: this runs on every page view and must never
	be the reason a page fails."""
	if not blocks or (isinstance(blocks, str) and "u-over-image" not in blocks):
		return blocks
	import frappe

	try:
		from builder.site_ai.nora.buttons import _render_palette

		palette = _render_palette() or {}
		data = frappe.parse_json(blocks) if isinstance(blocks, str) else copy.deepcopy(blocks)
		listed = data if isinstance(data, list) else [data]
		return data if read_over_photos(listed, palette) else blocks
	except Exception:
		frappe.log_error("Contrast: page rendered without the scrim check", frappe.get_traceback())
		return blocks


# //// Neoffice ▼▼▼ — what the browser measured is repaired here, not sent back to the writer
# //// (2026-09-17). On a brands page the writer fixed a washed-out heading and lost the button
# //// under it, then fixed the button and lost the heading: two model calls for a colour the
# //// gate had already measured. A measured contrast finding names the element and the ground
# //// it sits on; the block is found by its text and given an ink that reads on that ground.
MEASURED_GROUND = re.compile(r"background rgb\((\d+),\s*(\d+),\s*(\d+)\)")
MEASURED_WHERE = re.compile(r'^\s*([a-z0-9]+)\s+"(.+)"\s*$', re.S)


def _plain_text(block: dict) -> str:
    html = block.get("innerHTML")
    if not isinstance(html, str) or "<svg" in html:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip().lower()


def repair_measured_contrast(blocks: list[dict], findings: list[dict], palette: dict[str, str], minimum: float = MIN_RATIO) -> list[str]:
    """Give every block the gate measured unreadable an ink that reads on the ground it was
    measured on. `findings` are the gate's (kind, where, detail); the block is found by the
    text the probe quoted. Returns one line per edit."""
    fixes: list[str] = []
    targets = []
    for finding in findings or []:
        if finding.get("kind") != "unreadable-text":
            continue
        ground = MEASURED_GROUND.search(finding.get("detail") or "")
        named = MEASURED_WHERE.match(finding.get("where") or "")
        if not ground or not named:
            continue
        bg = (float(ground.group(1)), float(ground.group(2)), float(ground.group(3)), 1.0)
        targets.append((named.group(1).lower(), re.sub(r"\s+", " ", named.group(2)).strip().lower(), bg))
    if not targets:
        return fixes

    INLINE_STYLE = re.compile(r'(<(?P<tag>[a-z][a-z0-9]*)\b[^>]*\bstyle="[^"]*?)color\s*:\s*[^;"]+', re.I)

    def recolour_inline(block: dict, tag: str, wanted: str, ink: str) -> bool:
        """//// Neoffice — a colour written INLINE in the block's html (2026-09-18): the writer
        styled <a href="tel:…" style="color:#E85D2B"> by hand, and no block colour can reach
        an inline style. The colour is rewritten in the html, on the tag that carries the text."""
        html = block.get("innerHTML")
        if not isinstance(html, str) or "style=" not in html:
            return False
        changed = False

        def swap(m):
            nonlocal changed
            if m.group("tag").lower() != tag:
                return m.group(0)
            changed = True
            return f"{m.group(1)}color: {ink}"

        new_html = INLINE_STYLE.sub(swap, html)
        if changed:
            block["innerHTML"] = new_html
        return changed

    def walk(block: dict, depth: int = 0) -> None:
        if depth > 24 or not isinstance(block, dict):
            return
        text = _plain_text(block)
        if text:
            for tag, wanted, bg in targets:
                # an inline-styled element inside this block's html carries the text
                if wanted[:60] in text and not text.startswith(wanted[:60]):
                    handle, ink = best_text(bg, palette, minimum)
                    if recolour_inline(block, tag, wanted, handle):
                        fixes.append(f"{tag} '{wanted[:40]}' (inline style) given {handle} on rgb({int(bg[0])}, {int(bg[1])}, {int(bg[2])})")
                    continue
                # //// the probe names the element it measured (a span inside a p): the block that
                # //// carries that text is the one to colour, whatever its tag — a kicker written as
                # //// <p><span>ACTUALITÉS</span></p> was never found by tag (2026-09-17)
                if not text.startswith(wanted[:60]) or (block.get("children") and len(text) > len(wanted) + 40):
                    continue
                styles = block.setdefault("baseStyles", {})
                current = parse_color(styles.get("color"), palette)
                if current and contrast(composite(current, bg), bg) >= minimum:
                    continue
                handle, ink = best_text(bg, palette, minimum)
                styles["color"] = handle
                fixes.append(f"{tag} '{wanted[:40]}' given {handle} on rgb({int(bg[0])}, {int(bg[1])}, {int(bg[2])})")
        for child in block.get("children") or []:
            walk(child, depth + 1)

    for block in blocks:
        walk(block)
    return fixes
# //// Neoffice ▲▲▲

