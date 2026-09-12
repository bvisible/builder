"""The site pipeline behind the generate_site tool.

Our orchestration (brief with design intelligence, design tokens, site chrome,
multi-profile scoping, menu, images) on upstream's page engine: every page is
YAML written by the heavy model under Prompts.GENERATION_YAML and expanded by
builder.ai.page_writer, so the result is a page the editor agent edits with
its own conventions. Runs inside the agent's turn (a server tool), reporting
progress on the chat channel and in the generation status cache.
"""

from __future__ import annotations

import json
import re
import unicodedata
import time
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import now

from builder.site_ai.nora.contrast import palette_roles

PLACEHOLDER = "https://placehold.co/{w}x{h}/e5e7eb/9ca3af/png?text={text}"

# title (lower, accents stripped) -> (route, page type)
KNOWN_PAGES = {
    "accueil": ("home", "accueil"), "home": ("home", "accueil"), "index": ("home", "accueil"),
    "a propos": ("about", "about"), "about": ("about", "about"), "qui sommes-nous": ("about", "about"),
    "services": ("services", "services"), "prestations": ("services", "services"),
    "contact": ("contact", "contact"),
    "faq": ("faq", "faq"),
    "equipe": ("team", "team"), "team": ("team", "team"),
    "blog": ("blog", "blog"), "articles": ("blog", "blog"), "actualites": ("blog", "blog"),
    "temoignages": ("testimonials", "testimonials"), "testimonials": ("testimonials", "testimonials"),
    "boutique": ("shop", "shop"), "shop": ("shop", "shop"), "produits": ("shop", "shop"),
    "tarifs": ("pricing", "pricing"), "pricing": ("pricing", "pricing"),
    "projets": ("projects", "portfolio"), "portfolio": ("projects", "portfolio"), "realisations": ("projects", "portfolio"),
    "fonctionnalites": ("features", "features"), "features": ("features", "features"),
}

SECTION_PLANS = {
    "accueil": [
        "hero: the site's promise in one line, a supporting sentence and the main CTA",
        "three or four value propositions with Lucide icons",
        "the featured services or products, one card each",
        "an about teaser with a photo and a link to the About page",
        "proof: testimonials, figures or partner logos",
        "a final CTA band",
    ],
    "about": ["the story and the mission", "values, three of them", "the team or the founder", "milestones or key figures", "a CTA"],
    "services": ["the services, one detailed card each", "how it works in three steps", "what is included / packages", "three FAQ entries", "a CTA"],
    "contact": [
        "the contact details from BUSINESS DATA, verbatim: address, phone, email, opening hours",
        "a contact form: name, email, message, one submit button",
        "directions or a map placeholder image",
        "a CTA to call or write",
    ],
    "faq": ["an intro line", "eight questions and answers grouped by theme", "a CTA to contact"],
    "team": ["an intro", "the team members as cards with photo placeholders", "a CTA to contact"],
    "blog": ["an intro", "three article teasers with placeholder photos and dates", "a newsletter or CTA band"],
    "testimonials": ["an intro", "six testimonials as cards", "a CTA"],
    "shop": ["an intro to the catalogue", "featured products with placeholders", "why buy here", "a CTA to the products list at /all-products"],
    "pricing": ["an intro", "three plans side by side with a highlighted one", "what is included", "FAQ", "a CTA"],
    "portfolio": ["an intro", "a project grid with placeholder photos", "the way of working", "a CTA"],
    "features": ["an intro", "the features as an alternating rows layout with icons", "a comparison or figures", "a CTA"],
    "one_page": ["hero", "services", "about", "proof", "contact details and form", "final CTA"],
    "generic": ["an intro", "the page's content in two or three sections", "a CTA"],
}

# //// Neoffice ▼▼▼ — an image-led site: the photographs carry the page and the copy steps
# //// back to names and a line. A brief saying "less is more", "not much text", "people
# //// consume through the image" still got the standard plan above: value propositions
# //// with icons, testimonials, an about teaser, every one of them a paragraph
# //// (2026-09-10). These plans build the same pages out of pictures.
IMAGE_LED_PLANS = {
    "accueil": [
        "hero: one full-bleed photograph, the site's name or promise in two to five words over it, one button",
        "the categories, segments or collections the activity names, one full-bleed photo tile each, its name only (one or two words) as the link",
        "one wide photograph with a single short line (at most twelve words)",
        "a closing band: one line and one button",
    ],
    "shop": ["the collections as full-bleed photo tiles, their name only", "a strip of products", "one line and a button"],
    "about": ["one large photograph and three short lines on who they are", "a strip of photographs", "one line and a button"],
    "contact": ["the contact details from BUSINESS DATA, verbatim, with no introduction", "a contact form: name, email, message, one submit button"],
    "generic": ["one large photograph with the page's point in one line", "the content as photo tiles with short captions", "one line and a button"],
}
# a page that is text by nature keeps its own plan whatever the density
TEXT_BY_NATURE = {"faq", "blog", "legal"}

# the words of a brief, or of the chosen direction, that ask for less copy
MINIMAL_COPY_WORDS = re.compile(
    r"less is more|not much text|little text|no text|almost no text|minimal (?:text|copy)|image[- ]led|"
    r"photo(?:graph)?[- ]first|through the image|peu de texte|moins de texte|pas (?:besoin )?d['’]autant de texte|par l['’]image",
    re.I,
)


def wants_minimal_copy(*texts) -> bool:
    """True when the brief asks for the pictures to carry the page and the copy to step back."""
    return any(MINIMAL_COPY_WORDS.search(str(t or "")) for t in texts)


def page_word_count(blocks: list) -> int:
    """The words a visitor reads on a page (headings, paragraphs, buttons), templates aside."""
    count = 0

    def walk(block: dict) -> None:
        nonlocal count
        text = re.sub(r"\{\{.*?\}\}|\{%.*?%\}|<[^>]+>", " ", str(block.get("innerHTML") or ""))
        count += len(re.findall(r"[^\W\d_]{2,}", text))
        for child in block.get("children") or []:
            walk(child)

    for block in blocks or []:
        walk(block)
    return count
# //// Neoffice ▲▲▲

CLASS_CONTRACT = (
    "set `classes` on the matching elements: buttons ['u-btn', 'u-btn--primary'] (or --secondary / --outline / --ghost), "
    "cards ['u-card'] (add 'u-card--raised' or 'u-card--flat'), photos and media frames ['u-media'], form fields ['u-input'], "
    "a wrapper that puts text over a photo ['u-over-image'] (add --bottom, --diagonal or --soft), a set of 2 to 4 equal items "
    "(cards, stats, steps, logos) in a container ['u-grid', 'u-grid--3'] (--2, --3 or --4) with NO gridTemplateColumns of its own: "
    "the site lays it out on every screen. These classes carry the site's corners, elevation, hover, motion and grids, so do not "
    "hand-write borderRadius, boxShadow, hover rules or the columns of such a set."
)

LAYOUT_BY_TONE = {
    "professional": "editorial-grid",
    "elegant": "split-screen",
    "bold": "poster-brutalist",
    "playful": "bento",
    "minimal": "classic-centered",
}


