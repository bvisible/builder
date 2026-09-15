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
import math
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


def repeater_rows(data_script: str) -> dict:
	"""The rows each repeater draws, from the page data script (`data.key = [{...}]`). A generated
	page lists its categories there and clones one template over them, so the rows are where their
	words, photographs and links live."""
	import json

	rows = {}
	for m in re.finditer(r"^\s*data\.(\w+)\s*=\s*(\[.*\])\s*;?\s*$", data_script or "", re.M):
		try:
			value = json.loads(m.group(2))
		except ValueError:
			continue
		if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
			rows[m.group(1)] = value
	return rows


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


# //// Neoffice — the last item alone on its phone row takes the row (2026-09-14): an About page's five
# //// framed category tiles, on the two phone columns the page wrote itself, left a white cell beside
# //// the fifth inside the frame.
def _phone_template(block: dict) -> str | None:
    """The columns the phone lays a grid on: its own, else the tablet's, else the desktop's."""
    for key in ("mobileStyles", "tabletStyles", "baseStyles"):
        value = (block.get(key) or {}).get("gridTemplateColumns")
        if value:
            return value
    return None


def fill_last_phone_row(blocks: list) -> int:
    """In a plain grid of equal items, the last item alone on its phone row spans the row. A
    repeater's clones cannot be told apart and are left as they are. Returns the edit count."""
    edits = 0
    for block in _walk(blocks):
        if (block.get("baseStyles") or {}).get("display") != "grid" or _is_repeater(block):
            continue
        kids = [c for c in block.get("children") or [] if isinstance(c, dict)]
        columns = _tracks(_phone_template(block))
        if columns < 2 or len(kids) <= columns or len(kids) % columns != 1 or any(_placed(c) for c in kids):
            continue
        last = kids[-1].get("mobileStyles") or {}
        if "gridColumn" in last:
            continue
        last["gridColumn"] = "1 / -1"
        kids[-1]["mobileStyles"] = last
        edits += 1
    return edits


# //// Neoffice — the categories as one circle cut into parts (2026-09-15). A brand whose mark is a
# //// circle of segments — a wheel, a rosette, a pie — can show its categories in the shape of that
# //// mark: one circle, one part per category, each part on its own photograph, the mark in the
# //// middle. It is a way of showing three to six categories, not a drawing for one site: the brief
# //// picks it (design_brief.category_showcase) and every other site keeps its tiles.
WHEEL_GAP = 1.6      # the white day between two parts, in degrees
WHEEL_REACH = 75     # how far a part reaches before the circle clips it
WHEEL_MIN, WHEEL_MAX = 3, 6


def _wheel_point(index: float, count: int, reach: float) -> tuple[float, float]:
	"""A point at `reach` percent from the middle, in the direction of part `index`."""
	angle = math.radians(-90 + index * (360 / count))
	return 50 + reach * math.cos(angle), 50 + reach * math.sin(angle)


def _wheel_slice_path(index: int, count: int) -> str:
	"""The clip-path of one part, drawn from the middle of the circle out along its arc."""
	step = 360 / count
	start, end = -90 + index * step + WHEEL_GAP, -90 + (index + 1) * step - WHEEL_GAP
	points = ["50% 50%"]
	steps = max(2, int((end - start) / 6))
	for k in range(steps + 1):
		angle = math.radians(start + (end - start) * k / steps)
		points.append(f"{50 + WHEEL_REACH * math.cos(angle):.2f}% {50 + WHEEL_REACH * math.sin(angle):.2f}%")
	return "polygon(" + ", ".join(points) + ")"


def _tile_link(tile: dict) -> str:
	"""Where a tile leads: its own href, else the first link it carries."""
	for block in _walk([tile]):
		href = str((block.get("attributes") or {}).get("href") or "")
		if href:
			return href
	return ""


def _tile_label(tile: dict) -> tuple[str, dict]:
	"""The words a tile shows and the styles they are set in: its first text, empty when it has none."""
	texts = _texts(tile)
	if not texts:
		return "", {}
	return str(texts[0].get("innerHTML") or ""), dict(texts[0].get("baseStyles") or {})


def _wheel_parts(tiles: list, names: dict) -> list | None:
	"""(label, label styles, photograph, link) for each tile, or None when one of them has no
	photograph or nothing to say — a circle of parts needs every part."""
	parts = []
	for tile in tiles:
		name = _tile_category(tile, names) if names else None
		photo = _tile_photo(tile) or (names.get(name) if name else None)
		label, styles = _tile_label(tile)
		if not photo or not _plain(label):
			return None
		parts.append((label, styles, photo, _tile_link(tile)))
	return parts


