"""Font sizes a page can live with.

Given a "big display type" direction the model reaches for viewport units without a
clamp: on the B2C regeneration (2026-09-08) paragraphs at 11vw and headings at 12vw,
which is a 210 px paragraph on a 1920 px screen and a 140 px one in the editor. The
brief now forbids bare vw, and this pass caps whatever still comes through: a vw size
becomes clamp(minimum, Xvw, cap) and any fixed size above the cap is lowered to it.

Pure functions over the block tree."""

import re

STYLE_KEYS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
HEADING_CAP = {"h1": 4.5, "h2": 3.25, "h3": 2.25, "h4": 1.75, "h5": 1.5, "h6": 1.25}
HEADING_CAP_MOBILE = {"h1": 2.75, "h2": 2.25, "h3": 1.75, "h4": 1.5, "h5": 1.25, "h6": 1.125}
HEADING_MIN = {"h1": 2, "h2": 1.5, "h3": 1.25}
# a p, span or div is display type when its viewport size is large (the brand name of a
# hero at 11vw) and running text when it is small (a 3vw paragraph): the cap follows
DISPLAY_VW = 4
DISPLAY_CAP, DISPLAY_CAP_MOBILE = 4.5, 2.75
TEXT_CAP, TEXT_CAP_MOBILE = 1.5, 1.125
FIXED_CAP, FIXED_CAP_MOBILE = 6, 3.5
ROOT_PX = 16
SIZE = re.compile(r"^\s*([\d.]+)\s*(rem|em|px|vw)\s*$", re.I)
OUR_CLAMP = re.compile(r"^clamp\(([\d.]+)rem,\s*([\d.]+)vw,\s*([\d.]+)rem\)$")


def _walk(blocks: list):
    stack = list(blocks or [])
    while stack:
        block = stack.pop()
        if not isinstance(block, dict):
            continue
        yield block
        stack.extend(block.get("children") or [])


def capped_font_size(value: str, element: str, mobile: bool = False) -> str | None:
    """The font size to write instead of `value`, or None when it can stay. A clamp this
    module wrote earlier is re-derived from its vw part, so the rule can be re-applied."""
    text = str(value or "").strip()
    again = OUR_CLAMP.match(text)
    if again:
        text = f"{again.group(2)}vw"
    m = SIZE.match(text)
    if not m:
        return None
    number, unit = float(m.group(1)), m.group(2).lower()
    tag = (element or "").lower()
    heading = tag in HEADING_CAP
    if unit == "vw":
        if heading:
            cap = (HEADING_CAP_MOBILE if mobile else HEADING_CAP)[tag]
            low = min(HEADING_MIN.get(tag, 1), cap)
        elif number >= DISPLAY_VW:
            cap, low = (DISPLAY_CAP_MOBILE if mobile else DISPLAY_CAP), (1.5 if mobile else 2)
        else:
            cap, low = (TEXT_CAP_MOBILE if mobile else TEXT_CAP), 1
        out = f"clamp({low:g}rem, {number:g}vw, {cap:g}rem)"
        return None if out == str(value or "").strip() else out
    rem = number / ROOT_PX if unit == "px" else number
    if heading:
        cap = (HEADING_CAP_MOBILE if mobile else HEADING_CAP)[tag]
    else:
        cap = FIXED_CAP_MOBILE if mobile else FIXED_CAP
    return f"{cap:g}rem" if rem > cap else None


def cap_font_sizes(blocks: list) -> int:
    """Rewrite every oversized or viewport-relative fontSize in place. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        element = block.get("element") or ""
        for key in STYLE_KEYS:
            styles = block.get(key)
            if not styles or "fontSize" not in styles:
                continue
            new = capped_font_size(styles.get("fontSize"), element, mobile=(key == "mobileStyles"))
            if new and new != styles.get("fontSize"):
                styles["fontSize"] = new
                edits += 1
    return edits
