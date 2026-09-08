# //// Neoffice — added file (no upstream equivalent): French spacing on generated text.
# //// builder/site_ai/** = the Neoffice AI site generator; frappe/builder ships no such module.
"""French spacing the model does not type.

French sets a no-break space before ? ! : ; » and after «. The model writes a plain
space, and the browser breaks the line in front of the mark: on the card-driven B2C run
(2026-09-08) a CTA heading ended on a lone "?" on its own line. The narrow no-break
space (U+202F) replaces that plain space in the text of every block, outside tags,
Jinja and SVG markup.

Pure functions over the block tree."""

import re

from builder.site_ai.nora.layout import _walk

NNBSP = " "
BEFORE = re.compile(r"[  ]+([?!:;»])")
AFTER = re.compile(r"(«)[  ]+")
TAG = re.compile(r"(<[^>]*>)")


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
