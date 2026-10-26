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
import json
import re
from urllib.parse import quote, unquote, unquote_plus

from builder.site_ai.nora.layout import _is_card, _walk

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


def neutral_image(width: int, height: int, palette: dict, prefix: str, colour: str | None = None) -> str:
    """An inline SVG: the colour the placeholder asked for when it names one of its own (the page
    was composed around it: a dark hero under light text), else the site's background with a
    wash of its secondary colour."""
    base = colour or (palette or {}).get(f"{prefix}-background") or "#f3f1ec"
    wash = None if colour else ((palette or {}).get(f"{prefix}-secondary") or (palette or {}).get(f"{prefix}-primary") or "#c8c2b8")
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<rect width='100%' height='100%' fill='{base}'/>"
        + (f"<rect width='100%' height='100%' fill='{wash}' fill-opacity='0.35'/>" if wash else "")
        + "</svg>"
    )
    # the quotes of the SVG's attributes are encoded: a slot written as a CSS background sits
    # inside url('…'), which a bare quote would close
    return "data:image/svg+xml;utf8," + quote(svg, safe="/:=<> ,.")


# //// Neoffice — added (2026-10-19, neoffice-maintenance #1723): a block drawn by neutral_image read
# //// back from its data URI. Copy written for a photograph sits on this block once no photograph
# //// comes, and contrast.py has to know what colour it lands on (and redraw the block when it is light).
NEUTRAL_URI = re.compile(r"data:image/svg\+xml;utf8,([^'\")]*)")
NEUTRAL_SIZE = re.compile(r"<svg [^>]*\bwidth='(\d+)' height='(\d+)'")
NEUTRAL_RECT = re.compile(r"<rect width='100%' height='100%' fill='([^']+)'(?: fill-opacity='([\d.]+)')?/>")


def neutral_paint(value: str) -> tuple[int, int, str, str | None, float] | None:
    """What a block drawn by neutral_image paints, read back from its data URI (an image src, or a CSS
    url()): (width, height, base fill, wash fill or None, wash opacity). None when `value` holds no
    such block: a photograph, a logo, any other data URI."""
    found = NEUTRAL_URI.search(value or "")
    if not found:
        return None
    svg = unquote(found.group(1))
    size, rects = NEUTRAL_SIZE.search(svg), NEUTRAL_RECT.findall(svg)
    if not size or not rects or len(rects) > 2:
        return None
    wash = rects[1] if len(rects) == 2 else None
    return int(size.group(1)), int(size.group(2)), rects[0][0], wash[0] if wash else None, float(wash[1] or 1) if wash else 0.0


# //// Neoffice — added (2026-10-19, neoffice-maintenance #1723): an img the writer left without any
# //// src is a photo slot with no photo, and it paints nothing: a feature card whose height came from
# //// its photograph collapsed to zero at desktop width (the copy over it, absolute, clipped away),
# //// and the gate measured text nobody could see. It becomes the plain block of any other slot (see
# //// neutral_empty_slots: the build does it, with images on or off).
# the hero / banner size the brief hands the model (system_prompts: "Hero/Banner: 1200x600")
EMPTY_SLOT_SIZE = (1200, 600)


def is_empty_slot(block: dict) -> bool:
    """An img that shows nothing and will show nothing: no src of any kind, none bound to data, not
    the skeleton of a component instance (its picture lives in the component)."""
    if str(block.get("element") or "").lower() != "img" or block.get("extendedFromComponent") or block.get("referenceBlockId"):
        return False
    attrs = block.get("attributes") or {}
    if any(str(attrs.get(key) or "").strip() for key in ("src", "data-src", "srcset")):
        return False
    return not any((d or {}).get("property") in ("src", "srcset") for d in block.get("dynamicValues") or [])


def neutral_empty_slots(blocks: list, palette: dict, prefix: str) -> int:
    """Every img with no src at all becomes the plain block of any other slot, whether image generation
    is on or off: the image job only draws the placehold.co URLs, and nothing would ever fill it. Run
    by the BUILD on the page it has just written, never at render (neutral_for_render): a page of a
    site that an editor built by hand may carry an img whose picture is not chosen yet, and showing
    a pale rectangle there is not ours to decide. Returns how many were filled."""
    filled = 0
    for block in _walk(blocks):
        if is_empty_slot(block):
            block.setdefault("attributes", {})["src"] = neutral_image(*EMPTY_SLOT_SIZE, palette, prefix)
            filled += 1
    return filled


# a placehold.co URL: its size, and the background colour it names when it names one. The
# greys handed to the model by default stand for no colour: the site's own takes their place.
SLOT = re.compile(r"placehold\.co/(\d+)x(\d+)(?:/([0-9a-fA-F]{3,8})(?=[/?&.]|$))?")
OUR_GREYS = {"e5e7eb", "cccccc", "ccc", "eeeeee", "eee"}
# the URL a placeholder takes in CSS, and in an HTML src: whole, up to its closing quote, since
# its caption may carry an apostrophe ("Cave+d'affinage" cut there left a broken image showing
# its alt text, 2026-09-13)
CSS_URL = re.compile(r"url\(\s*(['\"]?)(https?://placehold\.co/[^)]*?)\1\s*\)")
HTML_SRC = re.compile(r"(\bsrc\s*=\s*)(['\"])(https?://placehold\.co/.*?)\2")