def _slug(text: str) -> str:
    text = frappe.utils.strip_html(text or "")
    text = "".join(c for c in __import__("unicodedata").normalize("NFKD", text) if not __import__("unicodedata").combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _bare(text: str) -> str:
    """lower-cased, accents stripped, punctuation trimmed: the lookup key of KNOWN_PAGES"""
    text = "".join(c for c in __import__("unicodedata").normalize("NFKD", text or "") if not __import__("unicodedata").combining(c))
    return re.sub(r"[^a-z0-9 -]+", "", text.lower()).strip()


NO_LOGO_WORDS = {"", "none", "null", "no", "non", "aucun", "aucune", "skip", "pas de logo"}


def clean_logo(value) -> str | None:
    """The logo argument as a path or URL, or None: the model answers "none" in words
    when the user skipped the logo, and a truthy "none" used to reach the brief as an
    image to analyse (neoffice-maintenance #296)."""
    text = str(value or "").strip()
    if text.lower() in NO_LOGO_WORDS:
        return None
    return text if text.startswith(("/", "http://", "https://", "data:")) else None


def pages_by_name(pages: list[dict], created: list[dict]) -> list[dict]:
    """The page specs (title, route, type) of the pages that were written, keyed later by
    the Builder Page name they got, so a revision pass can rebuild a page from its brief.

    A page is found by the route it was PLANNED under: one written beside a kept page that
    holds its route is suffixed ("about-d0ec"), and matching on that route left three
    pages of four out of the visual check's revision pass (2026-09-11)."""
    by_route = {p["route"]: p for p in pages}
    out = []
    for item in created:
        spec = by_route.get(item.get("planned") or "")
        spec = spec or by_route.get(item["route"].strip("/")) or by_route.get("home" if item["route"] in ("/", "/home") else item["route"].strip("/"))
        if spec:
            out.append({**spec, "name": item["name"]})
    return out


def pages_to_replace(classes: dict, replace_existing: str) -> list[str]:
    """The existing pages a build replaces: the untouched AI pages unless the user keeps
    everything ('none'), the hand-made ones too only when they said so ('force').

    'keep_edited' is what "keep them" means after a CONFIRM_NEEDED: the hand-made pages
    stay and the rest goes as usual. Answered with 'none', a question about one page kept
    the whole previous site beside the new one: two home pages, the new pages' routes
    suffixed, their calls to action on the old contact page (2026-09-11)."""
    if replace_existing == "none":
        return []
    names = [p["name"] for p in classes.get("untouched") or []]
    if replace_existing == "force":
        names += [p["name"] for p in classes.get("protected") or []]
    return names


def moved_routes(created: list[dict]) -> dict[str, str]:
    """Planned route -> the route the page really got, for the pages suffixed at write
    time because a kept page held their route. The home page answers for "/" as well."""
    moved: dict[str, str] = {}
    for item in created:
        planned = (item.get("planned") or "").strip("/")
        if not planned or f"/{planned}" == item["route"]:
            continue
        moved[f"/{planned}"] = item["route"]
        if planned in ("home", "index"):
            moved["/"] = item["route"]
    return moved


def _repoint_moved_links(created: list[dict], moved: dict[str, str]) -> dict[str, list[str]]:
    """Rewrite the new pages' links to the routes their targets really got. The stored
    fingerprint follows, or the page would read as edited by hand at the next build."""
    from builder.api import _blocks_fingerprint
    from builder.site_ai.nora.buttons import remap_routes

    edits: dict[str, list[str]] = {}
    for item in created:
        draft, published = frappe.db.get_value("Builder Page", item["name"], ["draft_blocks", "blocks"])
        changes = {}
        for field, raw in (("draft_blocks", draft), ("blocks", published)):
            try:
                blocks = json.loads(raw or "[]")
            except ValueError:
                continue
            done = remap_routes(blocks if isinstance(blocks, list) else [blocks], moved)
            if done:
                changes[field] = json.dumps(blocks)
                edits.setdefault(item["title"], []).extend(done)
        if changes:
            changes["ai_blocks_hash"] = _blocks_fingerprint(changes.get("draft_blocks") or draft or changes.get("blocks") or published)
            frappe.db.set_value("Builder Page", item["name"], changes, update_modified=False)
    return edits


def normalise_pages(pages: list, site_type: str) -> list[dict]:
    """Every page gets a route and a type; the home page comes first."""
    out, seen = [], set()
    for raw in pages or []:
        if isinstance(raw, str):
            raw = {"title": raw}
        title = (raw.get("title") or "").strip()
        if not title:
            continue
        known_route, ptype = KNOWN_PAGES.get(_bare(title), (None, None))
        # the home page keeps its canonical route whatever the model proposed: on the
        # B2C regeneration the model sent route "accueil" for Accueil, so the home
        # page lost its "home" route and everything keyed on it (the host page, the
        # profile's home_page, the hero brief). Every other page keeps the route the
        # model proposed (the French "a-propos" over the canonical "about"): forced to
        # the canonical one, the model "corrected" the routes after the build of The
        # League and renamed the open page, the home, to a-propos (2026-09-09)
        # //// Neoffice — see reasoning above; every page but home now keeps the model's proposed route instead of always falling back to the canonical one (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
        proposed = _slug(str(raw.get("route") or "").strip("/")) if raw.get("route") else ""
        route = "home" if known_route == "home" else (proposed or known_route or _slug(title))
        # the canonical type wins as well: with the model's own label ("form", "contact-page")
        # the Contact page of the B2B regeneration got no includes and no CTA link
        ptype = ptype or raw.get("type") or "generic"
        if site_type == "one_page" and route == "home":
            ptype = "one_page"
        if route in seen:
            continue
        seen.add(route)
        out.append({"title": title, "route": route, "type": ptype})
    if not out:
        from builder.api import DEFAULT_PAGES_BY_SITE_TYPE

        out = [dict(p) for p in DEFAULT_PAGES_BY_SITE_TYPE.get(site_type, DEFAULT_PAGES_BY_SITE_TYPE["vitrine"])]
    out.sort(key=lambda p: 0 if p["route"] == "home" else 1)
    return out


def token_prefix(name: str) -> str:
    words = [w for w in re.split(r"[^a-z0-9]+", _bare(name)) if w]
    if len(words) >= 2:
        prefix = "".join(w[0] for w in words)[:6]
    else:
        prefix = (words[0] if words else "site")[:8]
    return prefix or "site"


def choose_layout_system(style_direction: str, brief) -> str:
    s = (style_direction or "").lower()
    for word, system in (
        ("editorial", "editorial-grid"), ("éditorial", "editorial-grid"), ("grille", "editorial-grid"),
        ("poster", "poster-brutalist"), ("affirm", "poster-brutalist"), ("brut", "poster-brutalist"),
        ("bento", "bento"), ("mosa", "bento"),
        ("split", "split-screen"), ("scind", "split-screen"),
        ("classi", "classic-centered"), ("sobre", "classic-centered"), ("clair", "classic-centered"), ("clean", "classic-centered"),
        ("zine", "zine-collage"), ("collage", "zine-collage"),
        ("stage", "single-object stage"), ("produit", "single-object stage"),
    ):
        if word in s:
            return system
    return LAYOUT_BY_TONE.get(getattr(brief, "site_tone", "") or "", "editorial-grid")


COLOR_LITERAL = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()")


def _color(*candidates: str, fallback: str) -> str:
    """The first candidate that is a literal colour. A default brief carries CSS
    variable references (var(--muted-color)) that would leave a token pointing at
    nothing on the published page."""
    for value in candidates:
        value = (value or "").strip()
        if value and COLOR_LITERAL.match(value):
            return value
    return fallback


def palette_values(prefix: str) -> dict[str, str]:
    """The colour tokens of the site by id (nt2-primary -> #C68E3F): what the
    contrast repair resolves var(--id) against, and what the brief's light/dark
    line is computed from."""
    values = {}
    for key in ("primary", "secondary", "background", "text", "accent"):
        value = frappe.db.get_value("Builder Token", f"{prefix}-{key}", "value")
        if value:
            values[f"{prefix}-{key}"] = value
    return values


# //// Neoffice — the text token must read on the background token: the brief of a reseller site gave a dark site a dark text (#1a1a1a on #1b1f24) and every page frappe renders itself (login, shop, account request) came out unreadable (be2042bd "fix(nora): the text token reads on the background token")
def ensure_readable_text(prefix: str, palette: dict) -> str | None:
    """The text token must read on the background token: the brief of a reseller site gave a
    dark site a dark text (#1a1a1a on #1b1f24), and every page frappe renders itself
    (login, shop, account request) came out unreadable (2026-09-09). Below the WCAG
    ratio the text becomes near-white on a dark background, near-black on a light one.
    Returns the new value, None when nothing moved."""
    from builder.site_ai.nora.contrast import MIN_RATIO, contrast, luminance, parse_color

    bg, text = parse_color(palette.get(f"{prefix}-background"), palette), parse_color(palette.get(f"{prefix}-text"), palette)
    if not bg or not text or contrast(text, bg) >= MIN_RATIO:
        return None
    value = "#f5f5f5" if luminance(bg) < 0.4 else "#1a1a1a"
    doc_id = f"{prefix}-text"
    if frappe.db.exists("Builder Token", doc_id):
        doc = frappe.get_doc("Builder Token", doc_id)
        doc.value = value
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    palette[doc_id] = value
    return value


def mint_accent_token(prefix: str, group: str, value: str) -> str:
    """The seventh token, minted from the first page that leans on a colour of its own
    (see accent.py). Returns the handle."""
    doc_id = f"{prefix}-accent"
    label = f"{group} Accent"
    if frappe.db.exists("Builder Token", doc_id):
        doc = frappe.get_doc("Builder Token", doc_id)
        doc.update({"type": "Color", "value": value, "token_name": label, "group": group})
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "Builder Token", "token_name": label, "type": "Color", "value": value, "group": group}).insert(
            ignore_permissions=True, set_name=doc_id
        )
    frappe.db.commit()
    return f"var(--{doc_id})"


def mint_tokens(prefix: str, group: str, brief, primary: str, secondary: str) -> dict:
    """Six Builder Tokens with stable ids: the site's design system, referenced by
    the pages as var(--<prefix>-<key>) and by the chrome through its aliases."""
    backgrounds = getattr(brief, "section_backgrounds", None) or []
    spec = [
        ("primary", "Color", _color(primary, getattr(brief, "primary_color", ""), fallback="#1a1a1a")),
        ("secondary", "Color", _color(secondary, getattr(brief, "secondary_color", ""), fallback="#444444")),
        ("background", "Color", _color(backgrounds[0] if backgrounds else "", fallback="#ffffff")),
        ("text", "Color", _color(getattr(brief, "body_color", ""), getattr(brief, "heading_color", ""), fallback="#1a1a1a")),
        ("font-heading", "Font", getattr(brief, "heading_font", "") or "Inter"),
        ("font-body", "Font", getattr(brief, "body_font", "") or "Inter"),
    ]
    handles = {}
    for key, ttype, value in spec:
        doc_id = f"{prefix}-{key}"
        label = f"{group} {key.replace('-', ' ').title()}"
        if frappe.db.exists("Builder Token", doc_id):
            doc = frappe.get_doc("Builder Token", doc_id)
            doc.update({"type": ttype, "value": value, "token_name": label, "group": group})
            doc.save(ignore_permissions=True)
        else:
            frappe.get_doc(
                {"doctype": "Builder Token", "token_name": label, "type": ttype, "value": value, "group": group}
            ).insert(ignore_permissions=True, set_name=doc_id)
        handles[key] = f"var(--{doc_id})"
    frappe.db.commit()
    return handles


def placeholder_photos(page: dict, activity: str) -> list[str]:
    subject = (activity or "").strip()[:60] or page["title"]
    shots = {
        "accueil": [f"{subject}, hero", f"{subject}, in action", f"{subject}, team"],
        "about": [f"{subject}, founder portrait", f"{subject}, workshop"],
        "services": [f"{subject}, service detail", f"{subject}, result"],
        "contact": [f"{subject}, storefront", "map"],
        "team": [f"{subject}, team member portrait", f"{subject}, team member portrait 2", f"{subject}, team member portrait 3"],
        "blog": [f"{subject}, article 1", f"{subject}, article 2", f"{subject}, article 3"],
        "portfolio": [f"{subject}, project 1", f"{subject}, project 2", f"{subject}, project 3", f"{subject}, project 4"],
        "shop": [f"{subject}, product 1", f"{subject}, product 2", f"{subject}, product 3"],
        "one_page": [f"{subject}, hero", f"{subject}, in action", f"{subject}, storefront"],
    }.get(page["type"], [f"{subject}, {page['title']}"])
    urls = []
    for i, text in enumerate(shots):
        w, h = (1600, 900) if i == 0 else (1200, 800)
        urls.append(PLACEHOLDER.format(w=w, h=h, text=quote(text)))
    return urls


# The client's own photographs go to the page that shows them. Written with three generic
# placeholders matched afterwards, an image-led home dropped its category wall and placed
# two of twelve photographs (2026-09-11): the page is now written with the real pictures,
# each with what the vision read in it and what it is for.
CATEGORY_LIST = re.compile(
    r"(?:segments?|categories|collections|departments|univers|rayons|sections)\b[^:(.\n]{0,30}[:：(]\s*([^.\n)]+)",
    re.I,
)
PAGE_PHOTO_COUNT = {"about": 2, "contact": 1, "shop": 3, "portfolio": 4, "services": 3}


def category_names(*texts) -> list[str]:
    """The categories a brief names ("five segments: Snow, Street, Water, Outdoor, Home"),
    in its own words: an image-led home gives each one its photograph."""
    for text in texts:
        found = CATEGORY_LIST.search(text or "")
        if not found:
            continue
        names = [n.strip(" '\"") for n in re.split(r",|;|/|\band\b|\bet\b|\bund\b", found.group(1))]
        names = [n for n in names if n and len(n.split()) <= 3]
        if len(names) >= 2:
            return names[:8]
    return []


