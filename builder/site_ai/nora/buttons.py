# //// Neoffice — added file (no upstream equivalent).
"""Buttons and calls to action the model leaves broken.

Three defects seen on one build (2026-09-10): a primary button on a section
painted in the primary colour (a label floating with no button around it), a
"Learn more" that was a bare span going nowhere, and a card without the action its
two siblings carried. None is left to the model: the variant is checked against
the section behind the button, a call-to-action text without a link becomes one,
and the cards of a grid all get the action of their siblings.
"""

import copy
import re
import secrets

from builder.site_ai.nora.contrast import Color, contrast, parse_color

# a button must stand out from what it sits on; text-level contrast is not needed
BUTTON_MIN_RATIO = 1.8

CTA_TEXT = re.compile(
    r"^(en savoir plus|d[ée]couvrir(?: .{0,30})?|voir(?: .{0,30})?|se connecter|acc[ée]der(?: .{0,30})?"
    r"|demander(?: .{0,40})?|contactez(?:-nous)?|nous contacter|rejoindre(?: .{0,30})?|commander(?: .{0,30})?"
    r"|learn more|discover(?: .{0,30})?|see (?:more|all|the .{0,25})|sign in|log in|get in touch|contact us"
    r"|request(?: .{0,30})?|join(?: .{0,30})?|explore(?: .{0,30})?)\s*[›»→>]*\s*$",
    re.I,
)
TAG = re.compile(r"<[^>]+>")

# what a call to action talks about, and the route that answers it: first match wins
TARGETS = [
    (re.compile(r"connect|connexion|login|log in|sign in", re.I), ("login",)),
    (re.compile(r"compte|account|revendeur|reseller|dealer|partenaire|partner|r[ée]seau|network|rejoin|join", re.I), ("revendeur", "reseller", "partner", "partenaire", "compte", "account")),
    (re.compile(r"marque|brand", re.I), ("marque", "brand")),
    (re.compile(r"catalogue|catalog|produit|product|boutique|shop|collection|commander|order", re.I), ("all-products", "produit", "product", "boutique", "shop", "catalogue")),
    (re.compile(r"contact|devis|quote|rendez-vous|appointment", re.I), ("contact",)),
    (re.compile(r"agence|agency|propos|about|[ée]quipe|team|histoire|story", re.I), ("propos", "about", "equipe", "team")),
    (re.compile(r"service|prestation|offre|offer", re.I), ("service", "prestation", "offre")),
    (re.compile(r"blog|actualit|news|article", re.I), ("blog", "actualite", "news")),
]


def _text(block: dict) -> str:
    return " ".join(TAG.sub(" ", str(block.get("innerHTML") or "")).split())


def _role(palette: dict, role: str) -> Color | None:
    for key, value in palette.items():
        if key == role or key.endswith("-" + role):
            return parse_color(value, palette)
    return None


def _background(block: dict, palette: dict, inherited: Color | None) -> Color | None:
    styles = block.get("baseStyles") or {}
    for key in ("backgroundColor", "background"):
        parsed = parse_color(styles.get(key), palette)
        if parsed is not None:
            return parsed
    return inherited


def _over_photo(block: dict, inherited: bool) -> bool:
    """Whether a block's content sits on a photograph: a section over an image (its class, a
    background picture, a photograph laid across it), unless the block paints its own colour."""
    styles = block.get("baseStyles") or {}
    classes = block.get("classes") or []
    if any(str(c).startswith("u-over-image") for c in classes) or "url(" in str(styles.get("backgroundImage") or styles.get("background") or ""):
        return True
    for child in block.get("children") or []:
        if isinstance(child, dict) and (child.get("element") or "").lower() == "img" and (child.get("baseStyles") or {}).get("position") == "absolute":
            return True
    if str(styles.get("backgroundColor") or "").strip().lower() not in ("", "transparent", "none"):
        return False
    return inherited


def _hex(colour: Color | None) -> str | None:
    if colour is None:
        return None
    return "#" + "".join(f"{max(0, min(255, round(channel))):02x}" for channel in colour[:3])