def _neutral_for(url: str, palette: dict, prefix: str) -> str:
    """The plain block standing in for one placehold.co URL, of its size and colour."""
    match = SLOT.search(url or "")
    if not match:
        return neutral_image(1200, 800, palette, prefix)
    named = (match.group(3) or "").lower()
    colour = f"#{named}" if named and named not in OUR_GREYS else None
    return neutral_image(int(match.group(1)), int(match.group(2)), palette, prefix, colour)


def _replace_css(value: str, palette: dict, prefix: str) -> str:
    replaced = CSS_URL.sub(lambda m: f"url('{_neutral_for(m.group(2), palette, prefix)}')", value)
    if replaced == value and value.strip().startswith(("http://placehold.co", "https://placehold.co")):
        return f"url('{_neutral_for(value.strip(), palette, prefix)}')"
    return replaced


def _replace(text: str, palette: dict, prefix: str) -> str:
    """Each placehold.co URL of an HTML text: in a src attribute, whole, or in a CSS url()."""
    text = HTML_SRC.sub(lambda m: f"{m.group(1)}{m.group(2)}{_neutral_for(m.group(3), palette, prefix)}{m.group(2)}", text)
    return _replace_css(text, palette, prefix)


def neutral_placeholders(blocks: list, palette: dict, prefix: str) -> int:
    """Every placehold.co URL in an image source, a background or a text becomes an
    inline neutral block. Returns the number of blocks changed."""
    edits = 0
    for block in _walk(blocks):
        changed = False
        attrs = block.get("attributes") or {}
        for key in ("src", "data-src"):
            value = attrs.get(key)
            if isinstance(value, str) and "placehold.co" in value:
                attrs[key] = _neutral_for(value, palette, prefix)
                changed = True
        # the src carries the plain block; a srcset of placeholders would override it
        if isinstance(attrs.get("srcset"), str) and "placehold.co" in attrs["srcset"]:
            attrs.pop("srcset")
            changed = True
        for style_key in ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles"):
            styles = block.get(style_key) or {}
            for prop in ("backgroundImage", "background"):
                value = styles.get(prop)
                if isinstance(value, str) and "placehold.co" in value:
                    styles[prop] = _replace_css(value, palette, prefix)
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
        listed = data if isinstance(data, list) else [data]
        if not neutral_placeholders(listed, colours, "render"):
            return blocks
        # //// Neoffice — and the stand-in of a photo still to come is dark under copy written light for
        # //// it, in the tokens of this page's own site (contrast.darken_plain_slots, #1723). A page that
        # //// is only being shown is rewritten no further than that.
        try:
            from builder.site_ai.nora.contrast import darken_plain_slots, page_tokens

            tokens = page_tokens(blocks if isinstance(blocks, str) else json.dumps(blocks), palette)
            if tokens:
                darken_plain_slots(listed, tokens)
        except Exception:
            frappe.log_error("Placeholders: stand-ins left pale", frappe.get_traceback())
        return data
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
                attrs["src"] = _neutral_for(src, palette, prefix)
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
                    styles[prop] = _replace_css(value, palette, prefix)
                    edits.append(text[:60])
    return edits


# //// Neoffice — added (2026-10-26): a card whose photograph will not be drawn is a card without one. A regenerated site showed its
# //// photo cards with grey rectangles where two of the three pictures should have been: the guard above had withheld the card whose
# //// alt named a screen, and the image job had given up on another (the site draws the plain block of a placeholder nobody filled).
def _card_photo(card: dict) -> tuple[dict, dict] | None:
    """(the child of the card that carries its photograph, the img) for a card that opens on a picture: the img itself, or a wrapper
    around it that holds nothing else. None for a card with no copy beside the picture, or that opens on anything else."""
    kids = [c for c in card.get("children") or [] if isinstance(c, dict)]
    if len(kids) < 2:
        return None
    first = kids[0]
    if str(first.get("element") or "").lower() == "img":
        return first, first
    inside = [c for c in first.get("children") or [] if isinstance(c, dict)]
    if len(inside) == 1 and str(inside[0].get("element") or "").lower() == "img" and not (first.get("innerHTML") or first.get("innerText")):
        return first, inside[0]
    return None


def drop_plain_card_photos(blocks: list, failed=frozenset()) -> int:
    """Each card that opens on a photograph the site will draw as a plain block (neutral_image: withheld by neutral_named_slots, an
    image generation that is off, an img with no source), or that `failed` names by block id (the image job gave up on it), is written
    without the picture: its copy stays. In a row of cards where half of the photographs or more are gone the row has none, so that
    three cards are alike. A card with a real photograph, or one still waiting for the image job, is only touched by that rule.
    Returns the number of cards rewritten."""
    failed = set(failed or ())
    edits = 0
    for parent in _walk(blocks):
        photographed = [(card, found) for card in parent.get("children") or [] if isinstance(card, dict) and _is_card(card) and (found := _card_photo(card))]
        if not photographed:
            continue
        gone = [
            pair for pair in photographed
            if neutral_paint(str((pair[1][1].get("attributes") or {}).get("src") or "")) is not None or pair[1][1].get("blockId") in failed
        ]
        if not gone:
            continue
        rewritten = photographed if len(gone) * 2 >= len(photographed) else gone
        for card, (holder, _img) in rewritten:
            card["children"] = [c for c in card["children"] if c is not holder]
            edits += 1
    return edits