def library_photos(session_id: str | None, only: list[str] | None = None) -> list[dict]:
    """The photographs this conversation took in, with what the vision read in them;
    `only` keeps the ones the build was given. Read whether the build took them in just
    now or an earlier build of the same conversation did: a rebuild found all twelve
    already known, took in none, and wrote its pages with placeholders (2026-09-11)."""
    if not session_id or not frappe.db.exists("DocType", "Builder Content Asset"):
        return []
    rows = frappe.get_all(
        "Builder Content Asset",
        filters={"session_id": session_id, "asset_type": "Image"},
        fields=["file", "original_filename", "summary", "tags", "orientation", "quality", "extracted_text", "suggested_section"],
        order_by="creation asc",
    )
    wanted = set(only or [])
    photos = []
    for row in rows:
        if not (row.file or "").startswith("/files/") or (wanted and row.file not in wanted):
            continue
        stem = (row.original_filename or row.file).rsplit("/", 1)[-1].rsplit(".", 1)[0]
        words = {w for w in re.split(r"[^a-z0-9]+", f"{stem} {row.tags or ''} {row.suggested_section or ''}".lower()) if len(w) > 2}
        photos.append(
            {
                "url": row.file,
                "shows": re.split(r"(?<=[.!?])\s", (row.summary or "").strip())[0][:140],
                "words": words,
                "text": (row.summary or "").lower(),
                "landscape": (row.orientation or "") == "landscape",
                "quality": row.quality or "",
                "has_text": bool((row.extracted_text or "").strip()),
            }
        )
    return photos


def photos_for_page(page: dict, library: list[dict], used: dict, categories: list[str], minimal: bool) -> tuple[list[str], list[str]]:
    """The client's photographs a page is written with, and what each is for.

    The home gets its hero, one photograph per category the brief names (matched on what
    the vision read in it, else the best left) when the site is image-led or names its
    categories, and a wide one. A photograph carrying text never opens a page, and the ones
    already used go last, so the pages do not repeat each other."""
    if not library:
        return [], []

    def take(wanted=(), landscape=None) -> dict:
        # a picture carrying text (a banner, an advert) goes nowhere while anything else is left
        pool = [p for p in library if not p["has_text"]] or library
        if landscape is not None:
            pool = [p for p in pool if p["landscape"] == landscape] or pool

        def rank(p):
            fit = sum(2 for w in wanted if w in p["words"] or w in p["text"])
            return fit + {"high": 1.0, "medium": 0.5}.get(p["quality"], 0) - 3 * used.get(p["url"], 0)

        best = max(pool, key=rank)
        used[best["url"]] = used.get(best["url"], 0) + 1
        return best

    picks = []
    if page["type"] == "accueil":
        # the category tiles choose first: each needs one precise photograph, the hero any
        # good one (served first, the hero took the only snow picture and the snow tile got
        # the banner)
        tiles = []
        if minimal or categories:
            for name in categories:
                wanted = [w for w in re.split(r"[^a-z0-9]+", name.lower()) if len(w) > 2]
                tiles.append((take(wanted), f"the tile of '{name}'"))
        picks = [(take(landscape=True), "the hero, full bleed"), *tiles, (take(landscape=True), "a wide photograph")]
    else:
        wanted = [w for w in re.split(r"[^a-z0-9]+", f"{page['title']} {page['type']}".lower()) if len(w) > 2]
        for i in range(PAGE_PHOTO_COUNT.get(page["type"], 2)):
            picks.append((take(wanted), "the first photograph of the page" if i == 0 else "a photograph"))
    urls, notes = [], []
    for photo, role in picks:
        if photo["url"] in urls:
            continue
        urls.append(photo["url"])
        notes.append(f"{role}; it shows: {photo['shows']}" if photo["shows"] else role)
    return urls, notes


# Jinja includes a page may carry, by page type: the site's own components (a
# working contact form, a map, a team grid) and, where the shop app is installed,
# its live widgets. The old generator listed them per page in its system prompt
# (site_ai/prompts/system_prompts.py); the page brief does the same for the
# upstream page writer. An include is the innerHTML of its own plain block: the
# Builder renderer runs Jinja on block content, so the widget appears at render.
# an include listed here is REQUIRED on its page: the model wrote its own <form> on the
# Contact page of the B2B regeneration, five inputs that post nowhere
REQUIRED_INCLUDES = {"{% include 'builder/templates/includes/contact_form.html' %}"}

PAGE_INCLUDES = {
    "contact": [
        ("{% include 'builder/templates/includes/contact_form.html' %}", "a working contact form, sent to the site's inbox"),
        ("{% include 'builder/templates/includes/google_map.html' %}", "a map of the address"),
        ("{% include 'webshop/templates/includes/opening_hours.html' %}", "the shop's opening hours, live, holidays included"),
    ],
    "about": [
        ("{% include 'builder/templates/includes/team_grid.html' %}", "the team"),
        ("{% include 'builder/templates/includes/company_timeline.html' %}", "the company's timeline"),
        ("{% include 'webshop/templates/includes/opening_hours.html' %}", "the shop's opening hours, live"),
    ],
    "accueil": [
        ("{%- set carousel_title = \"Nos produits\" -%}{%- set carousel_limit = 8 -%}{% include \"webshop/templates/includes/product_carousel.html\" %}", "a carousel of real products (title of your choice)"),
        ("{%- set carousel_title = \"Nos marques\" -%}{% include \"webshop/templates/includes/brand_carousel.html\" %}", "the brands carried"),
    ],
    "shop": [
        ("{%- set carousel_title = \"Nos produits\" -%}{%- set carousel_limit = 8 -%}{% include \"webshop/templates/includes/product_carousel.html\" %}", "a carousel of real products"),
        ("{%- set show_discounted_only = true -%}{% include \"webshop/templates/includes/product_carousel.html\" %}", "the products on sale"),
    ],
    "one_page": [
        ("{% include 'builder/templates/includes/contact_form.html' %}", "a working contact form, in the contact section"),
        ("{% include 'webshop/templates/includes/opening_hours.html' %}", "the shop's opening hours, live"),
    ],
}


# //// Neoffice ▼▼▼ — new: an include a page carries must be the one the brief offered, written exactly as offered; the model wrote the shop's opening hours with builder's path instead of webshop's and the Contact page of a reseller site answered 417 for a template it could not find (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
INCLUDE_TAG = re.compile(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}")
ALWAYS_ALLOWED_INCLUDES = ("{% include 'builder/templates/includes/contact_form.html' %}",)


def repair_includes(blocks: list, allowed: list[tuple[str, str]]) -> tuple[int, int]:
    """An include a page may carry is one the brief offered, written as offered. The
    model wrote the shop's opening hours with builder's path instead of webshop's and
    the Contact page of a reseller site answered 417 (a template it could not find,
    2026-09-09). A tag whose file name was offered is rewritten to the offered tag; any
    other include block is removed. Returns (rewritten, removed)."""
    from builder.site_ai.nora.layout import _walk

    canon = {}
    for tag, _purpose in list(allowed) + [(t, "") for t in ALWAYS_ALLOWED_INCLUDES]:
        m = INCLUDE_TAG.search(tag)
        if m:
            canon[m.group(1).rsplit("/", 1)[-1]] = tag
    rewritten = removed = 0
    for block in _walk(blocks):
        kids = [c for c in (block.get("children") or []) if isinstance(c, dict)]
        kept = []
        for child in kids:
            html = child.get("innerHTML") if isinstance(child.get("innerHTML"), str) else ""
            m = INCLUDE_TAG.search(html) if html and "include" in html else None
            if not m:
                kept.append(child)
                continue
            tag = canon.get(m.group(1).rsplit("/", 1)[-1])
            if not tag:
                removed += 1
                continue
            if html.strip() != tag:
                child["innerHTML"] = tag
                rewritten += 1
            kept.append(child)
        if len(kept) != len(block.get("children") or []):
            block["children"] = kept
    return rewritten, removed
# //// Neoffice ▲▲▲


def includes_block(includes: list[tuple[str, str]]) -> str:
    """The brief's INCLUDES block: the required includes as an order (the contact form
    IS the form, the model must not write its own), then the optional ones."""
    if not includes:
        return ""
    required = [(t, p) for t, p in includes if t in REQUIRED_INCLUDES]
    optional = [(t, p) for t, p in includes if t not in REQUIRED_INCLUDES]
    lines = []
    if required:
        lines.append(
            "INCLUDES REQUIRED on this page (each one as the `text` of its own plain div block, copied exactly, "
            "never inside a grid or flex row; do NOT write a <form> of your own, this include IS the working form):"
        )
        lines += [f"- {t} \u2014 {p}" for t, p in required]
    if optional:
        lines.append(
            ("INCLUDES available (optional, same rule: " if required else "INCLUDES (optional, ")
            + "each one as the `text` of its own plain div block, copied exactly, never inside a grid or flex row):"
        )
        lines += [f"- {t} \u2014 {p}" for t, p in optional]
    return "\n".join(lines)


def _business_key(name: str) -> str:
    """A company name reduced to what identifies it: lower-cased, accents and legal
    forms (SA, Sàrl, AG, GmbH, SARL, Ltd) and punctuation stripped."""
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    words = [w for w in re.findall(r"[a-z0-9]+", text) if w not in LEGAL_FORMS]
    return " ".join(words)


LEGAL_FORMS = {"sa", "sarl", "ag", "gmbh", "ltd", "llc", "inc", "sagl", "snc", "societe", "company", "co"}


def _other_business(profile: str | None, site_name: str = "") -> bool:
    """Whether the site being built is another business than the instance's shop. The
    shop app's data (products, brands, opening hours, the cart) is instance-wide, so a
    site of ANOTHER business must not show it (the B2B test site listed the host bakery's
    products and opening hours), while a second storefront of the SAME company (a B2B
    space beside the shop) shows exactly the same shop and hours, as it should. Website
    Profile carries no company: a profile is a storefront of the instance's company by
    design, so the test is the name the user gave the site against the instance's
    default company, reduced to what identifies them."""
    if not profile:
        return False
    try:
        if frappe.db.get_value("Website Profile", profile, "is_default"):
            return False
        company = frappe.db.get_single_value("Global Defaults", "default_company") or ""
        title = frappe.db.get_value("Website Profile", profile, "title") or ""
    except Exception:
        return True
    mine = _business_key(site_name)
    if not mine:
        return True
    # the instance's company, or the profile's own name (a second brand of the company
    # gets a profile named after it: "a second brand" beside "the agency")
    for theirs in (_business_key(company), _business_key(title)):
        if theirs and (mine in theirs or theirs in mine):
            return False
    return True


