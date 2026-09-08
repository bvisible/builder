"""Font sizes a page can live with.

Given a "big display type" direction the model reaches for viewport units without a
clamp: on the B2C regeneration (2026-09-08) paragraphs at 11vw and headings at 12vw,
which is a 210 px paragraph on a 1920 px screen and a 140 px one in the editor. The
brief now forbids bare vw, and this pass caps whatever still comes through: a vw size
becomes clamp(minimum, Xvw, cap) and any fixed size above the cap is lowered to it.

Pure functions over the block tree."""

import re

STYLE_KEYS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
# desktop caps in rem by element; anything else (a display number in a span, a div) gets the generic one
DESKTOP_CAP = {"h1": 4.5, "h2": 3.25, "h3": 2.25, "h4": 1.75, "h5": 1.5, "h6": 1.25, "p": 1.35, "li": 1.35, "a": 1.35, "small": 1, "generic": 4.5}
MOBILE_CAP = {"h1": 2.75, "h2": 2.25, "h3": 1.75, "h4": 1.5, "h5": 1.25, "h6": 1.125, "p": 1.125, "li": 1.125, "a": 1.125, "small": 0.875, "generic": 2.75}
MIN_REM = {"h1": 2, "h2": 1.5, "h3": 1.25, "generic": 1}
ROOT_PX = 16
SIZE = re.compile(r"^\s*([\d.]+)\s*(rem|em|px|vw)\s*$", re.I)


def _cap(element: str, mobile: bool) -> float:
    table = MOBILE_CAP if mobile else DESKTOP_CAP
    return table.get((element or "").lower(), table["generic"])


def _walk(blocks: list):
    stack = list(blocks or [])
    while stack:
        block = stack.pop()
        if not isinstance(block, dict):
            continue
        yield block
        stack.extend(block.get("children") or [])


def capped_font_size(value: str, element: str, mobile: bool = False) -> str | None:
    """The font size to write instead of `value`, or None when it can stay."""
    m = SIZE.match(str(value or ""))
    if not m:
        return None
    number, unit = float(m.group(1)), m.group(2).lower()
    cap = _cap(element, mobile)
    if unit == "vw":
        low = MIN_REM.get((element or "").lower(), MIN_REM["generic"])
        low = min(low, cap)
        return f"clamp({low:g}rem, {number:g}vw, {cap:g}rem)"
    rem = number / ROOT_PX if unit == "px" else number
    if rem > cap:
        return f"{cap:g}rem"
    return None


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
