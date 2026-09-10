# //// Neoffice — added file (no upstream equivalent): the sites and images a client likes, read
# //// for the site build. builder/site_ai/** = the Neoffice AI site generator.
"""Inspirations: the sites and images the client likes.

The old modal collected them (Builder Site Inspiration rows fed the brief); the Nora
playbook lost them in the move to the agent, and a link pasted in the chat reached
nobody (2026-09-08). They come back as tool arguments: every URL is screenshotted,
every picture read for its dominant colours, and the brief receives the pictures (the
vision pass) plus one line of findings per source. Each source is also kept as a
Builder Site Inspiration row, which the brief view lists."""

from __future__ import annotations

import json

import frappe
from frappe.utils import now

from builder.site_ai.logging import ai_log

# //// Neoffice — a client names the sites they like by the handful, six or eight in one
# //// email, and three was an arbitrary cap that silently dropped the rest. Reading is
# //// cheap (a screenshot and a colour count); only the vision pass costs, so it keeps
# //// its own, smaller bound.
MAX_URLS = 8
MAX_IMAGES = 8
MAX_VISION = 6
MAX_SOURCES = MAX_URLS  # kept: the name older callers import
MAX_COLOURS = 4

# //// Neoffice — how far from grey a colour has to be to count as a colour at all.
# //// Chroma is (max - min) / 255 of the RGB channels: 0 for any grey, black or white.
# //// Below this, a page has no colour, whatever its brightness.
NEUTRAL_CHROMA = 0.12
# //// Neoffice — and how much of the page may be chromatic before it counts as coloured.
# //// Measured on six references a client sent as "black and white, no other colour": the
# //// coloured share came out at 0, 1, 9 and 10 per cent. What pushes a photographic page
# //// past zero is skin, wood and sand in the pictures, plus the brand mark itself at one
# //// per cent. Judging each swatch on its own called two of those four pages coloured;
# //// the share is what actually says whether a page has a palette.
NEUTRAL_SHARE = 15.0
PALETTE_SHARE = 5.0  # kept: the name older callers import


def clean_list(value) -> list[str]:
    """Tool arguments arrive as a list, a JSON string or a comma-separated line."""
    if not value:
        return []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                value = json.loads(text)
            except ValueError:
                value = [text]
        else:
            value = [part for part in text.replace("\n", ",").split(",")]
    out = []
    for item in value if isinstance(value, (list, tuple)) else [value]:
        item = str(item or "").strip().strip("<>")
        if item and item.lower() not in ("none", "null", "aucun", "skip", "-") and item not in out:
            out.append(item)
    return out


def _notes(analysis: dict) -> str:
    colours = [c.get("hex") for c in (analysis or {}).get("dominant_colors") or [] if c.get("hex")][:MAX_COLOURS]
    parts = []
    if colours:
        parts.append("colours " + ", ".join(colours))
    if (analysis or {}).get("is_dark_theme") is not None:
        parts.append("dark" if analysis.get("is_dark_theme") else "light")
    # //// Neoffice — say it in words, because the hexes alone mislead: a page of large
    # //// photographs reads back as browns and greys, which is the photography, not a
    # //// palette. Told plainly, the brief keeps the structure and drops the mud.
    if colours and is_neutral(analysis):
        parts.append("NO COLOUR: neutrals only, the photographs carry the page")
    return ", ".join(parts)