# //// Neoffice — added helper and _webshop_installed() below (5efa79d1 "feat(nora): a B2B
# //// site is a shop window, and frappe's pages read on a dark site"): a B2B or login-gated
# //// profile had no way to the catalogue in its menu, whatever the site type the model chose
# //// (a reseller site, 2026-09-09: "on a pas la page shop dans le b2b").
def _profile_is_b2b(profile: str | None) -> bool:
    """Whether the profile is a business-to-business site (its kind, or the sign-in
    gate). Such a site is a shop window whatever the site type the model chose:
    visitors browse the catalogue at the public price and sign in for their tariff and
    the cart, so it gets the catalogue entry in its menu and the product carousels on
    its pages (a reseller site, 2026-09-09: "on a pas la page shop dans le b2b")."""
    if not profile:
        return False
    try:
        kind, gated = frappe.db.get_value("Website Profile", profile, ["site_kind", "b2b_only"]) or (None, 0)
    except Exception:
        return False
    return kind == "B2B" or bool(gated)


def _webshop_installed() -> bool:
    try:
        return "webshop" in frappe.get_installed_apps()
    except Exception:
        return False


# //// Neoffice — added ACCOUNT_REQUEST_ROUTE and _account_request_route() below (8756214d
# //// "feat(chrome): a menu that folds by itself, a CTA that reads on its header, no Home
# //// entry"): a B2B site now gets "Request an account" on the theme's request page as its
# //// CTA instead of doubling the resellers page or the sign-in entry.
# neoffice_theme/www/compte_professionnel.py: the form that opens a B2B Account Request
ACCOUNT_REQUEST_ROUTE = "/compte-professionnel"


def _account_request_route() -> str | None:
    """The theme's professional account request page, when the theme is installed."""
    try:
        return ACCOUNT_REQUEST_ROUTE if "neoffice_theme" in frappe.get_installed_apps() else None
    except Exception:
        return None


def available_includes(page_type: str, site_type: str = "vitrine", profile: str | None = None, site_name: str = "") -> list[tuple[str, str]]:
    """The includes of this page type whose app is installed on the bench (an include of
    an absent app turns the whole page into a 500 at render time), minus every include
    that would show another business's data — the team, the timeline, the map of the
    address, the hours, the products: only the contact form is left to a site built for
    a business other than the instance's (the About page of the B2C test site carried
    the host's employees and milestones, 2026-09-08) — and the product and brand
    carousels only on an e-commerce site."""
    try:
        installed = set(frappe.get_installed_apps())
    except Exception:
        installed = {"builder"}
    shop_data = not _other_business(profile, site_name)
    out = []
    for tag, purpose in PAGE_INCLUDES.get(page_type, []):
        path = re.search(r"include\s+['\"]([^'\"]+)['\"]", tag)
        app = path.group(1).split("/", 1)[0] if path else ""
        if app not in installed and app != "templates":
            continue
        if not shop_data and "contact_form" not in tag:
            continue
        # //// Neoffice — "and not _profile_is_b2b(profile)" added (5efa79d1): a B2B profile is
        # //// a shop window whatever its site type, so it keeps the product carousels too.
        if app == "webshop" and "carousel" in tag and site_type != "ecommerce" and not _profile_is_b2b(profile):
            continue
        out.append((tag, purpose))
    return out


def page_brief_text(site: dict, brief, page: dict, handles: dict, contact_prompt: str, layout_system: str, language: str, photos: list[str], cta: tuple[str, str], palette: dict | None = None, revision: str | None = None, photo_notes: list[str] | None = None) -> str:
    is_home = page["route"] == "home"
    # //// Neoffice — an image-led site takes the image-led plans (IMAGE_LED_PLANS); a page
    # //// that is text by nature keeps its own
    minimal = site.get("copy_density") == "minimal" and page["type"] not in TEXT_BY_NATURE
    plan = (IMAGE_LED_PLANS.get(page["type"]) or IMAGE_LED_PLANS["generic"]) if minimal else SECTION_PLANS.get(page["type"], SECTION_PLANS["generic"])
    sections = "\n".join(f"{i}. {s}" for i, s in enumerate(plan, 1))
    concept = getattr(brief, "design_concept", "") or ""
    signature = getattr(brief, "signature_element", "") or ""
    tone = getattr(brief, "site_tone", "") or ""
    hero = getattr(brief, "hero_style", "") or ""
    # the client's own photographs come with what each shows and what it is for (photos_for_page)
    notes = photo_notes or []
    photo_lines = "\n".join(f"{i}. {u}" + (f"  ({notes[i - 1]})" if i - 1 < len(notes) else "") for i, u in enumerate(photos, 1))
    includes = available_includes(page["type"], site.get("site_type") or "vitrine", site.get("profile"), site.get("site_name") or "")
    page_role = (
        "the HOME page: open with the hero" if is_home
        else "an INTERIOR page: the site renders a title band with the page title above the content, so start directly with the first content section, no hero banner and no repeated page title"
    )
    lines = [
        f"DESIGN DIRECTION: {concept or 'a distinctive direction that fits the brand'} (tone: {tone or 'professional'}; hero style: {hero or 'free'}).",
        f"LAYOUT SYSTEM: {layout_system}. SIGNATURE MOVE: {signature or 'choose one that fits the system'}. Keep the SAME system and move on every page of this site.",
        ("INSPIRATION (what the client likes; echo the palette and the mood, never copy): " + " | ".join(site["inspiration"])) if site.get("inspiration") else "",
        f"BRAND: {site['site_name']}. Activity: {site['activity']}",
        f"POSITIONING: {site.get('differentiators') or 'derive it from the activity'}",
        contact_prompt.strip() if contact_prompt else "",
        (
            f"PALETTE (token handles, use them for every brand colour): primary {handles['primary']}, secondary {handles['secondary']}, "
            f"background {handles['background']}, text {handles['text']}. Literal hex only for derived shades (rgba() tints)."
        ),
        (
            # the model knows the handles by role, not by luminance: a cream secondary
            # under white copy was the invisible CTA band of neoffice-maintenance #281
            f"CONTRAST: {palette_roles(palette)}. A dark band uses {handles['text']} as background with {handles['background']} "
            f"as text colour; a light band keeps {handles['text']} as text colour. Never white text on a LIGHT or MID handle."
            if palette else ""
        ),
        (
            f"FONTS: headings '{getattr(brief, 'heading_font', 'Inter')}' as fontFamily {handles['font-heading']}, "
            f"body '{getattr(brief, 'body_font', 'Inter')}' as fontFamily {handles['font-body']}."
        ),
        (
            f"SHAPE: corners {getattr(brief, 'border_radius_style', 'subtle')}, buttons {getattr(brief, 'cta_shape', 'Rounded')}, "
            f"hover {getattr(brief, 'button_hover', 'Darken')}, motion {getattr(brief, 'motion_style', 'Calm')}."
        ),
        f"PAGE: '{page['title']}' at /{page['route']} — {page_role}.",
        f"SECTIONS, in order, with real copy written in {language}:\n{sections}",
        (
            # the client's categories by name: without them the category wall came out with no
            # name and two repeated photographs (2026-09-12)
            f"CATEGORIES, in the client's words: {', '.join(site['categories'])}. Name each one exactly so, in this order, "
            "and give each its own photograph tile (the PHOTOS notes say which)."
            if site.get("categories") and page["type"] == "accueil"
            else ""
        ),
        (
            # //// Neoffice — the copy rule of an image-led site (see IMAGE_LED_PLANS)
            "COPY: minimal, the photographs carry the page. Headlines of two to five words, at most one line of twelve "
            "words under a heading, NO paragraph, no list of features, no testimonials, no grid of icons, no band of "
            "figures. When in doubt, cut the text and enlarge the photograph."
            if minimal else ""
        ),
        f"CTA: the primary button says '{cta[0]}' and links to '{cta[1]}'; use it once in the hero (home) or the last section, and in the final band.",
        (
            "PHOTOS: the client's OWN photographs. Copy each URL exactly, without the note in brackets after it; give each "
            f"a descriptive alt in {language}; use each at most once and follow its note: the hero opens the page, each "
            f"category tile takes the photograph named for it, full bleed, the category's name as its only text:\n{photo_lines}"
            if notes
            else "PHOTOS AVAILABLE (placeholders that the site replaces with real photos after the build; use each at most once, "
            f"copy the URL exactly, give it a descriptive alt in {language}):\n{photo_lines}"
        ),
        (
            f"ACCENT: {handles['accent']} is the site's signature accent (kickers, badges, one highlight per section, "
            "sparingly); use it instead of inventing another bright colour, and no other raw hex."
            if handles.get("accent") else ""
        ),
        "CLASS CONTRACT: " + CLASS_CONTRACT,
        includes_block(includes),
        (
            "RULES: no header, navigation or footer sections (the site chrome is rendered around the page); no lorem; "
            f"business data verbatim; spell the brand name exactly '{site['site_name']}'; every text in {language}; "
            "no em dashes; mobile-first m_style on every grid; font sizes in rem or clamp(), never a bare vw "
            "(h1 at most 4.5rem, h2 3.25rem, body text 1.35rem on desktop). A repeat block carries the grid classes "
            "itself (u-grid u-grid--3 on the repeat, never on a div around it: the clones would stack in one column). "
            "In a 12-column grid the spans of a text block and of a media block never overlap: text never runs under an image. "
            # //// Neoffice — added: every "Learn more" must be a real link to a route, cards of a
            # //// group share the same action, and a button never takes the colour of the section
            # //// it sits on (0d1ae82c "feat(design system): buttons that read anywhere, calls to
            # //// action that lead somewhere, no client names in comments")
            "Every invitation to go further ('Learn more', 'Discover', 'See the…') is a real link: an <a> with an href to one "
            "of this site's routes, never a bare span; the cards of a group carry the same action each. In a pair of buttons "
            "the main action comes first, on the left. A button never wears the colour of the section it sits on: no "
            "u-btn--primary on a section painted in the primary colour (use u-btn--secondary or u-btn--outline there)."
        ),
        revision or "",
    ]
    return "\n".join(line for line in lines if line)


def _progress(ctx, job_id: str, message: str, progress: int, extra: dict | None = None) -> None:
    from builder.api import _update_generation_status

    try:
        ctx.emit("progress", message=message)
    except Exception:
        pass
    _update_generation_status(job_id, {"status": "running", "progress": progress, "current_step": message, **(extra or {})})


PAGE_STREAM_MAX_CHARS = 80_000  # a page of YAML is 10 to 20 k characters; beyond this the model is looping
# a page after a long think still needs its 60 to 120 s of YAML: the ceiling sits above
# the thinking budget plus that, not at the old 480 s that cut streams mid-page
PAGE_STREAM_MAX_SECONDS = 600
# a stream that has sent nothing at all after this long is a stalled connection, not
# a slow page: the Contact page of the B2C regeneration waited the full 480 s twice
# for nothing before the retry
PAGE_STREAM_FIRST_CHUNK_SECONDS = 90
# a thinking model (Kimi K2.7) streams its reasoning before the first line of YAML;
# on a home page that alone takes over 90 s, and counting only content killed two
# healthy attempts in a row (B2B regeneration, 2026-09-08). Reasoning proves the
# stream is alive; it only has to end within this budget. 300 s cut two healthy pages
# of the B2B regeneration at 42 k and 52 k characters of reasoning (they finished on
# the retry in about six minutes); 420 s covers what was measured.
PAGE_STREAM_THINKING_SECONDS = 420