def _rows_parts(rows: list, names: dict, template: dict) -> list | None:
	"""The parts a repeater's rows draw: each row's words, photograph and link, set in the face the
	template gives its words. None when a row has no picture or nothing to say."""
	_label, styles = _tile_label(template)
	parts = []
	for row in rows:
		label = str(row.get("title") or row.get("label") or row.get("name") or "")
		photo = str(row.get("photo") or row.get("image") or "") or names.get(_plain(label), "")
		if not _plain(label) or not photo:
			return None
		parts.append((label, styles, photo, str(row.get("url") or row.get("href") or "")))
	return parts


def _wheel_children(parts: list, hub_image: str) -> list:
	"""The parts of the circle, and the mark in the middle when the site has one."""
	count = len(parts)
	children = []
	for index, (label, styles, photo, href) in enumerate(parts):
		# the picture is pushed the other way, so its middle — where the subject is — lands inside the
		# part: framed towards the part, the top one showed the sky of its photograph (2026-09-15)
		frame_x, frame_y = _wheel_point(index + 0.5, count, -26)
		label_x, label_y = _wheel_point(index + 0.5, count, 33)
		children.append({
			"blockId": uuid.uuid4().hex[:10],
			"element": "a",
			"blockName": "wheel-part",
			"attributes": {"href": href} if href else {},
			"baseStyles": {
				"position": "absolute", "top": "0", "left": "0", "right": "0", "bottom": "0",
				"borderRadius": "50%", "clipPath": _wheel_slice_path(index, count),
				"backgroundImage": f"url({photo})", "backgroundSize": "cover",
				# each photograph is framed towards its own part, not towards the middle of the picture
				"backgroundPosition": f"{frame_x:.0f}% {frame_y:.0f}%",
				"textDecoration": "none",
				# the veil the words are read on, without a layer of its own
				"boxShadow": "inset 0 0 0 9999px rgba(0, 0, 0, 0.32)",
			},
			"children": [{
				"blockId": uuid.uuid4().hex[:10],
				"element": "span",
				"blockName": "wheel-label",
				"innerHTML": label,
				"baseStyles": {
					"position": "absolute", "left": f"{label_x:.2f}%", "top": f"{label_y:.2f}%",
					"transform": "translate(-50%, -50%)", "color": "#ffffff",
					"fontFamily": styles.get("fontFamily") or "inherit",
					"fontWeight": styles.get("fontWeight") or "700",
					"fontSize": "clamp(0.72rem, 0.5rem + 1.1vw, 1rem)",
					"letterSpacing": "0.1em", "textTransform": "uppercase", "whiteSpace": "nowrap",
					"textShadow": "0 2px 14px rgba(0, 0, 0, 0.7)", "pointerEvents": "none",
					# the Builder paints text with its block's picture (`.__text_block__ > *` inherits
					# background-image, for lettering cut out of a photograph): the words of a part
					# would carry the part's photograph as a dark patch behind them (2026-09-15)
					"backgroundImage": "none", "backgroundClip": "border-box",
				},
				"children": [],
			}],
		})
	if hub_image:
		children.append({
			"blockId": uuid.uuid4().hex[:10],
			"element": "div",
			"blockName": "wheel-hub",
			"baseStyles": {
				"position": "absolute", "left": "50%", "top": "50%", "width": "31%", "aspectRatio": "1",
				"transform": "translate(-50%, -50%)", "borderRadius": "50%", "background": "#ffffff",
				"display": "grid", "placeItems": "center", "boxShadow": "0 8px 28px rgba(0, 0, 0, 0.22)",
			},
			"children": [{
				"blockId": uuid.uuid4().hex[:10],
				"element": "img",
				"blockName": "wheel-mark",
				"attributes": {"src": hub_image, "alt": "", "loading": "lazy"},
				"baseStyles": {"width": "74%", "height": "auto", "display": "block"},
				"children": [],
			}],
		})
	return children