def rendered_buttons(palette: dict) -> tuple[Color | None, Color | None]:
    """The colours the theme paints the two buttons with (header_footer.button_colours): the
    page's action colour for the primary, and for the secondary its fill, or None when the
    theme draws it as an outline. Judged on the raw palette, the pass swapped a primary
    button the theme was already painting in the readable secondary (a site whose primary is
    its own background), and missed one painted in that colour on a section of the same
    colour (2026-09-13)."""
    primary, secondary = _role(palette, "primary"), _role(palette, "secondary")
    try:
        from builder.hf_utils.header_footer import button_colours
    except ImportError:
        # an edition without the site chrome paints the palette as it is
        return primary, secondary
    theme = {f"{role}_color": _hex(_role(palette, role)) for role in ("primary", "secondary", "background", "text")}
    colours = button_colours(theme)
    painted = parse_color(colours.get("cta_hex"), palette) or primary
    fill = colours.get("secondary_button")
    if fill is None:
        return painted, None
    return painted, secondary if str(fill).startswith("var(") else parse_color(fill, palette)


def repair_button_variants(blocks: list, palette: dict) -> list[str]:
    """A u-btn--primary on a background of the colour the theme paints it with becomes
    secondary (or outline), and a u-btn--secondary on a background of its own fill becomes
    primary (or outline). An outlined secondary reads everywhere and is left alone. The
    colours are the ones the page will show (rendered_buttons), not the raw palette."""
    primary, secondary = rendered_buttons(palette)
    default_bg = _role(palette, "background") or (255.0, 255.0, 255.0, 1.0)
    edits: list[str] = []

    def walk(block: dict, bg: Color | None, photo: bool = False) -> None:
        photo = _over_photo(block, photo)
        bg = _background(block, palette, bg)
        classes = list(block.get("classes") or [])
        # an outline over a photograph reads on none of it: the design system's own backing (the
        # ghost "Contact us" of a photo hero was a dark outline on a dark picture, 2026-09-12)
        if photo and "u-btn" in classes and {"u-btn--outline", "u-btn--ghost"} & set(classes):
            block["classes"] = classes = ["u-btn--on-image" if c in ("u-btn--outline", "u-btn--ghost") else c for c in classes]
            edits.append(f"'{_text(block)}': an outline button over a photograph -> u-btn--on-image")
        for variant, colour, other, other_name in (("u-btn--primary", primary, secondary, "u-btn--secondary"), ("u-btn--secondary", secondary, primary, "u-btn--primary")):
            if variant in classes and colour is not None and bg is not None and contrast(colour, bg) < BUTTON_MIN_RATIO:
                new = other_name if other is not None and contrast(other, bg) >= BUTTON_MIN_RATIO else "u-btn--outline"
                block["classes"] = [new if c == variant else c for c in classes]
                edits.append(f"'{_text(block)}': {variant} on its own colour -> {new}")
                break
        for child in block.get("children") or []:
            walk(child, bg, photo)

    for block in blocks:
        walk(block, default_bg)

    # one main action per group: two buttons side by side in the same filled variant
    # read as two equal actions, so the second and the next ones step back to outline
    def demote_siblings(block: dict) -> None:
        buttons = [c for c in block.get("children") or [] if "u-btn" in (c.get("classes") or [])]
        for variant in ("u-btn--primary", "u-btn--secondary"):
            same = [b for b in buttons if variant in (b.get("classes") or [])]
            for extra in same[1:]:
                extra["classes"] = ["u-btn--outline" if c == variant else c for c in extra["classes"]]
                edits.append(f"'{_text(extra)}': a second {variant} beside the first -> u-btn--outline")
        for child in block.get("children") or []:
            demote_siblings(child)

    for block in blocks:
        demote_siblings(block)
    return edits


