# //// Neoffice — added file (no upstream equivalent): photo slots when no picture will come.
# //// builder/site_ai/** = the Neoffice AI site generator.
"""Photo slots without photos.

The brief hands the model placeholder URLs (placehold.co) for the photos the image job
fills afterwards. With no image backend the slots stayed on those URLs: grey boxes with
a caption, fetched from a third party by every visitor. Image generation was switched
off on 2026-09-09 (the pictures were not good enough): each slot becomes a plain block
in the site's own colours, drawn as an inline SVG, so the page needs nothing from
outside and looks composed rather than unfinished.

Pure functions over the block tree."""

import re
from urllib.parse import quote

from builder.site_ai.nora.layout import _walk

PLACEHOLD = re.compile(r"https?://placehold\.co/(\d+)x(\d+)[^\s'\")]*")


def neutral_image(width: int, height: int, palette: dict, prefix: str) -> str:
    """An inline SVG: the site's background with a wash of its secondary colour."""
    base = (palette or {}).get(f"{prefix}-background") or "#f3f1ec"
    wash = (palette or {}).get(f"{prefix}-secondary") or (palette or {}).get(f"{prefix}-primary") or "#c8c2b8"
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<rect width='100%' height='100%' fill='{base}'/>"
        f"<rect width='100%' height='100%' fill='{wash}' fill-opacity='0.35'/>"
        "</svg>"
    )
    return "data:image/svg+xml;utf8," + quote(svg, safe="/:='<> ,.")


def _replace(text: str, palette: dict, prefix: str) -> str:
    def swap(m):
        return neutral_image(int(m.group(1)), int(m.group(2)), palette, prefix)

    return PLACEHOLD.sub(swap, text)


def neutral_placeholders(blocks: list, palette: dict, prefix: str) -> int:
    """Every placehold.co URL in an image source, a background or a text becomes an
    inline neutral block. Returns the number of blocks changed."""
    edits = 0
    for block in _walk(blocks):
        changed = False
        attrs = block.get("attributes") or {}
        for key in ("src", "data-src", "srcset"):
            value = attrs.get(key)
            if isinstance(value, str) and "placehold.co" in value:
                attrs[key] = _replace(value, palette, prefix)
                changed = True
        for style_key in ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles"):
            styles = block.get(style_key) or {}
            for prop in ("backgroundImage", "background"):
                value = styles.get(prop)
                if isinstance(value, str) and "placehold.co" in value:
                    styles[prop] = _replace(value, palette, prefix)
                    changed = True
        html = block.get("innerHTML")
        if isinstance(html, str) and "placehold.co" in html:
            block["innerHTML"] = _replace(html, palette, prefix)
            changed = True
        if changed:
            edits += 1
    return edits
