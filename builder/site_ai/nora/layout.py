# //// Neoffice — added file (no upstream equivalent): the layout passes a written page goes through.
"""Layout a page can live with.

The page writer lays sections on a 12-column grid and places each child by a span
(`gridColumn: 1 / -1` for a heading, `span 4` for a card). A child it forgets to place
takes ONE of the twelve columns: on the B2B regeneration (2026-09-08) the cards wrapper
of every section rendered as a 110 px column with the cards stacked inside, on the
desktop and in the editor alike, and a revision pass did not catch it. Placing the
forgotten child across the row is what the author meant.

Pure functions over the block tree."""

import copy
import re
import unicodedata
import uuid

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


# //// Neoffice ▼▼▼ — the trust section of a reseller site's home listed its four reasons as
# //// rows: a card repeater or a card wrapper without a grid now gets u-grid and a
# //// column count (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
def _is_card(block: dict) -> bool:
    return "u-card" in (block.get("classes") or [])


def repeater_counts(data_script: str) -> dict:
    """How many rows each repeater has, from the page data script (`data.key = [...]`)."""
    import json

    counts = {}
    for m in re.finditer(r"^\s*data\.(\w+)\s*=\s*(\[.*\])\s*;?\s*$", data_script or "", re.M):
        try:
            counts[m.group(1)] = len(json.loads(m.group(2)))
        except ValueError:
            continue
    return counts


def grid_stacked_cards(blocks: list, data_counts: dict | None = None) -> int:
    """A repeater whose template is a card, or a plain wrapper holding two cards or
    more, stacks them in one column when it carries no grid: the trust section of The
    League's home listed its four reasons as rows (2026-09-09). They get u-grid and a
    column count from the repeater's data (three when unknown) or the number of cards,
    between two and four. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        classes = list(block.get("classes") or [])
        styles = block.get("baseStyles") or {}
        if any(c.startswith("u-grid") for c in classes) or styles.get("display") == "grid":
            continue
        if styles.get("display") == "flex" and styles.get("flexDirection") not in ("column", "column-reverse"):
            continue
        kids = [c for c in (block.get("children") or []) if isinstance(c, dict)]
        if _is_repeater(block):
            if len(kids) != 1 or not _is_card(kids[0]):
                continue
            count = (data_counts or {}).get((block.get("dataKey") or {}).get("key")) or 3
        else:
            if len(kids) < 2 or not all(_is_card(c) for c in kids):
                continue
            count = len(kids)
        block["classes"] = classes + ["u-grid", f"u-grid--{max(2, min(4, count))}"]
        for key in ("display", "flexDirection", "flexWrap"):
            styles.pop(key, None)
        edits += 1
    return edits
# //// Neoffice ▲▲▲


# //// Neoffice — columns for the phone (2026-09-14): balance_grids gave a home's five tiles five
# //// columns and nothing for the narrower screens, and a 390 px phone showed five 50 px cells with
# //// their labels cut. A grid of equal items that the phone would lay out at three columns or more
# //// gets columns of its own there: two from four items, one below.
def _tracks(value) -> int:
    """The number of columns a gridTemplateColumns value lays out: repeat(N, ...) or a list of
    tracks. 0 when there is none, 1 for a repeat(auto-fit, ...) that lays itself out."""
    text = str(value or "").strip()
    m = WIDE_GRID.match(text)
    if m:
        return int(m.group(1))
    count, depth, inside = 0, 0, False
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch.isspace() and depth == 0:
            if inside:
                count += 1
            inside = False
        else:
            inside = True
    return count + 1 if inside else count


def _narrow_screens(block: dict, items: int) -> int:
    """Columns for the tablet and the phone of a grid of `items` equal items, where the page wrote
    none: three on the tablet for six items or more, two on the phone from four items and one below.
    The odd last card of a plain grid takes the phone's whole row (a repeater's clones cannot be told
    apart). A screen inherits the wider screen's columns, so what it would inherit is what is judged.
    Returns the edit count."""
    edits = 0
    base = (block.get("baseStyles") or {}).get("gridTemplateColumns")
    tablet = block.get("tabletStyles") or {}
    mobile = block.get("mobileStyles") or {}
    if items >= 6 and "gridTemplateColumns" not in tablet and _tracks(base) >= 6:
        tablet["gridTemplateColumns"] = "repeat(3, minmax(0, 1fr))"
        block["tabletStyles"] = tablet
        edits += 1
    if "gridTemplateColumns" in mobile or _tracks(tablet.get("gridTemplateColumns") or base) < 3:
        return edits
    mobile["gridTemplateColumns"] = "repeat(2, minmax(0, 1fr))" if items >= 4 else "minmax(0, 1fr)"
    block["mobileStyles"] = mobile
    edits += 1
    kids = [c for c in block.get("children") or [] if isinstance(c, dict)]
    if items >= 4 and items % 2 and kids and not _is_repeater(block):
        last = kids[-1].get("mobileStyles") or {}
        last.setdefault("gridColumn", "1 / -1")
        kids[-1]["mobileStyles"] = last
    return edits


def phone_columns(blocks: list, data_counts: dict | None = None) -> int:
    """Every grid of equal items (no child placed by a span) that the phone would lay out at three
    columns or more gets columns of its own there (_narrow_screens). The twelve-column layout grids
    are left to place_orphans and to the page's own mobile styles. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        styles = block.get("baseStyles") or {}
        if styles.get("display") != "grid" or _tracks(styles.get("gridTemplateColumns")) >= MIN_COLUMNS:
            continue
        kids = [c for c in block.get("children") or [] if isinstance(c, dict)]
        if any(_placed(c) for c in kids):
            continue
        if _is_repeater(block):
            items = (data_counts or {}).get((block.get("dataKey") or {}).get("key")) or _tracks(styles.get("gridTemplateColumns"))
        else:
            items = len(kids)
        edits += _narrow_screens(block, items)
    return edits