# //// Neoffice ▼▼▼ — reading "no colour" off the sources. A client who asks for black
# //// and white says it in words AND by the sites they send; both must reach the brief.
def chroma(hex_colour: str) -> float:
    """Distance from grey, 0 (any grey, black, white) to 1 (a pure hue)."""
    value = (hex_colour or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        return 0.0
    try:
        channels = [int(value[i : i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return 0.0
    return (max(channels) - min(channels)) / 255


def coloured_share(analysis: dict) -> float:
    """How much of the picture, in per cent, is anything other than a grey."""
    return sum(
        (c.get("percentage") or 0)
        for c in (analysis or {}).get("dominant_colors") or []
        if c.get("hex") and chroma(c["hex"]) >= NEUTRAL_CHROMA
    )


def is_neutral(analysis: dict) -> bool:
    """True when the picture has no palette: almost none of it is chromatic."""
    colours = [c for c in (analysis or {}).get("dominant_colors") or [] if c.get("hex")]
    if not colours:
        return False
    # //// Neoffice — an analysis that carries hexes but no percentages says NOTHING
    # //// about how much of the page is coloured, and `coloured_share` sums missing
    # //// weights as zero. Read literally, that made every such palette "neutrals
    # //// only" -- a bright red and a blue included -- and one neutral source is
    # //// enough for monochrome() to send the whole brief to black and white. Unknown
    # //// is not zero: with no weights at all we say nothing.
    if not any(c.get("percentage") is not None for c in colours):
        return False
    return coloured_share(analysis) <= NEUTRAL_SHARE


def monochrome(found: dict) -> bool:
    """True when EVERY source read is neutral: the client's references have no colour,
    so neither should the site. One coloured reference is enough to say nothing."""
    sources = [s for s in (found or {}).get("sources") or [] if (s.get("analysis") or {}).get("dominant_colors")]
    return bool(sources) and all(is_neutral(s["analysis"]) for s in sources)
# //// Neoffice ▲▲▲


def _analyse(file_url: str) -> dict:
    from builder.site_ai.inspiration.analyzer import DesignAnalyzer

    try:
        return DesignAnalyzer().analyze_from_file_url(file_url)
    except Exception as e:
        ai_log("warning", "Inspiration image not analysed", file=file_url, error=str(e)[:120])
        return {}


def read_url(url: str) -> dict:
    """A site the client likes: its above-the-fold look as a screenshot, and the colours."""
    from builder.site_ai.inspiration.screenshotter import capture_website_screenshot
    from builder.site_ai.inspiration.site_extractor import assert_public_http_url

    url = assert_public_http_url(url)
    shot = capture_website_screenshot(url, full_page=False)
    if not shot.get("success") or not shot.get("file_url"):
        raise RuntimeError(str(shot.get("error") or "screenshot failed"))
    analysis = _analyse(shot["file_url"])
    return {"kind": "URL", "source": url, "image": shot["file_url"], "analysis": analysis, "title": shot.get("title") or ""}


def read_image(file_url: str) -> dict:
    """A picture the client likes (uploaded through a card, or attached to a message)."""
    if not file_url.startswith(("/files/", "/private/files/")):
        raise ValueError("not a site file")
    return {"kind": "Image", "source": file_url, "image": file_url, "analysis": _analyse(file_url), "title": ""}


def _record(item: dict) -> None:
    """Keep the source as a Builder Site Inspiration row (best effort: the build must
    not fail on bookkeeping)."""
    try:
        if not frappe.db.exists("DocType", "Builder Site Inspiration"):
            return
        doc = frappe.get_doc(
            {
                "doctype": "Builder Site Inspiration",
                "source_type": item["kind"],
                "url": item["source"] if item["kind"] == "URL" else None,
                "image": item["source"] if item["kind"] == "Image" else None,
                "screenshot": item["image"] if item["kind"] == "URL" else None,
                "sentiment": "like",
                "status": "captured",
                "captured_at": now(),
                "analysis": json.dumps(item.get("analysis") or {}),
            }
        )
        doc.insert(ignore_permissions=True)
    except Exception as e:
        ai_log("warning", "Inspiration not recorded", source=item.get("source"), error=str(e)[:120])


def gather(urls: list[str], images: list[str], record: bool = True) -> dict:
    """Read every source (at most MAX_URLS sites and MAX_IMAGES pictures). Returns the pictures for the
    vision pass, one line of findings per source, and the sources that could not be read."""
    found, failed = [], []
    for url in clean_list(urls)[:MAX_URLS]:
        try:
            found.append(read_url(url))
        except Exception as e:
            failed.append(f"{url} ({str(e)[:80]})")
            ai_log("warning", "Inspiration site not read", url=url, error=str(e)[:120])
    for image in clean_list(images)[:MAX_IMAGES]:
        try:
            found.append(read_image(image))
        except Exception as e:
            failed.append(f"{image} ({str(e)[:80]})")
    if record:
        for item in found:
            _record(item)
    notes = []
    for item in found:
        label = item["source"] if item["kind"] == "URL" else "picture"
        line = _notes(item.get("analysis"))
        notes.append(f"{label}: {line}" if line else label)
    return {"images": [item["image"] for item in found], "notes": notes, "failed": failed, "sources": found}


def describe(found: dict, model: str | None = None) -> str:
    """What the assistant can say about the sources: the measured colours, and when a
    vision model is at hand, three lines on the style of each picture."""
    lines = []
    for i, item in enumerate(found.get("sources") or [], 1):
        head = item["source"] if item["kind"] == "URL" else f"picture {item['source']}"
        note = _notes(item.get("analysis"))
        lines.append(f"{i}. {head}" + (f" — {note}" if note else ""))
    for failure in found.get("failed") or []:
        lines.append(f"Could not read {failure}.")
    if found.get("images") and model:
        try:
            from builder.site_ai.providers.litellm_provider import LiteLLMProvider

            provider = LiteLLMProvider(model=model)
            if provider.supports_vision():
                text = provider.generate(
                    "For each attached picture, in this order, give three short lines: palette (hex), typography feel, "
                    "layout pattern and mood. Number them. No preamble.",
                    images=found["images"][:MAX_VISION],
                    max_tokens=600,
                )
                if text and text.strip():
                    lines.append("Style read from the pictures:\n" + text.strip())
        except Exception as e:
            ai_log("warning", "Inspiration description failed", error=str(e)[:120])
    if not lines:
        return "No inspiration could be read."
    return "\n".join(lines) + "\nKeep these for generate_site (inspiration_urls / inspiration_images)."


# //// Neoffice ▼▼▼ — the brief painted the consumer site's header in the rose of its wordmark and the wordmark vanished; this guard moves a header background close to a dominant logo colour to the site's background token, or to white when that is a logo colour too (925e2366 "fix(nora): the header never wears one of the logo's own colours")
LOGO_COLOUR_DISTANCE = 56


def _rgb(hex_colour: str):
    value = (hex_colour or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return None


def colour_near(a: str, b: str, distance: int = LOGO_COLOUR_DISTANCE) -> bool:
    ra, rb = _rgb(a), _rgb(b)
    if not ra or not rb:
        return False
    return sum((x - y) ** 2 for x, y in zip(ra, rb)) ** 0.5 < distance


def logo_colours(file_url: str) -> list[str]:
    """The dominant colours of the logo, for the header guard below."""
    if not file_url or not str(file_url).startswith(("/files/", "/private/files/")):
        return []
    return [c.get("hex") for c in (_analyse(file_url) or {}).get("dominant_colors") or [] if c.get("hex")]


def header_off_logo_palette(config, logo_image: str | None, palette: dict, prefix: str) -> str | None:
    """A header painted in one of the logo's own colours hides the logo: the brief gave
    the consumer site the rose of its wordmark and the wordmark vanished (2026-09-09). The
    background moves to the site's background token, or to white when that is a logo
    colour too; the text follows. Returns the new background, None when nothing moved."""
    current = (config.get("header_bg_color") or "").strip()
    colours = logo_colours(logo_image)
    if not current or not colours or not any(colour_near(current, c) for c in colours):
        return None
    background = (palette or {}).get(f"{prefix}-background") or "#ffffff"
    if any(colour_near(background, c) for c in colours):
        background = "#ffffff"
    config.header_bg_color = background
    config.header_text_color = (palette or {}).get(f"{prefix}-text") or "#1a1a1a"
    return background
# //// Neoffice ▲▲▲
