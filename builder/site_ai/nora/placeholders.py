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

import copy
import re
from urllib.parse import quote, unquote_plus

from builder.site_ai.nora.layout import _walk

PLACEHOLD = re.compile(r"https?://placehold\.co/(\d+)x(\d+)[^\s'\")]*")
TEXT_PARAM = re.compile(r"[?&]text=([^&'\")\s]+)")

# a slot a generated picture would make a false statement in: a stranger's face is taken for the
# person the page names, and a map, a sign or a document comes drawn with made-up streets and
# lettering (the access map of a contact page showed an invented street address, 2026-09-13)
PORTRAIT = re.compile(r"\b(?:portrait|porträt|ritratto|headshot)s?\b", re.I)
DOCUMENT = re.compile(
    r"\b(?:maps?|carte|plans?|itinéraire|itinerary|directions|karte|lageplan|signs?|signage|enseigne|panneau|schild"
    r"|logos?|brochure|flyer|menu|document|certificat|certificate|diplôme|diploma|screen|écran|bildschirm)\b",
    re.I,
)
PERSON = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ'’]+(?:[ -][A-ZÀ-Ý][a-zà-ÿ'’]+){1,2}\b")


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
    # the quotes of the SVG's attributes are encoded: a slot written as a CSS background sits
    # inside url('…'), which a bare quote would close
    return "data:image/svg+xml;utf8," + quote(svg, safe="/:=<> ,.")


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


def neutral_for_render(blocks):
    """The blocks a page renders, each placehold.co slot drawn as the plain block of
    neutral_placeholders, in the colours of this render. A page written before the slots were
    neutralised at the build (2026-09-09) kept them, and a slot waits for its picture while the
    image job draws it: a test site's home showed "Cave daffinage" in grey capitals across its
    hero, fetched from a third party by every visitor (2026-09-13). The stored page keeps its
    slots, for the image job to find. `blocks` as stored (JSON text) or parsed; returned
    untouched when there is no slot, and on any error: this runs on every page view."""
    if not blocks or (isinstance(blocks, str) and "placehold.co" not in blocks):
        return blocks
    import frappe

    try:
        from builder.site_ai.nora.buttons import _render_palette

        palette = _render_palette() or {}
        colours = {
            "render-background": palette.get("background") or "#f3f1ec",
            "render-secondary": palette.get("secondary") or palette.get("primary") or "#c8c2b8",
        }
        data = frappe.parse_json(blocks) if isinstance(blocks, str) else copy.deepcopy(blocks)
        return data if neutral_placeholders(data if isinstance(data, list) else [data], colours, "render") else blocks
    except Exception:
        frappe.log_error("Placeholders: page rendered with its placeholders", frappe.get_traceback())
        return blocks


def _names_a_person(text: str, names: set[str]) -> bool:
    """Whether the text names someone: two or three capitalised words in a row that are not one of
    `names` (the site's own name, its categories). A Title Case text says nothing either way."""
    words = re.findall(r"[^\W\d_]{4,}", text)
    if words and all(word[0].isupper() for word in words):
        return False
    return any(match.group(0).lower() not in names for match in PERSON.finditer(text))


def must_not_be_drawn(text: str, names: set[str] | frozenset = frozenset()) -> bool:
    """A picture of this would state something false: a portrait, a named person, a map, a sign or
    a document."""
    return bool(PORTRAIT.search(text) or DOCUMENT.search(text) or _names_a_person(text, names))


def neutral_named_slots(blocks: list, palette: dict, prefix: str, names=()) -> list[str]:
    """The photo slots the image job must not fill become the plain block a site without image
    generation gets (must_not_be_drawn: read from an image's alt, or from the text of a background
    placeholder). `names` are the proper names that are not people: the site's own, its
    categories. Returns the texts of the slots changed."""
    known = {str(name).strip().lower() for name in names or () if str(name).strip()}
    edits: list[str] = []
    for block in _walk(blocks):
        attrs = block.get("attributes") or {}
        src = attrs.get("src")
        if isinstance(src, str) and "placehold.co" in src:
            alt = str(attrs.get("alt") or "")
            if must_not_be_drawn(alt, known):
                attrs["src"] = _replace(src, palette, prefix)
                edits.append(alt[:60])
        for style_key in ("baseStyles", "mobileStyles", "tabletStyles"):
            styles = block.get(style_key) or {}
            for prop in ("backgroundImage", "background"):
                value = styles.get(prop)
                if not (isinstance(value, str) and "placehold.co" in value):
                    continue
                param = TEXT_PARAM.search(value)
                text = unquote_plus(param.group(1)) if param else ""
                if must_not_be_drawn(text, known):
                    styles[prop] = _replace(value, palette, prefix)
                    edits.append(text[:60])
    return edits
