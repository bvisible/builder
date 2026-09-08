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
    default_bg = next((parse_color(v, palette) for k, v in palette.items() if k.endswith("-background")), None) or NAMED["white"]
    default_fg = next((parse_color(v, palette) for k, v in palette.items() if k.endswith("-text")), None) or (26.0, 26.0, 26.0, 1.0)
    for block in blocks or []:
        _walk(block, default_bg, default_fg, palette, minimum, fixes)
    return fixes


def _walk(block: dict, bg: Color | None, fg: Color | None, palette: dict[str, str], minimum: float, fixes: list[str]) -> None:
    styles = block.get("baseStyles") or {}
    if any(c.startswith("u-over-image") for c in _classes(block)):
        # copy laid over a photo: the photo decides, not a flat colour
        bg = None
    raw_bg = styles.get("backgroundColor") or styles.get("background")
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
