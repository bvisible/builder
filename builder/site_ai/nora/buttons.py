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


def repair_button_variants(blocks: list, palette: dict) -> list[str]:
    """A u-btn--primary on a primary-coloured background becomes secondary (or outline),
    and a u-btn--secondary on a secondary-coloured one becomes primary (or outline)."""
    primary, secondary = _role(palette, "primary"), _role(palette, "secondary")
    default_bg = _role(palette, "background") or (255.0, 255.0, 255.0, 1.0)
    edits: list[str] = []

    def walk(block: dict, bg: Color | None) -> None:
        bg = _background(block, palette, bg)
        classes = list(block.get("classes") or [])
        for variant, colour, other, other_name in (("u-btn--primary", primary, secondary, "u-btn--secondary"), ("u-btn--secondary", secondary, primary, "u-btn--primary")):
            if variant in classes and colour is not None and bg is not None and contrast(colour, bg) < BUTTON_MIN_RATIO:
                new = other_name if other is not None and contrast(other, bg) >= BUTTON_MIN_RATIO else "u-btn--outline"
                block["classes"] = [new if c == variant else c for c in classes]
                edits.append(f"'{_text(block)}': {variant} on its own colour -> {new}")
                break
        for child in block.get("children") or []:
            walk(child, bg)

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
                named = {(_text(block) or "").strip().lower(), path.strip("/").replace("-", " ").lower()}
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
        named = slug in category_keys or bool(set(slug.split()) & category_keys)
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