def settle_rendered_variants(blocks: list, palette: dict) -> int:
    """In place, at render: each u-btn--primary or u-btn--secondary whose painted colour does not
    stand out from the section behind it steps to the other filled variant when that one does
    and no button beside it wears it already, else to the outline. The render's half of
    repair_button_variants, without its design choices (one main action per group, the variant
    over a photograph): the page keeps the variant its author chose, and a theme that changes
    after the page was written (a retheme, a new rule for what the buttons paint) is judged at
    each render. A button over a photograph keeps its variant. Returns how many changed."""
    primary, secondary = rendered_buttons(palette)
    painted = {"u-btn--primary": primary, "u-btn--secondary": secondary}
    changed = 0

    def settle(button: dict, row: list, bg: Color) -> bool:
        classes = list(button.get("classes") or [])
        for variant, other in (("u-btn--primary", "u-btn--secondary"), ("u-btn--secondary", "u-btn--primary")):
            colour = painted[variant]
            if variant not in classes or colour is None or contrast(colour, bg) >= BUTTON_MIN_RATIO:
                continue
            fill = painted[other]
            taken = any(other in (sibling.get("classes") or []) for sibling in row if sibling is not button)
            new = other if fill is not None and not taken and contrast(fill, bg) >= BUTTON_MIN_RATIO else "u-btn--outline"
            button["classes"] = [new if c == variant else c for c in classes]
            return True
        return False

    def walk(block: dict, bg: Color, photo: bool) -> None:
        nonlocal changed
        photo = _over_photo(block, photo)
        bg = _background(block, palette, bg)
        row = [child for child in block.get("children") or [] if isinstance(child, dict)]
        for child in row:
            if "u-btn" in (child.get("classes") or []) and not _over_photo(child, photo) and settle(child, row, bg):
                changed += 1
            walk(child, bg, photo)

    page = _role(palette, "background") or (255.0, 255.0, 255.0, 1.0)
    for block in blocks:
        if isinstance(block, dict):
            walk(block, page, False)
    return changed


def _render_palette() -> dict | None:
    """The colours of this render, keyed as the repair reads them: the four roles from the
    chrome's theme (the site's own variant, as theme_variables.html gets it) first, then every
    Builder Token and the chrome's own variables, so that a section's var(--…) resolves. None
    when the page has no chrome theme (an offline site, a bench without the config)."""
    from builder.builder.doctype.builder_token.builder_token import get_css_variables
    from builder.hf_utils.header_footer import get_header_footer_config

    config = get_header_footer_config()
    theme = config.get_theme_data() if config else None
    if not theme:
        return None
    roles = [role for role in ("primary", "secondary", "background", "text") if theme.get(f"{role}_color")]
    # the bare role names come first: _role() takes the first key naming the role, and the
    # tokens of every site of the instance (nt2-primary, nt3-primary…) name it as well
    palette = {role: theme[f"{role}_color"] for role in roles}
    tokens, _dark = get_css_variables()
    palette.update({name.removeprefix("--"): value for name, value in (tokens or {}).items()})
    palette.update({f"{role}-color": theme[f"{role}_color"] for role in roles})
    return palette


def settle_for_render(blocks):
    """The blocks a page renders, each filled button in the variant that reads on its section
    with the theme of this render (settle_rendered_variants). `blocks` as stored (JSON text) or
    parsed; returned untouched when nothing changes, and on any error: this runs on every page
    view and must never be the reason a page fails."""
    if not blocks or (isinstance(blocks, str) and "u-btn--" not in blocks):
        return blocks
    import frappe

    try:
        palette = _render_palette()
        if not palette:
            return blocks
        data = frappe.parse_json(blocks) if isinstance(blocks, str) else copy.deepcopy(blocks)
        return data if settle_rendered_variants(data if isinstance(data, list) else [data], palette) else blocks
    except Exception:
        frappe.log_error("Buttons: page rendered without the variant check", frappe.get_traceback())
        return blocks


def guess_target(text: str, routes: list[str], fallback: str) -> str:
    """The route a call to action most likely means, from its words and its card's."""
    for pattern, needles in TARGETS:
        if not pattern.search(text):
            continue
        for needle in needles:
            for route in routes:
                if needle in route.lower():
                    return route
    return fallback