def _delta_parts(chunk) -> tuple[str, str]:
    """The (content, reasoning) text of one streamed chunk. Thinking models send their
    reasoning as `reasoning_content` (litellm's Delta attribute, or the provider's own
    field) with an empty content, for minutes, before the first line of the answer."""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return "", ""
    delta = choices[0].delta
    reasoning = getattr(delta, "reasoning_content", None)
    if not reasoning:
        extra = getattr(delta, "provider_specific_fields", None)
        reasoning = extra.get("reasoning_content") if isinstance(extra, dict) else None
    return (getattr(delta, "content", None) or ""), (reasoning or "")


def _stream_text(ctx, model: str, messages: list, params: dict) -> str:
    """A page of YAML takes minutes to write: stream it, as upstream's artifact
    generator does, so the provider's read timeout counts between chunks instead
    of over the whole completion. Stops early when the user cancels the turn, and
    gives up on a runaway generation (size or wall clock) so the page is retried
    instead of holding the whole build."""
    from builder.ai import llm

    stream = llm.complete(model, messages, params, stream=True)
    parts: list[str] = []
    size, thought, started = 0, 0, time.time()
    try:
        for chunk in stream:
            if ctx.is_cancelled():
                break
            elapsed = time.time() - started
            if size > PAGE_STREAM_MAX_CHARS or elapsed > PAGE_STREAM_MAX_SECONDS:
                raise TimeoutError(f"page generation runaway after {size} chars / {int(elapsed)} s")
            if not size and not thought and elapsed > PAGE_STREAM_FIRST_CHUNK_SECONDS:
                raise TimeoutError(f"page generation stalled: no output after {int(elapsed)} s")
            if not size and elapsed > PAGE_STREAM_THINKING_SECONDS:
                raise TimeoutError(f"page generation still thinking after {int(elapsed)} s ({thought} chars of reasoning)")
            try:
                ctx.record_usage(chunk, model=model)
            except Exception:
                pass
            delta, reasoning = _delta_parts(chunk)
            thought += len(reasoning)
            if delta:
                parts.append(delta)
                size += len(delta)
    finally:
        try:
            stream.close()
        except Exception:
            pass
    return "".join(parts)


def _page_model(ctx) -> str:
    """The heavy model for page YAML: the managed page model when the instance is
    managed and it is registered, else the chat's model."""
    from builder.ai.models import ModelRegistry
    from builder.site_ai.capabilities import is_managed
    from builder.site_ai.config import get_ai_settings
    from builder.site_ai.managed import ROUTE_PREFIX

    if is_managed():
        candidate = f"{ROUTE_PREFIX}/{get_ai_settings().page_model}"
        if ModelRegistry.find(candidate):
            return candidate
    return ctx.model


def _write_page(page: dict, blocks: list, data_script: str, profile: str | None, host_page: str | None, description: str) -> tuple[str, str]:
    """Create (or refill the host page as) a published Builder Page. Returns (name, route)."""
    from builder.ai.page_writer import compact_json
    from builder.api import _blocks_fingerprint

    payload = compact_json(blocks)
    scoped = frappe.db.has_column("Builder Page", "neo_website_profile")
    if host_page and frappe.db.exists("Builder Page", host_page):
        name = host_page
        doc = frappe.get_doc("Builder Page", name)
        doc.page_title = page["title"]
        doc.blocks = payload
        doc.draft_blocks = payload
        doc.page_data_script = data_script or ""
        doc.published = 1
        doc.meta_description = description
        if scoped:
            doc.neo_website_profile = profile
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc("Builder Page")
        doc.page_title = page["title"]
        doc.blocks = payload
        doc.draft_blocks = payload
        doc.page_data_script = data_script or ""
        doc.published = 1
        doc.meta_description = description
        if scoped and profile:
            doc.neo_website_profile = profile
        doc.insert(ignore_permissions=True)
        name = doc.name
    route = page["route"]
    occupant_filters = {"route": route, "is_template": 0, "name": ("!=", name)}
    if scoped:
        occupant_filters["neo_website_profile"] = profile if profile else ("is", "not set")
    if frappe.db.get_value("Builder Page", occupant_filters, "name"):
        route = f"{route}-{frappe.generate_hash(length=4)}"
    # the fingerprint must match what the row holds: the doctype re-serialises blocks on
    # save, and the draft is what classify_existing_pages hashes first
    stored_draft, stored_blocks = frappe.db.get_value("Builder Page", name, ["draft_blocks", "blocks"])
    frappe.db.set_value(
        "Builder Page",
        name,
        {"route": route, "ai_generated_at": now(), "ai_blocks_hash": _blocks_fingerprint(stored_draft or stored_blocks)},
        update_modified=False,
    )
    frappe.db.commit()
    return name, route


def _describe(blocks: list) -> str:
    from builder.api import _describe_page

    try:
        return _describe_page(blocks) or ""
    except Exception:
        return ""


def apply_navigation(config, created: list[dict], site_type: str, description: str, profile: str | None, lang: str = "fr", site_name: str = "") -> None:
    """Menu, footer and home page from the pages just built (the worker's step 5).
    Labels are translated into the site's language, not the operator's session."""
    config.menu_items = []
    # /all-products is the instance's catalogue: on another business's profile it would
    # be someone else's shop in this site's menu (the florist listed the bakery)
    # //// Neoffice — moved out of the pages loop below (8756214d "feat(chrome): a menu that
    # //// folds by itself, a CTA that reads on its header, no Home entry"): that loop no
    # //// longer visits a "Home" entry to hang the Shop/Catalogue append off, so it now runs
    # //// once here instead.
    if not _other_business(profile, site_name):
        if site_type in ("ecommerce", "ecommerce_search"):
            config.append("menu_items", {"label": _("Shop", lang=lang), "url": "/all-products", "is_external": False, "open_in_new_tab": False})
        elif _profile_is_b2b(profile) and _webshop_installed():
            # a B2B site is a shop window whatever its site type (see _profile_is_b2b)
            config.append("menu_items", {"label": _("Catalogue", lang=lang), "url": "/all-products", "is_external": False, "open_in_new_tab": False})
    seen = set()
    for page in created:
        route = page["route"]
        # the logo is the way home: a "Home" entry only fills a row that fills up fast
        # (a reseller site, 2026-09-10: "le côté accueil fait trop d'entrées")
        # //// Neoffice — route no longer aliased to "Home" (8756214d "feat(chrome): a menu
        # //// that folds by itself, a CTA that reads on its header, no Home entry"): "/",
        # //// "/home" and "/index" are now skipped instead of relabelled.
        if route in seen or route in ("/", "/home", "/index"):
            continue
        seen.add(route)
        # //// Neoffice — see the block marker above: no more Home relabelling
        config.append("menu_items", {"label": page["title"], "url": route, "is_external": False, "open_in_new_tab": False})
    for field, value in (("footer_logo_type", config.get("logo_type")), ("footer_logo_text", config.get("logo_text")), ("footer_logo_image", config.get("logo_image")), ("show_footer_logo", True), ("footer_menu_source", "Custom links")):
        if hasattr(config, field):
            config.set(field, value)
    if hasattr(config, "footer_description"):
        from builder.api import _shorten_for_footer

        config.footer_description = _shorten_for_footer(description)
    if hasattr(config, "footer_links"):
        config.footer_links = []
        for page in created:
            home = page["route"] in ("/", "/home", "/index")
            config.append("footer_links", {"column_name": _("Navigation", lang=lang), "label": _("Home", lang=lang) if home else page["title"], "url": "/" if home else page["route"]})
    config.save(ignore_permissions=True)
    home_name = next((p["name"] for p in created if p["route"] in ("/", "/home", "/index")), None)
    if profile and frappe.db.exists("DocType", "Website Profile"):
        if home_name:
            frappe.db.set_value("Website Profile", profile, "home_page", home_name)
        frappe.cache.delete_value("nt_website_profiles_by_host")
        frappe.cache.delete_value("website_page")
    elif home_name:
        frappe.db.set_value("Website Settings", "Website Settings", "home_page", "home")
        frappe.db.set_value("Builder Settings", "Builder Settings", "home_page", "home")
    frappe.db.commit()
    frappe.clear_cache()


