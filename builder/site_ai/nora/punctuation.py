# //// Neoffice — added file (no upstream equivalent): French spacing on generated text.
# //// builder/site_ai/** = the Neoffice AI site generator; frappe/builder ships no such module.
"""French spacing the model does not type.

French sets a no-break space before ? ! : ; » and after «. The model writes a plain
space, and the browser breaks the line in front of the mark: on the card-driven B2C run
(2026-09-08) a CTA heading ended on a lone "?" on its own line. The narrow no-break
space (U+202F) replaces that plain space in the text of every block, outside tags,
Jinja and SVG markup.

Pure functions over the block tree."""

import json
import re

from builder.site_ai.nora.layout import _walk

NNBSP = " "
BEFORE = re.compile(r"[  ]+([?!:;»])")
AFTER = re.compile(r"(«)[  ]+")
TAG = re.compile(r"(<[^>]*>)")

# an elision the model wrote with a space where the apostrophe goes: "les bases d un travail",
# "un temps d écoute" on a practice's services page (2026-09-13). The apostrophe comes back, as
# the typographic apostrophe (U+2019). A single letter never stands alone in French but "a", "à" and "y"; one
# after a number is a unit ("à 5 m à pied") and is left alone.
ELISION = re.compile(
    r"(?<!\d )\b([dDlLnNmMtTsSjJcC]|[qQ]u|[jJ]usqu|[lL]orsqu|[pP]uisqu|[qQ]uoiqu|[aA]ujourd) "
    r"(?=[aeiouyhàâäéèêëîïôöûüœæAEIOUYHÀÂÄÉÈÊËÎÏÔÖÛÜŒÆ])"
)
DATA_LINE = re.compile(r"^(data\.[A-Za-z_]\w*\s*=\s*)(.+)$", re.M)


def _fix_text(text: str) -> str:
    text = BEFORE.sub(NNBSP + r"\1", text)
    return AFTER.sub(r"\1" + NNBSP, text)


def french_spacing(blocks: list) -> int:
    """Narrow no-break spaces around French double punctuation in every text block.
    Returns the number of blocks changed."""
    edits = 0
    for block in _walk(blocks):
        html = block.get("innerHTML")
        if not isinstance(html, str) or not html or "{%" in html or "{{" in html or "<svg" in html:
            continue
        fixed = "".join(part if part.startswith("<") else _fix_text(part) for part in TAG.split(html))
        if fixed != html:
            block["innerHTML"] = fixed
            edits += 1
    return edits


def _elide(text: str) -> str:
    return ELISION.sub(lambda m: m.group(1) + "’", text)


def french_elisions(blocks: list) -> int:
    """The apostrophe of every elision written with a space (ELISION), in the text of the blocks
    (outside tags, Jinja and SVG markup) and in the texts of their attributes that a visitor or a
    screen reader gets. Returns the number of blocks changed."""
    edits = 0
    for block in _walk(blocks):
        changed = False
        html = block.get("innerHTML")
        if isinstance(html, str) and html and "{%" not in html and "{{" not in html and "<svg" not in html:
            fixed = "".join(part if part.startswith("<") else _elide(part) for part in TAG.split(html))
            if fixed != html:
                block["innerHTML"] = fixed
                changed = True
        attrs = block.get("attributes") or {}
        for key in ("alt", "title", "placeholder", "aria-label"):
            value = attrs.get(key)
            if isinstance(value, str) and _elide(value) != value:
                attrs[key] = _elide(value)
                changed = True
        edits += changed
    return edits


def _elide_values(value):
    if isinstance(value, str):
        return _elide(value)
    if isinstance(value, list):
        return [_elide_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _elide_values(item) for key, item in value.items()}
    return value


def script_elisions(script: str) -> tuple[str, int]:
    """The same apostrophes in the strings of the page's data script, whose lines are
    `data.<key> = <JSON>`: the repeated cards of the services page carried them. A line that is
    not JSON is left as it is. Returns (script, lines changed)."""
    edits = 0

    def fix(match) -> str:
        nonlocal edits
        try:
            value = json.loads(match.group(2))
        except ValueError:
            return match.group(0)
        fixed = _elide_values(value)
        if fixed == value:
            return match.group(0)
        edits += 1
        return match.group(1) + json.dumps(fixed, separators=(",", ":"))

    return DATA_LINE.sub(fix, script or ""), edits