def repair_foreign_links(blocks: list, routes: list[str], fallback: str, categories: list[str] | None = None, listing: str | None = None) -> list[str]:
    """A link to a route that is not this site's (another site of the instance, a page
    the model invented) goes to the page of this site its words mean, or to the site's
    call to action. Files, assets, anchors and external addresses are left alone.

    A link named after one of the categories the brief lists (a tile "Snow" to /snow, a
    page the site does not have) goes to `listing`, the page that shows what the site
    offers, when there is one: the five category tiles of a new site all led to the
    contact form (2026-09-11)."""
    known = {r.rstrip("/") or "/" for r in routes}
    category_keys = {c.strip().lower() for c in categories or [] if c.strip()}
    edits: list[str] = []

    def walk(block: dict, card_text: str) -> None:
        attrs = block.get("attributes") or {}
        href = str(attrs.get("href") or "")
        if href.startswith("/") and not href.startswith(("/files", "/assets", "/api", "/private", "//")):
            path = href.split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"
            if path not in known:
                words = " ".join(part for part in (_text(block), path.replace("-", " ").replace("/", " "), card_text) if part)
                # a category as the link says it or as its path spells it: "/snow", "/home-burrow",
                # and "/culture/snow", which the seventh build's tiles linked to (2026-09-12)
                named = {(_text(block) or "").strip().lower(), path.strip("/").replace("-", " ").lower()}
                named |= set(re.split(r"[/\s_-]+", path.strip("/").lower()))
                target = listing if listing and named & category_keys else guess_target(words, routes, fallback)
                block["attributes"] = dict(attrs, href=target)
                edits.append(f"'{_text(block)}' {href} -> {target}")
        heading = _heading(block) if (block.get("element") or "").lower() != "a" else ""
        context = " ".join(part for part in (heading, card_text) if part)
        for child in block.get("children") or []:
            walk(child, context)

    for block in blocks:
        walk(block, "")
    return edits


HREF_IN_HTML = re.compile(r"""href=(["'])(/[^"'#?]*)([^"']*)\1""")
DATA_ROUTE_KEYS = ("route", "href", "url", "link")


def _href_keys(blocks: list) -> set[str]:
    """The data keys a page binds to a link's href: a tile's `slug`, `route`, `url`..."""
    keys: set[str] = set()

    def walk(block: dict) -> None:
        for dv in block.get("dynamicValues") or []:
            if isinstance(dv, dict) and dv.get("property") == "href" and dv.get("key"):
                keys.add(str(dv["key"]).split(".")[-1])
        for child in block.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    for block in blocks or []:
        if isinstance(block, dict):
            walk(block)
    return keys


def repair_data_routes(
    script: str,
    routes: list[str],
    fallback: str,
    categories: list[str] | None = None,
    listing: str | None = None,
    blocks: list | None = None,
) -> tuple[str, list[str]]:
    """The routes a page's data script hands to its repeated blocks go through the same
    check as the links written in the blocks: category tiles bound to "/snow", a page the
    site does not have, led nowhere once their binding worked (2026-09-12). A category's
    route goes to `listing`, anything else to the page its words mean or to `fallback`.

    The keys checked are the usual link names and every key the page binds to an href:
    the tiles of one build linked through a key named `slug` ("/snow", "/home-burrow")."""
    if not script:
        return script, []
    keys = set(DATA_ROUTE_KEYS) | _href_keys(blocks or [])
    names = "|".join(re.escape(k) for k in sorted(keys))
    pattern = re.compile(rf"""(["'](?:{names})["']\s*:\s*["'])(/[^"'#?\s]*)([^"'\s]*)(["'])""")
    known = {r.rstrip("/") or "/" for r in routes}
    category_keys = {c.strip().lower() for c in categories or [] if c.strip()}
    edits: list[str] = []

    def swap(m: re.Match) -> str:
        path = m.group(2).rstrip("/") or "/"
        if path in known or path.startswith(("/files", "/assets", "/api", "/private")):
            return m.group(0)
        slug = path.strip("/").replace("-", " ").lower()
        # the path's words: "/culture/snow" names Snow as much as "/snow" does
        named = slug in category_keys or bool(set(re.split(r"[/\s_]+", slug)) & category_keys)
        target = listing if listing and named else guess_target(slug, routes, fallback)
        edits.append(f"{m.group(2)} -> {target}")
        return f"{m.group(1)}{target}{m.group(3)}{m.group(4)}"

    return pattern.sub(swap, script), edits