def build_site(ctx, spec: dict) -> str:
    from builder.ai import llm
    from builder.ai.block_codec import BlockCodec
    from builder.ai.page_writer import expand_page_yaml
    from builder.site_ai.nora.contrast import repair_contrast
    from builder.ai.prompts import Prompts
    from builder.api import (
        SITE_TYPE_HEADER_FOOTER_DEFAULTS,
        _contact_context_prompt,
        _enqueue_image_generation,
        _get_site_chrome_config,
        _image_backend_available,
        _scan_placeholder_images,
        _update_generation_status,
        apply_brief_site_chrome,
        classify_existing_pages,
        get_site_contact_context,
    )
    from builder.site_ai.config import get_ai_settings
    from builder.site_ai.generators.brief_generator import BriefGenerator, get_default_brief
    from builder.site_ai.logging import ai_log
    from builder.site_ai.nora.accent import dominant_accent, rewrite_hex
    from builder.site_ai.nora import visual_check
    from builder.hf_utils.header_footer import NEWSLETTER_DEFAULTS
    # //// Neoffice — cards stack on a grid (grid_stacked_cards/repeater_counts) and, with image
    # //// generation off, placehold.co slots become inline SVGs (neutral_placeholders) instead of
    # //// broken external images (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
    from builder.site_ai.nora.layout import grid_stacked_cards, place_orphans, repeater_counts, strip_title_band, unwrap_grid_wrappers
    from builder.site_ai.nora.placeholders import neutral_placeholders
    from builder.site_ai.nora.punctuation import french_spacing
    from builder.site_ai.nora.typography import cap_font_sizes
    from builder.site_ai.nora.prompts import page_profile

    started = time.time()
    site_name = (spec.get("site_name") or "").strip()
    activity = (spec.get("activity") or "").strip()
    if not site_name or not activity:
        return "FAILED: site_name and activity are required."
    site_type = spec.get("site_type") if spec.get("site_type") in SECTION_PLANS or spec.get("site_type") in ("vitrine", "vitrine_user", "ecommerce", "ecommerce_search", "saas", "blog", "portfolio", "one_page") else "vitrine"
    pages = normalise_pages(spec.get("pages") or [], site_type)
    profile = (spec.get("website_profile") or "").strip() or page_profile(ctx.page_id)
    if profile and not frappe.db.exists("Website Profile", profile):
        return f"FAILED: unknown website_profile '{profile}'."
    replace_existing = spec.get("replace_existing") or "auto"
    lang_code = (spec.get("language") or frappe.db.get_single_value("Builder Settings", "default_language") or "fr").strip().lower()
    language = {"fr": "French", "en": "English", "de": "German", "it": "Italian"}.get(lang_code[:2], lang_code)
    lang_code = lang_code[:2] if lang_code[:2] in ("fr", "en", "de", "it") else "fr"
    primary = (spec.get("primary_color") or "").strip() or None
    secondary = (spec.get("secondary_color") or "").strip() or None
    logo_image = clean_logo(spec.get("logo_image"))
    job_id = f"site_gen_{frappe.generate_hash(length=10)}"
    total = len(pages)

    # 1. the site's existing pages
    classes = classify_existing_pages(profile)
    host_page = ctx.page_id if ctx.page_id and frappe.db.exists("Builder Page", ctx.page_id) else None
    host_is_blank = False
    if host_page:
        blocks_raw = frappe.db.get_value("Builder Page", host_page, "draft_blocks") or frappe.db.get_value("Builder Page", host_page, "blocks")
        try:
            host_is_blank = not blocks_raw or not any((json.loads(blocks_raw) or [{}])[0].get("children") or [])
        except Exception:
            host_is_blank = False
    protected = [p for p in classes["protected"] if p["name"] != host_page or not host_is_blank]
    if replace_existing == "auto" and protected:
        names = ", ".join(f"'{p['title']}'" for p in protected[:6])
        ai_log("info", "Site build needs confirmation", site_name=site_name, profile=profile, protected=len(protected))
        return (
            f"CONFIRM_NEEDED: {len(protected)} existing page(s) were designed or edited by hand ({names}). "
            "Ask the user whether to replace them too (replace_existing='force') or keep them, the untouched pages "
            "being replaced as usual (replace_existing='keep_edited'), then call generate_site again with the same "
            "arguments plus their choice. 'none' keeps every existing page beside the new site: pass it only when "
            "the user asks for exactly that."
        )
    # the build is real from here on: the confirmation round trip above must leave neither
    # a "running" job behind (get_site_generation_status) nor a START line without an end
    _update_generation_status(job_id, {"status": "running", "progress": 0, "total_pages": total, "current_step": "Starting", "pages_created": [], "error": None, "site_name": site_name, "started_at": now()})
    ai_log("info", "=== NORA SITE BUILD STARTED ===", job_id=job_id, site_name=site_name, profile=profile, lang=lang_code, replace=replace_existing, pages=[p["title"] for p in pages])
    to_delete = pages_to_replace(classes, replace_existing)
    host_reusable = host_page and (host_is_blank or host_page in to_delete)
    to_delete = [n for n in to_delete if n != host_page]
    _progress(ctx, job_id, _("Preparing the site"), 3)
    for name in to_delete:
        try:
            frappe.delete_doc("Builder Page", name, ignore_permissions=True, force=True)
        except Exception:
            frappe.db.delete("Dynamic Link", {"link_doctype": "Builder Page", "link_name": name})
            frappe.delete_doc("Builder Page", name, ignore_permissions=True, force=True)
    frappe.db.commit()

    # 2. the chrome basics
    config = _get_site_chrome_config(profile)
    for key, value in SITE_TYPE_HEADER_FOOTER_DEFAULTS.get(site_type, SITE_TYPE_HEADER_FOOTER_DEFAULTS["vitrine"]).items():
        if hasattr(config, key):
            setattr(config, key, value)
    # a B2B or login-gated profile needs the account entry in its header whatever the
    # site type: its visitors sign in for their tariff and the cart (the catalogue itself
    # stays open, at the public price)
    # //// Neoffice — inlined into _profile_is_b2b() (5efa79d1): same site_kind/b2b_only lookup
    # //// as the menu's Catalogue entry, kept in one place.
    if profile and hasattr(config, "show_user") and _profile_is_b2b(profile):
        config.show_user = True
    if logo_image:
        config.logo_type = "Image"
        config.logo_image = logo_image
    elif profile:
        # a profile's Variant is bootstrapped from the main site's Single, logo
        # included: without an upload the new site shows its own name, not the
        # host's logo (on the Single, logo-default.png IS the client's logo)
        config.logo_type = "Text"
        config.logo_image = None
    else:
        config.logo_type = "Image" if config.get("logo_image") else "Text"
    config.logo_text = site_name
    if hasattr(config, "footer_logo_text"):
        config.footer_logo_text = site_name
    # the newsletter strings the Variant still carries as English defaults go blank:
    # footer.html translates an empty field in the visitor's language ("Subscribe to
    # our newsletter" sat on the French B2C footer, 2026-09-08)
    for field, default in NEWSLETTER_DEFAULTS.items():
        if hasattr(config, field) and (config.get(field) or "").strip() == default:
            config.set(field, "")
    if primary and hasattr(config, "primary_color"):
        config.primary_color = primary
    if secondary and hasattr(config, "secondary_color"):
        config.secondary_color = secondary
    contact_page = next((p for p in pages if p["type"] == "contact"), None)
    cta = (_("Contact us", lang=lang_code), f"/{contact_page['route']}" if contact_page else "/")
    # a B2B site opens accounts before it sells: its CTA asks for one on the theme's
    # request page, and never doubles the "Sign in" entry or a resellers page of the menu
    # //// Neoffice — added (8756214d "feat(chrome): a menu that folds by itself, a CTA that
    # //// reads on its header, no Home entry"): a B2B profile's CTA points to
    # //// _account_request_route() instead of the default "Contact us" link.
    if _profile_is_b2b(profile) and _account_request_route():
        cta = (_("Request an account", lang=lang_code), _account_request_route())
    config.cta_text, config.cta_url = cta
    if primary and hasattr(config, "cta_button_color"):
        config.cta_button_color = primary
    config.menu_items = []
    config.save(ignore_permissions=True)
    frappe.db.commit()

    # 3. the design brief (K3 with design intelligence), grounded in real business data
    _progress(ctx, job_id, _("Writing the design brief"), 8)
    # the instance's own company (ERPNext Company, its address, its logo) grounds the
    # site of THAT business; a site built for another business on a secondary profile
    # must not inherit its logo, address, phone or e-mail (the B2B test site carried the
    # host company's logo in its header and its address on every page, 2026-09-08)
    if _other_business(profile, site_name):
        contact_data = {}
        contact_prompt = (
            " Contact details: none are verified for this business. Use clearly generic placeholders the client "
            "will replace (a street in its town, a Swiss phone in the +41 format, an e-mail on its own domain) and "
            "never another company's name, logo, address or e-mail."
        )
    else:
        contact_data = get_site_contact_context(profile)
        contact_prompt = _contact_context_prompt(contact_data) or ""
    if not logo_image and contact_data.get("logo"):
        logo_image = contact_data["logo"]
    # the sites and pictures the client likes: read once, shown to the brief's vision
    # pass, and summarised for every page (inspiration.py)
    # //// Neoffice — imports monochrome() too, needed below to read "no colour" off the
    # //// inspirations when the client didn't say it (918629eb "feat(site build): the client's own photographs, every reference site, and a monochrome direction")
    from builder.site_ai.nora.inspiration import clean_list, gather, monochrome

    inspiration = {"images": [], "notes": [], "failed": []}
    inspiration_urls, inspiration_images = clean_list(spec.get("inspiration_urls")), clean_list(spec.get("inspiration_images"))
    if inspiration_urls or inspiration_images:
        _progress(ctx, job_id, _("Reading the inspirations"), 6)
        try:
            inspiration = gather(inspiration_urls, inspiration_images)
            ai_log("info", "Inspirations read", sites=len(inspiration_urls), pictures=len(inspiration_images), notes=inspiration["notes"], failed=inspiration["failed"])
        except Exception as e:
            ai_log("warning", "Inspirations skipped", error=str(e)[:200])
    inspiration_prompt = (" Inspirations the client likes (echo their palette and mood): " + " | ".join(inspiration["notes"])) if inspiration["notes"] else ""

    # //// Neoffice ▼▼▼ — "no colour" is a design direction of its own, and it arrives two
    # //// ways: the client says it, or every site they point at is neutral (inspiration.
    # //// monochrome). Left to the brief, a black-and-white reference read back as the
    # //// browns and greys of its own photographs, and the site came out muddy.
    palette_mode = (spec.get("palette_mode") or "auto").strip().lower()
    if palette_mode == "auto" and not primary and monochrome(inspiration):
        palette_mode = "monochrome"
        ai_log("info", "Monochrome read from the inspirations", sources=len(inspiration.get("sources") or []))
    monochrome_prompt = ""
    if palette_mode == "monochrome":
        primary, secondary = primary or "#000000", None
        monochrome_prompt = (
            " PALETTE: no colour at all. Black, white and greys ONLY, on every page and in every section — "
            "no accent, no tinted background, no coloured button, and never a colour taken from the inspirations "
            "or from the logo. Contrast comes from the photographs, the type and the empty space."
        )
    # //// Neoffice ▼▼▼ — "less text" is a direction too (IMAGE_LED_PLANS), given as
    # //// copy_density or read off the brief's own words and the direction it chose
    copy_density = (spec.get("copy_density") or "auto").strip().lower()
    if copy_density not in ("standard", "minimal"):
        copy_density = "minimal" if wants_minimal_copy(spec.get("style_direction"), spec.get("differentiators"), activity) else "standard"
    density_prompt = (
        " COPY: minimal. The photographs carry the site: short headlines, one line at most under each, no paragraphs."
        if copy_density == "minimal" else ""
    )
    # //// Neoffice ▲▲▲
    prompt = f"{site_name}: {activity}. {spec.get('differentiators') or ''} Style: {spec.get('style_direction') or ''}{contact_prompt}{inspiration_prompt}{monochrome_prompt}{density_prompt}"

    # the client's own photographs, read into the session's library so the pages can be
    # laid out with them (placed at step 7, after the pages exist)
    library = {"taken": 0, "understood": 0}
    photos = clean_list(spec.get("photos"))
    if photos and getattr(ctx, "session_id", None):
        _progress(ctx, job_id, _("Reading your photos"), 7)
        try:
            from builder.site_ai.ingestion.content_understanding import ingest_and_understand

            library = ingest_and_understand(ctx.session_id, photos)
            ai_log("info", "Client library ready", **library)
        except Exception as e:
            ai_log("warning", "Client library skipped", error=str(e)[:200])
    # the pages are written with the client's own photographs (photos_for_page), and the
    # categories the brief names get their tiles and a link to the page that lists them
    client_photos = library_photos(getattr(ctx, "session_id", None), only=photos) if photos else []
    # the categories travel as their own list; the brief's own words are only the fallback
    categories = [str(c).strip() for c in (spec.get("categories") or []) if str(c).strip()][:8] or category_names(
        activity, spec.get("differentiators") or "", spec.get("style_direction") or ""
    )
    ai_log("info", "Client photos ready", photos=len(client_photos), categories=categories)
    photos_used: dict[str, int] = {}
    # //// Neoffice ▲▲▲
    settings = get_ai_settings()
    brief = None
    try:
        logo_url = (frappe.utils.get_url() + logo_image) if logo_image and logo_image.startswith("/") else logo_image
        # the page model: the same Kimi as the chat on its highspeed serving, so the brief's
        # minute of reasoning becomes seconds
        brief, validation = BriefGenerator(provider="litellm", model=_page_model(ctx), config=settings).generate_brief_with_validation(
            prompt=prompt,
            site_name=site_name,
            site_type=site_type,
            theme="modern",
            primary_color=primary,
            secondary_color=secondary,
            pages_config=pages,
            max_retries=2,
            logo_image=logo_url,
            inspiration_images=inspiration["images"] or None,
        )
        ai_log("info", "Design brief ready", tone=brief.site_tone, valid=validation.is_valid)
    except Exception as e:
        ai_log("warning", "Design brief failed, using defaults", error=str(e)[:200])
        frappe.log_error("Nora site build: design brief failed", frappe.get_traceback())
        # said where the user looks (a silent fallback hid a wrong model for weeks,
        # neoffice-maintenance #274)
        _update_generation_status(job_id, {"warning": _("The design brief failed; the site uses default styling.")})
        ctx.emit("progress", message=_("The design brief failed; the site uses default styling."))
        brief = get_default_brief(theme="modern", primary_color=primary, secondary_color=secondary)
    primary = primary or getattr(brief, "primary_color", None)
    secondary = secondary or getattr(brief, "secondary_color", None)

    # 4. the design system as tokens, and the chrome from the brief
    prefix = token_prefix(profile or site_name)
    handles = mint_tokens(prefix, profile or site_name, brief, primary, secondary)
    palette = palette_values(prefix)
    # //// Neoffice — see the block marker above: text made readable on background
    readable = ensure_readable_text(prefix, palette)
    if readable:
        ai_log("info", "Text token made readable on the background", value=readable)
    try:
        apply_brief_site_chrome(brief, website_profile=profile)
        config = _get_site_chrome_config(profile)
        if getattr(brief, "heading_font", None):
            config.heading_font = brief.heading_font
            config.body_font = brief.body_font or "Inter"
        # the chrome's variables alias the tokens from now on (theme_variables.html)
        if hasattr(config, "token_prefix"):
            config.token_prefix = prefix
        # the brief behind the site, shown under Settings > Theme ("what the AI decided")
        if hasattr(config, "ai_brief"):
            try:
                config.ai_brief = brief.model_dump_json() if hasattr(brief, "model_dump_json") else json.dumps(brief.__dict__, default=str)
            except Exception:
                pass
        # the four colour fields carry the token VALUES (a literal each): the brief's
        # own body_color is a CSS variable on a default brief, which left the Variant
        # with `text_color = var(--muted-color)` on the third complete run
        for field, key in (("primary_color", "primary"), ("secondary_color", "secondary"), ("background_color", "background"), ("text_color", "text")):
            value = palette.get(f"{prefix}-{key}")
            if value and hasattr(config, field):
                config.set(field, value)
        # //// Neoffice — move the header off a background close to a dominant logo colour, see inspiration.py (925e2366 "fix(nora): the header never wears one of the logo's own colours")
        # the header never wears one of the logo's own colours (inspiration.py)
        if logo_image and hasattr(config, "header_bg_color"):
            from builder.site_ai.nora.inspiration import header_off_logo_palette

            moved = header_off_logo_palette(config, logo_image, palette, prefix)
            if moved:
                ai_log("info", "Header colour moved off the logo palette", background=moved)
        config.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        ai_log("warning", "Chrome from brief failed", error=str(e)[:200])
    try:
        ctx.emit("refetch", resources=["variables"], after_commit=True)
    except Exception:
        pass

    # 5. the pages, on upstream's page engine
    layout_system = choose_layout_system(spec.get("style_direction"), brief)
    page_model = _page_model(ctx)
    site = {"site_name": site_name, "activity": activity, "differentiators": spec.get("differentiators"), "site_type": site_type, "profile": profile, "inspiration": inspiration["notes"], "copy_density": copy_density, "categories": categories}
    created, failed, cancelled = [], [], False

    # //// Neoffice — image generation was switched off (the pictures were not good enough):
    # //// gates the neutral-SVG fallback below (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
    images_on = _image_backend_available()

    def write_page(page: dict, photos: list[str], revision: str | None = None, notes: list[str] | None = None) -> tuple[list, str, str | None]:
        """One page through the writer and the mechanical passes: (blocks, data_script, error)."""
        brief_text = page_brief_text(site, brief, page, handles, contact_prompt, layout_system, language, photos, cta, palette=palette, revision=revision, photo_notes=notes)
        messages = [
            {"role": "system", "content": Prompts.GENERATION_YAML},
            {"role": "user", "content": f"Build this page now:\n{brief_text}"},
        ]
        blocks, data_script, error = [], "", None
        for attempt in range(2):
            try:
                raw = _stream_text(ctx, page_model, messages, llm.TASK_PARAMS["complex"])
                blocks, data_script = expand_page_yaml(BlockCodec.strip_fences(raw))
                if blocks:
                    # //// Neoffice — new call: repairs includes to the offered tag or drops them (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
                    # an include is one the brief offered, written as offered (a wrong
                    # path is a 417 at render time): see repair_includes
                    fixed, dropped = repair_includes(blocks, available_includes(page["type"], site["site_type"], site["profile"], site["site_name"]))
                    if fixed or dropped:
                        ai_log("info", "Includes repaired", page=page["title"], rewritten=fixed, removed=dropped)
                    # the page's own accent joins the design system (accent.py): minted
                    # from the first page that has one, every later one is folded into it
                    foreign = dominant_accent(blocks, palette)
                    if foreign:
                        if not handles.get("accent"):
                            handles["accent"] = mint_accent_token(prefix, profile or site_name, foreign)
                            palette[f"{prefix}-accent"] = foreign
                            ai_log("info", "Accent token minted", page=page["title"], value=foreign)
                        edits = rewrite_hex(blocks, {foreign: handles["accent"]})
                        ai_log("info", "Accent folded into the token", page=page["title"], value=foreign, edits=edits)
                    # nor the placement on the 12-column grid: see layout.py (a cards wrapper
                    # squeezed into one column)
                    placed = place_orphans(blocks)
                    if placed:
                        ai_log("info", "Grid orphans placed", page=page["title"], edits=placed)
                    hoisted = unwrap_grid_wrappers(blocks)
                    if hoisted:
                        ai_log("info", "Grid wrappers unwrapped", page=page["title"], edits=hoisted)
                    # //// Neoffice — a card repeater or card wrapper without a grid now stacks in a column
                    # //// (the trust section of a reseller site's home listed its four reasons as rows), and with
                    # //// image generation off every placehold.co slot becomes an inline SVG instead of a
                    # //// broken external image (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
                    stacked = grid_stacked_cards(blocks, repeater_counts(data_script))
                    if stacked:
                        ai_log("info", "Stacked cards laid on a grid", page=page["title"], edits=stacked)
                    # //// Neoffice — added: wire orphaned CTAs to real routes and repair button
                    # //// variants so a button never keeps the section's own colour (0d1ae82c
                    # //// "feat(design system): buttons that read anywhere, calls to action that
                    # //// lead somewhere, no client names in comments")
                    # a "Learn more" that goes nowhere, a card without the action its siblings
                    # carry, a primary button on a primary-coloured section: see buttons.py
                    from builder.site_ai.nora.buttons import repair_button_variants, repair_foreign_links, wire_dead_ctas

                    routes = ["/" if p["route"] in ("home", "index") else "/" + p["route"].lstrip("/") for p in pages]
                    routes.append("/login")
                    if _webshop_installed() and not _other_business(profile, site_name):
                        routes.append("/all-products")
                    if _profile_is_b2b(profile) and _account_request_route():
                        routes.append(_account_request_route())
                    wired = wire_dead_ctas(blocks, routes, cta[1])
                    if wired:
                        ai_log("info", "Calls to action wired", page=page["title"], edits=wired)
                    # //// Neoffice — on a multi-site instance a link pointing at another site's
                    # //// route is sent home: to the page its words match, or to the site's call
                    # //// to action; files, assets and external addresses are left alone
                    # //// (16a271e0 "feat(buttons): a link to another site's page comes home")
                    # a link to another site of the instance, or to a page that does not exist
                    # a category tile the model linked to a page the site does not have goes to
                    # the page that lists what the site offers, not to the contact form
                    listing = next((r for p, r in zip(pages, routes) if p["type"] == "shop" or re.search(r"brand|shop|catalog|collection|product|boutique|store|marque", f"{p['title']} {p['route']}", re.I)), None)
                    foreign = repair_foreign_links(blocks, routes, cta[1], categories=categories, listing=listing)
                    if foreign:
                        ai_log("info", "Foreign links brought home", page=page["title"], edits=foreign)
                    # the routes the data script hands to repeated blocks pass the same check
                    from builder.site_ai.nora.buttons import repair_data_routes

                    data_script, data_moved = repair_data_routes(data_script, routes, cta[1], categories=categories, listing=listing)
                    if data_moved:
                        ai_log("info", "Data script links brought home", page=page["title"], edits=data_moved)
                    variants = repair_button_variants(blocks, palette)
                    if variants:
                        ai_log("info", "Button variants repaired", page=page["title"], edits=variants)
                    # no photo will come: the slots become plain blocks in the site's colours
                    if not images_on:
                        neutral = neutral_placeholders(blocks, palette, prefix)
                        if neutral:
                            ai_log("info", "Photo slots neutralised", page=page["title"], edits=neutral)
                    # an interior page opens under the site's own title band (page_header.py)
                    if page["route"] != "home":
                        stripped = strip_title_band(blocks, page["title"])
                        if stripped:
                            ai_log("info", "Repeated title dropped", page=page["title"], edits=stripped)
                    # nor the type scale: see typography.py (a 210 px paragraph at 11vw)
                    capped = cap_font_sizes(blocks)
                    if capped:
                        ai_log("info", "Font sizes capped", page=page["title"], edits=capped)
                    # legibility is not left to the model: see contrast.py (#281)
                    fixes = repair_contrast(blocks, palette)
                    if fixes:
                        ai_log("info", "Contrast repaired", page=page["title"], fixes=len(fixes), first=fixes[0][:80])
                    # nor the spacing of French punctuation: see punctuation.py
                    if lang_code == "fr":
                        spaced = french_spacing(blocks)
                        if spaced:
                            ai_log("info", "French spacing applied", page=page["title"], edits=spaced)
                    # //// Neoffice — measured, so "less text" is a number and not an impression
                    ai_log("info", "Page copy measured", page=page["title"], words=page_word_count(blocks), density=site.get("copy_density"))
                if blocks:
                    break
                error = "the model returned no usable blocks"
            except Exception as e:
                error = str(e)[:200]
                ai_log("warning", "Page generation attempt failed", page=page["title"], attempt=attempt + 1, error=error)
        return blocks, data_script, error

    for idx, page in enumerate(pages):
        if ctx.is_cancelled():
            cancelled = True
            break
        _progress(ctx, job_id, _("Writing page {0} of {1}: {2}").format(idx + 1, total, page["title"]), 10 + int(80 * idx / max(total, 1)), {"current_page": page["title"], "pages_created": created})
        page_photos, page_notes = photos_for_page(page, client_photos, photos_used, categories, copy_density == "minimal")
        blocks, data_script, error = write_page(page, page_photos or placeholder_photos(page, activity), notes=page_notes or None)
        if not blocks:
            failed.append({"title": page["title"], "error": error})
            # //// Neoffice — title/message swapped to frappe's documented log_error(title,
            # //// message) order: the page title (unbounded length) was going in as the title,
            # //// over frappe's 140-char cap, making log_error itself raise (3171fff1 "fix(agent):
            # //// the error handler was killing the message it existed to deliver")
            frappe.log_error("Nora site build: page failed", f"{page['title']}: {error or 'no blocks'}")
            continue
        use_host = host_page if (host_reusable and page["route"] == "home") else None
        name, route = _write_page(page, blocks, data_script, profile, use_host, _describe(blocks))
        created.append({"name": name, "title": page["title"], "route": f"/{route}", "planned": page["route"]})
        ai_log("info", "Page written", page=page["title"], name=name, route=route, model=page_model)
        if use_host:
            try:
                # _write_page has committed: an after_commit emit would wait for the
                # NEXT commit, i.e. the next page four minutes later (seen on the third
                # complete run, canvas blank until then)
                ctx.emit("refetch", resources=["page", "page_data", "canvas"], after_commit=False)
            except Exception:
                pass

    if not created:
        _update_generation_status(job_id, {"status": "failed", "progress": 0, "error": "no page could be generated", "pages_created": []})
        return "FAILED: no page could be generated (" + "; ".join(f"{f['title']}: {f['error']}" for f in failed) + "). Tell the user and offer to try again."

    # the pages written beside kept pages that held their planned routes were suffixed at
    # write time: their links, and the call to action, move to the routes they really got
    config = _get_site_chrome_config(profile)
    moved = moved_routes(created)
    if moved:
        repointed = _repoint_moved_links(created, moved)
        if (config.get("cta_url") or "") in moved:
            config.cta_url = moved[config.cta_url]
        ai_log("warning", "Pages written beside kept pages holding their routes", moved=moved, links=sum(len(v) for v in repointed.values()))

    # 6. menu, footer, home
    _progress(ctx, job_id, _("Menu, footer and home page"), 92, {"pages_created": created})
    apply_navigation(config, created, site_type, activity, profile, lang_code, site_name=site_name)

    # 7. the images: the client's own photographs first, drawings only for what is left
    # //// Neoffice ▼▼▼ — a client who supplies photographs wants THEM on the page, and a
    # //// drawn stand-in beside them is the tell that nobody read the brief. The library
    # //// (Builder Content Asset) and its matcher already existed for the old onboarding
    # //// wizard and no caller reached them; the build now places from the library, then
    # //// draws only the slots no photograph fits.
    placed = 0
    if client_photos:
        try:
            _progress(ctx, job_id, _("Placing your photos"), 90, {"pages_created": created})
            from builder.site_ai.ingestion.image_matcher import match_and_apply

            report = match_and_apply(ctx.session_id, [p["name"] for p in created])
            placed = report.get("matched") or 0
            ai_log("info", "Client photos placed", placed=placed, slots=report.get("slots"), assets=report.get("assets"))
        except Exception as e:
            ai_log("warning", "Client photos not placed", error=str(e)[:200])
    # //// Neoffice ▲▲▲
    pending, image_job = 0, None
    try:
        slots = _scan_placeholder_images([p["name"] for p in created], subject=activity[:180])
        pending = len(slots)
        if slots and _image_backend_available():
            image_job = _enqueue_image_generation(slots)
    except Exception as e:
        ai_log("warning", "Image generation not started", error=str(e)[:200])

    # 8. the final look: each page rendered, screenshotted and read against the brief by the
    # vision model; the body defects come back as one revision pass (visual_check.py)
    reviews, revised = [], {}
    if created and not cancelled and visual_check.enabled():
        try:
            _progress(ctx, job_id, _("Visual check: waiting for the images"), 95, {"pages_created": created})
            # //// Neoffice — the text-to-image backend answers in 60 to 70 s per picture (Codex behind the ComfyUI proxy): the wait budget follows the number of slots (77601a8e "fix(images): prompts with photographic direction only, and budgets sized on the slot count")
            # a picture takes 60 to 70 s on the Codex backend: the wait follows the slot count
            visual_check.wait_for_images(image_job, timeout=min(1800, max(visual_check.IMAGE_WAIT_SECONDS, 75 * pending + 120)))
            by_name = {p["name"]: p for p in pages_by_name(pages, created)}
            for item in created:
                if ctx.is_cancelled():
                    break
                _progress(ctx, job_id, _("Visual check: {0}").format(item["title"]), 96, {"pages_created": created})
                reviews.append(visual_check.review_page(item, profile, page_model, site_name=site_name, activity=activity))
            # the pages that failed the first glance first, then the ones with most defects
            todo = sorted(
                [r for r in reviews if r["issues"] and r["name"] in by_name],
                key=lambda r: (r["professional"] is not False, -len(r["issues"])),
            )[: visual_check.MAX_REVISIONS]
            for r in todo:
                if ctx.is_cancelled():
                    break
                _progress(ctx, job_id, _("Fixing {0} after the visual check").format(r["title"]), 97, {"pages_created": created})
                page = by_name[r["name"]]
                current = frappe.db.get_value("Builder Page", r["name"], "blocks") or ""
                # the photographs the page already carries, the client's own included, not only the drawn ones
                photos = list(dict.fromkeys(re.findall(r"/files/[^\"'\s)]+?\.(?:jpe?g|png|webp)", current))) or placeholder_photos(page, activity)
                blocks, data_script, error = write_page(page, photos, revision=visual_check.revision_instructions(r["issues"]))
                if not blocks:
                    ai_log("warning", "Revision pass failed", page=r["title"], error=error)
                    continue
                _write_page(page, blocks, data_script, profile, r["name"], _describe(blocks))
                revised[r["name"]] = len(r["issues"])
                ai_log("info", "Page revised after the visual check", page=r["title"], issues=len(r["issues"]))
            if revised:
                slots = _scan_placeholder_images([n for n in revised])
                if slots:
                    _enqueue_image_generation(slots)
                    ai_log("info", "Images re-queued after the revision pass", slots=len(slots))
        except Exception as e:
            ai_log("warning", "Visual check skipped", error=str(e)[:200])

    duration = int(time.time() - started)
    _update_generation_status(job_id, {
        "status": "completed", "progress": 100, "total_pages": total, "current_step": "Completed", "current_page": None,
        "pages_created": created, "remaining_image_slots": pending, "image_job_id": image_job, "error": None,
        "site_name": site_name, "completed_at": now(), "duration_seconds": duration,
    })
    ai_log("info", "=== NORA SITE BUILD COMPLETED ===", job_id=job_id, pages=len(created), failed=len(failed), duration=duration)
    lines = [f"DONE in {duration // 60} min {duration % 60} s. Site '{site_name}'" + (f" on profile '{profile}'" if profile else "") + ":"]
    lines += [f"- {p['title']} -> {p['route']} (page {p['name']})" for p in created]
    # //// Neoffice — new: tells the model its just-written routes are final, so it stops "correcting" them post-build (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
    lines.append("These routes are final: do not rename a page or change a route after this build, and do not rewrite the menu or the footer links, they already point at these routes.")
    if failed:
        lines.append("Pages that failed (offer to retry them one by one with generate_page on their page): " + ", ".join(f"{f['title']} ({f['error']})" for f in failed))
    if cancelled:
        lines.append("The build was cancelled by the user before every page was written.")
    lines.append(f"Design tokens minted with prefix '{prefix}': " + ", ".join(handles.values()) + ".")
    # //// Neoffice — reports the neutral-SVG fallback when image generation is off, instead of
    # //// always claiming a background image job is filling the slots (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
    # //// Neoffice — the client's own photographs come first, and what they filled is said
    # //// before anything about drawn images (see step 7).
    if client_photos:
        lines.append(
            f"{len(photos_used)} of the client's {len(client_photos)} photographs were laid into the pages as they were "
            f"written; {placed} leftover photo slot(s) were filled with them afterwards."
        )
    if image_job:
        lines.append(f"{pending} photo slot(s) are being filled with generated images in the background (job {image_job}).")
    # //// Neoffice — "elif pending" instead of "else": the client's own photographs may
    # //// already have filled every slot, and the old "image generation is off" line no
    # //// longer applies then (918629eb "feat(site build): the client's own photographs, every reference site, and a monochrome direction")
    elif pending:
        lines.append("Image generation is off: the photo slots hold plain blocks in the site's colours, to be replaced by the client's own pictures.")
    # //// Neoffice — reports the monochrome direction in the build summary, whether the
    # //// client asked for it or it was read off the inspirations (918629eb "feat(site build): the client's own photographs, every reference site, and a monochrome direction")
    if palette_mode == "monochrome":
        lines.append("The palette is monochrome: black, white and greys only, as asked.")
    if copy_density == "minimal":
        lines.append("The copy is minimal: short headlines and one line at most per section, the photographs carry the pages.")
    if host_reusable and any(p["name"] == host_page for p in created):
        lines.append("The page open in the editor is now the home page; the canvas has been refreshed.")
    lines.append("The header, the menu and the footer are set from the brief (Settings > Theme).")
    lines += visual_check.summary_lines(reviews, revised)
    return "\n".join(lines)