# //// Neoffice — a grid never ends on a hole it can avoid (2026-09-14): five photo tiles on three
# //// columns left the sixth cell of a home empty, a black square in a row of photographs.
def balance_grids(blocks: list, data_counts: dict | None = None) -> int:
    """A grid of up to six items that its column count does not divide lays them on one row of a
    desktop: five tiles, five columns. The count is the repeater's rows (from the page data) or the
    grid's children. The narrower screens the page wrote no columns for get some (_narrow_screens):
    five columns are a desktop answer. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        styles = block.get("baseStyles") or {}
        columns = _columns(styles)
        if not columns:
            continue
        if _is_repeater(block):
            items = (data_counts or {}).get((block.get("dataKey") or {}).get("key"))
        else:
            items = len([c for c in block.get("children") or [] if isinstance(c, dict)])
        if not items or items > 6 or items % columns == 0:
            continue
        styles["gridTemplateColumns"] = f"repeat({items}, minmax(0, 1fr))"
        block["baseStyles"] = styles
        _narrow_screens(block, items)
        edits += 1
    # //// Neoffice — a grid drawn by the design system's classes (u-grid u-grid--3) carries no inline
    # //// columns to change: the brands page of a consumer site kept its sixth cell empty on the rebuilt
    # //// site. It takes u-grid--fill, whose items share the last row at every width (theme_variables.html).
    for block in _walk(blocks):
        classes = [str(c) for c in block.get("classes") or []]
        wide = next((c for c in classes if c.startswith("u-grid--") and c[8:].isdigit()), None)
        if not wide or "u-grid--fill" in classes or (block.get("baseStyles") or {}).get("display") == "grid":
            continue
        columns = int(wide[8:])
        if _is_repeater(block):
            items = (data_counts or {}).get((block.get("dataKey") or {}).get("key"))
        else:
            items = len([c for c in block.get("children") or [] if isinstance(c, dict)])
        if not items or items % columns == 0:
            continue
        block["classes"] = [*classes, "u-grid--fill"]
        edits += 1
    return edits


# //// Neoffice — the tiles of one grid are alike (2026-09-14): an About page showed the site's five
# //// categories as tiles, one on its photograph and four in flat grey, because only the home and the
# //// listing page were handed a photograph per category (site_builder.category_photo_map).
URL_IN_BACKGROUND = re.compile(r"url\((['\"]?)([^'\")]+)\1\)")
STYLE_FIELDS = ("baseStyles", "mobileStyles", "tabletStyles", "rawStyles", "classes")


def _tile_photo(block: dict) -> str | None:
    """The photograph a tile shows: an image's source or a background image's url."""
    for b in _walk([block]):
        if b.get("element") == "img":
            src = str((b.get("attributes") or {}).get("src") or "")
            if src and not src.startswith("data:"):
                return src
        m = URL_IN_BACKGROUND.search(str((b.get("baseStyles") or {}).get("backgroundImage") or ""))
        if m:
            return m.group(2)
    return None


def _shape(block: dict) -> tuple:
    return (block.get("element"), tuple(_shape(c) for c in block.get("children") or [] if isinstance(c, dict)))


def _texts(block: dict) -> list[dict]:
    return [b for b in _walk([block]) if isinstance(b.get("innerHTML"), str) and _plain(b["innerHTML"])]


def _tile_category(tile: dict, names: dict) -> str | None:
    """The category a tile is named after: its text is the name, or holds it as a whole word."""
    label = _plain(" ".join(b["innerHTML"] for b in _texts(tile)))
    if label in names:
        return label
    found = [n for n in names if re.search(rf"\b{re.escape(n)}\b", label)]
    return found[0] if len(found) == 1 else None


def _restyle(tile: dict, model: dict, old_url: str, new_url: str) -> None:
    """Give `tile` the styles of `model`, block by block, with its own photograph in place of the
    model's; the texts, links and bindings stay the tile's."""
    pairs = [(tile, model)]
    while pairs:
        t, m = pairs.pop()
        for field in STYLE_FIELDS:
            if field not in m:
                t.pop(field, None)
                continue
            value = copy.deepcopy(m[field])
            if isinstance(value, dict):
                value = {k: v.replace(old_url, new_url) if isinstance(v, str) else v for k, v in value.items()}
            t[field] = value
        if t.get("element") == "img" and (m.get("attributes") or {}).get("src") == old_url:
            t.setdefault("attributes", {})["src"] = new_url
        pairs.extend(
            zip(
                [c for c in t.get("children") or [] if isinstance(c, dict)],
                [c for c in m.get("children") or [] if isinstance(c, dict)],
                strict=True,
            )
        )


def _relabelled_copy(tile: dict, model: dict, old_url: str, new_url: str) -> dict | None:
    """The model tile with the tile's texts and links, when their structures differ (a veil layer the
    flat tile lacks): None unless both carry the same number of texts and links."""
    texts, model_texts = _texts(tile), _texts(model)
    links = [b for b in _walk([tile]) if b.get("element") == "a"]
    clone = copy.deepcopy(model)
    clone_links = [b for b in _walk([clone]) if b.get("element") == "a"]
    if len(texts) != len(model_texts) or len(links) != len(clone_links):
        return None
    for mine, theirs in zip(_texts(clone), texts, strict=True):
        mine["innerHTML"] = theirs["innerHTML"]
    for mine, theirs in zip(clone_links, links, strict=True):
        mine["attributes"] = {**(mine.get("attributes") or {}), **{k: v for k, v in (theirs.get("attributes") or {}).items() if k == "href"}}
    for b in _walk([clone]):
        b["blockId"] = uuid.uuid4().hex[:10]
        styles = b.get("baseStyles") or {}
        for key, value in list(styles.items()):
            if isinstance(value, str) and old_url in value:
                styles[key] = value.replace(old_url, new_url)
        if b.get("element") == "img" and (b.get("attributes") or {}).get("src") == old_url:
            b["attributes"]["src"] = new_url
    return clone


def complete_tile_photos(blocks: list, category_photos: dict) -> list[str]:
    """A grid of three tiles or more that shows some on a photograph and others flat: each flat tile
    named after a category takes that category's photograph, dressed like the photographed tile.
    Returns the names of the tiles completed."""
    names = {_plain(name): url for name, url in (category_photos or {}).items() if url and _plain(name)}
    done = []
    if not names:
        return done
    for grid in _walk(blocks):
        tiles = [c for c in grid.get("children") or [] if isinstance(c, dict)]
        if len(tiles) < 3 or not _is_grid(grid):
            continue
        photos = [_tile_photo(t) for t in tiles]
        if all(photos) or not any(photos):
            continue
        model, model_url = next((t, url) for t, url in zip(tiles, photos, strict=True) if url)
        for tile, url in zip(tiles, photos, strict=True):
            name = None if url else _tile_category(tile, names)
            if not name:
                continue
            if _shape(tile) == _shape(model):
                _restyle(tile, model, model_url, names[name])
            else:
                clone = _relabelled_copy(tile, model, model_url, names[name])
                if clone is None:
                    continue
                grid["children"][grid["children"].index(tile)] = clone
            done.append(name)
    return done