def remap_routes(blocks: list, moved: dict[str, str]) -> list[str]:
    """Point links at the routes their pages really got (`moved`: planned -> real).

    A page written beside a kept page that holds its planned route is suffixed at write
    time, after the model, the call to action and the link repairs have all used the
    planned route: every "Contact us" of a new site led to the contact page it was built
    beside (2026-09-11). Only exact paths move, with the anchor or query they carry, and
    a link inside rich text moves like a link block."""
    edits: list[str] = []

    def moved_href(href: str) -> str | None:
        match = re.match(r"^(/[^?#]*)(.*)$", href)
        if not match:
            return None
        path = match.group(1).rstrip("/") or "/"
        return moved[path] + match.group(2) if path in moved else None

    def swap(m: re.Match) -> str:
        new = moved_href(m.group(2) + m.group(3))
        if not new:
            return m.group(0)
        edits.append(f"{m.group(2)}{m.group(3)} -> {new}")
        return f"href={m.group(1)}{new}{m.group(1)}"

    def walk(block: dict) -> None:
        attrs = block.get("attributes") or {}
        href = str(attrs.get("href") or "")
        target = moved_href(href) if href.startswith("/") else None
        if target:
            block["attributes"] = dict(attrs, href=target)
            edits.append(f"{href} -> {target}")
        html = block.get("innerHTML")
        if isinstance(html, str) and "href=" in html:
            block["innerHTML"] = HREF_IN_HTML.sub(swap, html)
        for child in block.get("children") or []:
            walk(child)

    for block in blocks:
        walk(block)
    return edits


def _new_id() -> str:
    return secrets.token_hex(5)[:9]


def _reidentify(block: dict) -> dict:
    clone = copy.deepcopy(block)

    def walk(b: dict) -> None:
        b["blockId"] = _new_id()
        for c in b.get("children") or []:
            walk(c)

    walk(clone)
    return clone


def _action_leaf(block: dict) -> dict | None:
    """The call-to-action link a card ends with, if any."""
    found = None

    def walk(b: dict) -> None:
        nonlocal found
        if (b.get("element") or "").lower() == "a" and CTA_TEXT.match(_text(b)):
            found = b
        for c in b.get("children") or []:
            walk(c)

    walk(block)
    return found


def _heading(block: dict) -> str:
    for child in block.get("children") or []:
        if (child.get("element") or "").lower() in ("h2", "h3", "h4"):
            return _text(child)
        deeper = _heading(child)
        if deeper:
            return deeper
    return ""


def wire_dead_ctas(blocks: list, routes: list[str], fallback: str) -> list[str]:
    """A call-to-action text that is not a link becomes one, and every card of a grid
    gets the action its siblings carry. Returns one line per edit."""
    edits: list[str] = []

    def walk(block: dict, inside_link: bool, card_text: str) -> None:
        element = (block.get("element") or "").lower()
        children = block.get("children") or []
        text = _text(block)
        if not children and not inside_link and element in ("span", "div", "p", "button") and text and CTA_TEXT.match(text):
            attrs = dict(block.get("attributes") or {})
            if not attrs.get("href"):
                target = guess_target(text + " " + card_text, routes, fallback)
                block["element"] = "a"
                attrs["href"] = target
                block["attributes"] = attrs
                edits.append(f"'{text}' -> {target}")
        # the words that say what the link means: the card's heading, then the section's
        heading = _heading(block) if element != "a" else ""
        context = " ".join(part for part in (heading, card_text) if part)
        for child in children:
            walk(child, inside_link or element == "a", context)

    for block in blocks:
        walk(block, False, "")

    def equalize(block: dict) -> None:
        classes = block.get("classes") or []
        cards = block.get("children") or []
        if any(c == "u-grid" or c.startswith("u-grid--") for c in classes) and len(cards) > 1:
            actions = [(card, _action_leaf(card)) for card in cards]
            model = next((leaf for _, leaf in actions if leaf is not None), None)
            if model is not None:
                model_href = (model.get("attributes") or {}).get("href") or fallback
                for card, leaf in actions:
                    if leaf is None and card.get("children") is not None:
                        clone = _reidentify(model)
                        clone["attributes"] = dict(clone.get("attributes") or {})
                        # the card's own words first; when they say nothing, the siblings' destination
                        guessed = guess_target(_text(model) + " " + _heading(card), routes, fallback)
                        clone["attributes"]["href"] = guessed if guessed != fallback else model_href
                        card["children"].append(clone)
                        edits.append(f"card '{_heading(card)}' gets '{_text(model)}' -> {clone['attributes']['href']}")
        for child in cards:
            equalize(child)

    for block in blocks:
        equalize(block)
    return edits