def _wheel_container(grid: dict) -> None:
	"""The grid becomes the circle: its rows and columns go, its box turns round."""
	base = grid.setdefault("baseStyles", {})
	for key in ("display", "gridAutoFlow", "alignItems", "justifyItems", *GRID_STYLE_KEYS):
		base.pop(key, None)
	for field in ("mobileStyles", "tabletStyles", "rawStyles"):
		styles = grid.get(field) or {}
		for key in ("display", "gridAutoFlow", *GRID_STYLE_KEYS):
			styles.pop(key, None)
	grid["classes"] = [c for c in (grid.get("classes") or []) if not c.startswith("u-grid")]
	# the parts are drawn one by one: nothing is cloned over rows any more
	grid.pop("isRepeaterBlock", None)
	grid.pop("dataKey", None)
	base.update({
		# the circle is the piece of the section, not a medallion in a corner
		"position": "relative", "width": "min(720px, 100%)", "aspectRatio": "1",
		"marginLeft": "auto", "marginRight": "auto", "borderRadius": "50%",
		"overflow": "hidden", "background": "#ffffff",
	})


def category_wheel(blocks: list, category_photos: dict, hub_image: str = "", data_rows: dict | None = None) -> int:
	"""The grid of category tiles, drawn as one circle cut into as many parts, each on its own
	photograph. The words and the links are kept, whether the page wrote the tiles one by one or
	clones one template over its data (repeater_rows). One grid per page — the one whose tiles are all
	named after a category, else the first that can be drawn. Returns 1 when one was turned."""
	names = {_plain(name): url for name, url in (category_photos or {}).items() if _plain(name)}
	candidates = []
	for grid in _walk(blocks):
		if not _is_grid(grid):
			continue
		tiles = [c for c in grid.get("children") or [] if isinstance(c, dict)]
		parts, named = None, False
		# one template cloned over the page's rows: the rows are the parts. The repeater may BE the
		# grid — unwrap_grid_wrappers hands it the columns so its clones are the items — or sit in it.
		holder = grid if _is_repeater(grid) else (tiles[0] if len(tiles) == 1 and tiles and _is_repeater(tiles[0]) else None)
		if holder is not None:
			rows = (data_rows or {}).get(str((holder.get("dataKey") or {}).get("key") or ""))
			template = tiles[0] if holder is grid and tiles else holder
			if rows and WHEEL_MIN <= len(rows) <= WHEEL_MAX:
				parts = _rows_parts(rows, names, template)
				named = True
		elif WHEEL_MIN <= len(tiles) <= WHEEL_MAX:
			parts = _wheel_parts(tiles, names)
			named = bool(names) and all(_tile_category(t, names) for t in tiles)
		if parts is None:
			continue
		candidates.append((named, grid, parts))
	if not candidates:
		return 0
	_named, grid, parts = next((c for c in candidates if c[0]), candidates[0])
	labels = {_plain(label) for label, _styles, _photo, _url in parts}
	grid["children"] = _wheel_children(parts, hub_image)
	_wheel_container(grid)
	_clear_around_the_wheel(blocks, grid, labels)
	return 1


def _decoration(block: dict) -> bool:
	"""A box drawn for the eye alone and as large as the circle: no words, no picture, no children."""
	if block.get("children") or _plain(block.get("innerHTML") or "") or _tile_photo(block):
		return False
	styles = block.get("baseStyles") or {}
	sizes = [str(styles.get(key) or "") for key in ("width", "height", "minHeight")]
	return any(re.match(r"^\s*([3-9]\d{2}|\d{4,})px", value) or re.match(r"^\s*([4-9]\d|100)v[wh]", value) for value in sizes)


def _clear_around_the_wheel(blocks: list, wheel: dict, labels: set) -> None:
	"""What the circle now says, said a second time beside it, goes.

	A page that composes the categories itself draws the same idea twice: a large empty circle
	behind, a ring of the category names around it, and the tiles this pass turns into the circle
	(2026-09-15). The names are on the parts, and the circle is the drawing: the decoration and the
	ring of names are removed from the section the wheel sits in."""
	parents = {}
	stack = [(b, None) for b in blocks if isinstance(b, dict)]
	while stack:
		node, parent = stack.pop()
		parents[id(node)] = parent
		for child in node.get("children") or []:
			if isinstance(child, dict):
				stack.append((child, node))
	section, node = None, wheel
	while node is not None:
		parent = parents.get(id(node))
		if parent is not None and str(parent.get("element") or "").lower() == "section":
			section = parent
			break
		node = parent
	section = section or parents.get(id(wheel))
	if section is None:
		return
	inside = {id(block) for block in _walk([wheel])}
	for parent in _walk([section]):
		# the parts of the circle carry the names: nothing is cleared inside it
		if id(parent) in inside:
			continue
		kept = []
		for child in parent.get("children") or []:
			if not isinstance(child, dict) or child is wheel or any(wheel is b for b in _walk([child])):
				kept.append(child)
				continue
			words = {_plain(t["innerHTML"]) for t in _texts(child)}
			ring = bool(words) and words <= labels and not _tile_photo(child)
			if _decoration(child) or ring:
				continue
			kept.append(child)
		parent["children"] = kept



