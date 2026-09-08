"""The site's signature accent as a token.

The design brief invites "an unexpected accent colour" and the model obliges with a raw
hex on every page, a slightly different one each time (#f59e0b, #f2a900, #e89b26 and
#f5a623 on the four pages of the B2B regeneration, 2026-09-08): outside the design
system, so a retheme never reaches it, and inconsistent across the site. The dominant
foreign colour of the first page becomes the <prefix>-accent token; the foreign accent
of every later page is rewritten to that same token, and the brief of those pages hands
the model the handle so it stops inventing one.

Pure functions over the block tree; the token itself is minted by site_builder."""

import re
from collections import Counter

STYLE_KEYS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles")
HEX = re.compile(r"#([0-9a-fA-F]{6})(?![0-9a-fA-F])")
MIN_USES = 3
MIN_SATURATION = 0.25


def _saturation(hex6: str) -> float:
    r, g, b = (int(hex6[i : i + 2], 16) / 255 for i in (0, 2, 4))
    high, low = max(r, g, b), min(r, g, b)
    return 0.0 if high == 0 else (high - low) / high


def _walk(blocks: list):
    stack = list(blocks or [])
    while stack:
        block = stack.pop()
        if not isinstance(block, dict):
            continue
        yield block
        stack.extend(block.get("children") or [])


def foreign_colours(blocks: list, palette: dict[str, str]) -> Counter:
    """Every saturated 6-digit hex used in the styles that is not a palette value.
    Neutrals (white, black, greys) are the page's own business, not an accent."""
    known = {str(v).lower() for v in (palette or {}).values() if str(v).startswith("#")}
    found: Counter = Counter()
    for block in _walk(blocks):
        for key in STYLE_KEYS:
            for value in (block.get(key) or {}).values():
                for hex6 in HEX.findall(str(value)):
                    colour = "#" + hex6.lower()
                    if colour in known or _saturation(hex6) < MIN_SATURATION:
                        continue
                    found[colour] += 1
    return found


def dominant_accent(blocks: list, palette: dict[str, str]) -> str | None:
    """The foreign colour the page leans on, or None when it has no accent of its own."""
    counts = foreign_colours(blocks, palette)
    if not counts:
        return None
    colour, uses = counts.most_common(1)[0]
    return colour if uses >= MIN_USES else None


def rewrite_hex(blocks: list, mapping: dict[str, str]) -> int:
    """Replace the given 6-digit hexes (case-insensitive, 8-digit alpha forms untouched)
    inside every style value, gradients and shadows included. Returns the edit count."""
    if not mapping:
        return 0
    lookup = {k.lower(): v for k, v in mapping.items()}
    pattern = re.compile("|".join(re.escape(k) for k in lookup) + r"(?![0-9a-fA-F])", re.I)
    edits = 0
    for block in _walk(blocks):
        for key in STYLE_KEYS:
            styles = block.get(key)
            if not styles:
                continue
            for prop, value in list(styles.items()):
                if not isinstance(value, str) or "#" not in value:
                    continue
                new = pattern.sub(lambda m: lookup[m.group(0).lower()], value)
                if new != value:
                    styles[prop] = new
                    edits += 1
    return edits