CONTACT_FORM_ANCHOR = "contact-form"


def retarget_self_links(blocks: list, own_route: str, fallback: str) -> list[str]:
    """A call to action never leads to the page it is on. The Contact page of a monochrome
    build closed on "Start a conversation" and a "Contact us" button to itself, under its
    own form (2026-09-13). On a page that carries the contact form, such a button goes to
    the form, which gets the anchor; on another page, an invitation ("Discover", "See the
    brands") goes to the site's call to action. Returns one line per edit."""
    route = str(own_route or "").strip("/")
    own = "/" if route in ("", "home", "index") else f"/{route}"
    form = _include_block(blocks, "contact_form.html")
    edits: list[str] = []

    def walk(block: dict) -> None:
        attrs = block.get("attributes") or {}
        href = str(attrs.get("href") or "")
        text = _text(block)
        if href.startswith("/") and "#" not in href and (href.split("?", 1)[0].rstrip("/") or "/") == own:
            target = None
            if form is not None and ("u-btn" in (block.get("classes") or []) or CTA_TEXT.match(text)):
                anchor = (form.get("attributes") or {}).get("id") or CONTACT_FORM_ANCHOR
                form["attributes"] = {**(form.get("attributes") or {}), "id": anchor}
                # a sticky header does not cover the form it scrolls to
                form["baseStyles"] = {**(form.get("baseStyles") or {}), "scrollMarginTop": "calc(var(--header-height, 72px) + 16px)"}
                target = f"#{anchor}"
            elif CTA_TEXT.match(text) and fallback and (fallback.rstrip("/") or "/") != own:
                target = fallback
            if target:
                block["attributes"] = {**attrs, "href": target}
                edits.append(f"'{text}' {href} -> {target}")
        for child in block.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    for block in blocks:
        if isinstance(block, dict):
            walk(block)
    return edits


def drop_closing_band(blocks: list, own_route: str) -> list[str]:
    """On the page the site's call to action leads to, a closing band whose every link leads back
    to the page itself goes. Told that this page carries none, a contact page still closed on
    "Vous avez une question ? Voir le formulaire", a band under its own form sending the visitor
    back up (2026-09-13). Only the page's last section, and only a short one with no form,
    include or field: the band, never content. Returns the heading of what went."""
    route = str(own_route or "").strip("/")
    own = "/" if route in ("", "home", "index") else f"/{route}"
    top = [b for b in blocks or [] if isinstance(b, dict)]
    sections = top[0]["children"] if len(top) == 1 and top[0].get("children") else top
    if not sections or not isinstance(sections[-1], dict):
        return []
    links: list[str] = []
    state = {"words": 0, "fields": False, "heading": ""}

    def walk(block: dict) -> None:
        element = (block.get("element") or "").lower()
        if "{%" in str(block.get("innerHTML") or "") or element in ("form", "input", "textarea", "select", "iframe"):
            state["fields"] = True
        if element in ("h1", "h2", "h3", "h4", "h5", "h6") and not state["heading"]:
            state["heading"] = _text(block)
        href = str((block.get("attributes") or {}).get("href") or "")
        if href:
            links.append(href)
        state["words"] += len(_text(block).split())
        for child in block.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    def to_itself(href: str) -> bool:
        path = href.split("#", 1)[0].split("?", 1)[0].rstrip("/") or "/"
        return href.startswith("#") or (href.startswith("/") and path == own)

    walk(sections[-1])
    if state["fields"] or not links or state["words"] > 60 or not all(to_itself(h) for h in links):
        return []
    sections.pop()
    return [state["heading"] or "the closing band"]


def _include_block(blocks: list, template: str) -> dict | None:
    """The block whose text includes `template` (the contact form, the map)."""
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        html = block.get("innerHTML")
        if isinstance(html, str) and "include" in html and template in html:
            return block
        found = _include_block(block.get("children") or [], template)
        if found is not None:
            return found
    return None
