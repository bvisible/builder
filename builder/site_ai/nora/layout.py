"""Layout a page can live with.

The page writer lays sections on a 12-column grid and places each child by a span
(`gridColumn: 1 / -1` for a heading, `span 4` for a card). A child it forgets to place
takes ONE of the twelve columns: on the B2B regeneration (2026-09-08) the cards wrapper
of every section rendered as a 110 px column with the cards stacked inside, on the
desktop and in the editor alike, and a revision pass did not catch it. Placing the
forgotten child across the row is what the author meant.

Pure functions over the block tree."""

import re

STYLE_KEYS = ("baseStyles", "tabletStyles")
WIDE_GRID = re.compile(r"repeat\(\s*(\d+)\s*,")
MIN_COLUMNS = 6
PLACEMENT_KEYS = ("gridColumn", "gridColumnStart", "gridColumnEnd", "gridArea")


def _walk(blocks: list):
    stack = list(blocks or [])
    while stack:
        block = stack.pop()
        if not isinstance(block, dict):
            continue
        yield block
        stack.extend(block.get("children") or [])


def _columns(styles: dict) -> int:
    if (styles or {}).get("display") != "grid":
        return 0
    m = WIDE_GRID.search(str(styles.get("gridTemplateColumns") or ""))
    return int(m.group(1)) if m else 0


def _placed(child: dict) -> bool:
    return any(key in (child.get("baseStyles") or {}) for key in PLACEMENT_KEYS)


def place_orphans(blocks: list) -> int:
    """Give a full-row span to every unplaced child of a wide grid when the unplaced
    children are too few to be a row of single-column items. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        columns = _columns(block.get("baseStyles") or {})
        if columns < MIN_COLUMNS:
            continue
        children = [c for c in (block.get("children") or []) if isinstance(c, dict)]
        unplaced = [c for c in children if not _placed(c)]
        if not unplaced or len(unplaced) > columns // 2:
            continue
        for child in unplaced:
            child.setdefault("baseStyles", {})["gridColumn"] = "1 / -1"
            edits += 1
    return edits
