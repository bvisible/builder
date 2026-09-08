"""Layout a page can live with.

The page writer lays sections on a 12-column grid and places each child by a span
(`gridColumn: 1 / -1` for a heading, `span 4` for a card). A child it forgets to place
takes ONE of the twelve columns: on the B2B regeneration (2026-09-08) the cards wrapper
of every section rendered as a 110 px column with the cards stacked inside, on the
desktop and in the editor alike, and a revision pass did not catch it. Placing the
forgotten child across the row is what the author meant.

Pure functions over the block tree."""

import re
import unicodedata

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


def _is_grid(block: dict) -> bool:
    return "u-grid" in (block.get("classes") or []) or (block.get("baseStyles") or {}).get("display") == "grid"


def _is_plain_wrapper(block: dict) -> bool:
    """A div with no class, no style and no text of its own."""
    if (block.get("element") or "div") != "div" or block.get("classes"):
        return False
    text = block.get("innerHTML")
    if isinstance(text, str) and text.strip():
        return False
    for key in ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles"):
        if any(value != "contents" for value in (block.get(key) or {}).values()):
            return False
    return True


GRID_STYLE_KEYS = ("gridTemplateColumns", "gridTemplateRows", "gridAutoFlow", "gap", "rowGap", "columnGap")


def _is_repeater(block: dict) -> bool:
    return bool(block.get("isRepeaterBlock") or block.get("dataKey"))


def _hand_grid_to_repeater(grid: dict, repeater: dict) -> None:
    """The repeater becomes the grid: its clones are the grid items, not the repeater."""
    grid_classes = [c for c in (grid.get("classes") or []) if c.startswith("u-grid")]
    repeater["classes"] = grid_classes + [c for c in (repeater.get("classes") or []) if c not in grid_classes]
    grid["classes"] = [c for c in (grid.get("classes") or []) if c not in grid_classes]
    styles = grid.get("baseStyles") or {}
    target = repeater.setdefault("baseStyles", {})
    for key in ("display", "flexDirection", "flexWrap"):
        target.pop(key, None)
    if styles.get("display") == "grid":
        target["display"] = styles.pop("display")
    for key in GRID_STYLE_KEYS:
        if key in styles:
            target[key] = styles.pop(key)


def unwrap_grid_wrappers(blocks: list) -> int:
    """A grid whose only item is a wrapper around the cards renders as one column with
    the cards stacked inside — twice on the Boutique page of the card-driven B2C run
    (2026-09-08), and the vision model still called the page professional. A plain
    wrapper is removed and its children become the grid's items; a repeater (one
    template child, cloned per data row) keeps its role and takes the grid over
    instead, so its clones are the items. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        if not _is_grid(block):
            continue
        children = [c for c in (block.get("children") or []) if isinstance(c, dict)]
        if len(children) == 1 and _is_repeater(children[0]):
            _hand_grid_to_repeater(block, children[0])
            edits += 1
            continue
        if len(children) != 1 or not _is_plain_wrapper(children[0]):
            continue
        items = [c for c in (children[0].get("children") or []) if isinstance(c, dict)]
        if len(items) < 2:
            continue
        block["children"] = items
        edits += 1
    return edits


def _plain(text) -> str:
    """Text reduced for comparison: no markup, no accents, no case, no punctuation."""
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def strip_title_band(blocks: list, title: str) -> int:
    """Drop the title the model writes at the top of an interior page although the site
    renders its own band there (page_header.py): "À propos" stood twice on the card-driven
    B2C run (2026-09-08). A first section that is only the title, with at most a subtitle,
    goes; a first section with more content keeps everything but the repeated heading.
    Returns the number of blocks removed."""
    wanted = _plain(title)
    root = blocks[0] if blocks and isinstance(blocks[0], dict) else None
    sections = [c for c in ((root or {}).get("children") or []) if isinstance(c, dict)]
    if not wanted or not sections:
        return 0
    first = sections[0]
    headings = [b for b in _walk([first]) if b.get("element") in ("h1", "h2") and _plain(b.get("innerHTML")) == wanted]
    if not headings:
        return 0
    texts = [b for b in _walk([first]) if isinstance(b.get("innerHTML"), str) and "<svg" not in b["innerHTML"] and _plain(b["innerHTML"])]
    images = [b for b in _walk([first]) if b.get("element") == "img" or (b.get("baseStyles") or {}).get("backgroundImage")]
    if len(texts) <= 2 and not images:
        root["children"] = [c for c in root["children"] if c is not first]
        return 1
    removed = 0
    for block in _walk([first]):
        kids = block.get("children") or []
        kept = [k for k in kids if not any(k is h for h in headings)]
        if len(kept) != len(kids):
            block["children"] = kept
            removed += len(kids) - len(kept)
    return removed