# //// Neoffice ▼▼▼ — added (2026-09-15): one photograph, one place on a page.
def one_photo_once(blocks: list, photos: list[str]) -> list[str]:
    """A client photograph shown twice on the same page takes an unused one instead.

    The brief says each photograph is used at most once; a home opened on a skateboarder and
    showed the same skateboarder again, three sections down, beside its two-column statement
    (2026-09-15). Walked in reading order: the first showing keeps the picture, and a later one
    takes the first photograph of the page's own list that nothing shows yet. With none left the
    repeat stays — a duplicate reads better than an empty frame. Returns one line per swap."""
    spare = [url for url in (photos or []) if url]
    seen: set[str] = set()
    swaps: list[str] = []

    def replace(block: dict, old: str, new: str) -> None:
        if block.get("element") == "img":
            attributes = block.setdefault("attributes", {})
            if str(attributes.get("src") or "") == old:
                attributes["src"] = new
        styles = block.get("baseStyles") or {}
        background = str(styles.get("backgroundImage") or "")
        if old in background:
            styles["backgroundImage"] = background.replace(old, new)
            block["baseStyles"] = styles

    def walk(block) -> None:
        if not isinstance(block, dict):
            return
        for url in _photos_of(block):
            if url not in seen:
                seen.add(url)
                continue
            fresh = next((u for u in spare if u not in seen), None)
            if not fresh:
                continue
            replace(block, url, fresh)
            seen.add(fresh)
            swaps.append(f"a photograph shown twice replaced by {fresh.rsplit('/', 1)[-1]}")
        for child in block.get("children") or []:
            walk(child)

    for block in blocks or []:
        walk(block)
    return swaps


def _photos_of(block: dict) -> list[str]:
    """The photographs this block itself shows (not its children's)."""
    found = []
    if block.get("element") == "img":
        src = str((block.get("attributes") or {}).get("src") or "")
        if src and not src.startswith("data:"):
            found.append(src)
    m = URL_IN_BACKGROUND.search(str((block.get("baseStyles") or {}).get("backgroundImage") or ""))
    if m and not m.group(2).startswith("data:"):
        found.append(m.group(2))
    return found
# //// Neoffice ▲▲▲


# //// Neoffice ▼▼▼ — added (2026-09-15): the emblem is an ornament or it is nothing.
MARK_MIN_PX = 200


def drop_small_marks(blocks: list, mark: str) -> list[str]:
    """Removes the site's emblem where it was drawn small: a bullet, an icon beside a heading.

    The page brief offers the mark as a background layer, at least 280px across. Offered that,
    the model put a 30px copy of it in front of every section title, where it reads as a stray
    favicon (2026-09-15). A picture whose declared size is under MARK_MIN_PX, or which declares
    none at all, is not an ornament: it goes. One kept large enough stays. Returns one line per
    removal."""
    if not mark:
        return []
    removed: list[str] = []

    def size(block: dict) -> float:
        styles = {**(block.get("baseStyles") or {}), **(block.get("attributes") or {})}
        found = 0.0
        for key in ("width", "height", "maxWidth", "minWidth"):
            m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*(px)?\s*$", str(styles.get(key) or ""))
            if m:
                found = max(found, float(m.group(1)))
        return found

    def walk(parent: dict) -> None:
        kids = [c for c in parent.get("children") or [] if isinstance(c, dict)]
        kept = []
        for child in kids:
            src = str((child.get("attributes") or {}).get("src") or "")
            if child.get("element") == "img" and src == mark and size(child) < MARK_MIN_PX:
                removed.append(f"the emblem drawn at {int(size(child)) or 'no'}px was removed")
                continue
            kept.append(child)
            walk(child)
        if len(kept) != len(kids):
            parent["children"] = kept

    for block in blocks or []:
        if isinstance(block, dict):
            walk(block)
    return removed
# //// Neoffice ▲▲▲
