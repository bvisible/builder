# //// Neoffice — added file (no upstream equivalent): the site pipeline behind the generate_site tool.
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
    # //// Neoffice — the legal pages are pages like the others (2026-09-15): a shop that carries
    # //// neither its terms nor its privacy policy cannot trade — no payment provider and no ad
    # //// network accepts it — so they are planned, written and linked in the footer like the rest.
    "conditions generales": ("terms-conditions", "legal"), "conditions generales de vente": ("terms-conditions", "legal"),
    "cgv": ("terms-conditions", "legal"), "cgu": ("terms-conditions", "legal"),
    "terms": ("terms-conditions", "legal"), "terms conditions": ("terms-conditions", "legal"),
    "terms and conditions": ("terms-conditions", "legal"), "agb": ("terms-conditions", "legal"),
    "politique de confidentialite": ("privacy-policy", "legal"), "confidentialite": ("privacy-policy", "legal"),
    "privacy": ("privacy-policy", "legal"), "privacy policy": ("privacy-policy", "legal"),
    "datenschutz": ("privacy-policy", "legal"),
    "mentions legales": ("legal-notice", "legal"), "legal notice": ("legal-notice", "legal"),
    "impressum": ("legal-notice", "legal"),
}

# a section asking for proof, figures, prices or people is filled from the brief or left out: asked
# for "proof: testimonials, figures" and "three plans side by side", a practice about to open came
# out with a patient's testimonial, three prices and a "most chosen" badge, and its contact page
# with a drawn access map showing a street address nobody gave (2026-09-13)
SECTION_PLANS = {
    "accueil": [
        "hero: the site's promise in one line, a supporting sentence and the main CTA",
        "three or four value propositions with Lucide icons",
        "the featured services or products, one card each",
        "an about teaser with a photo and a link to the About page",
        "proof, only what the brief gives: its testimonials, figures, clients or partners by name (no such section when it gives none)",
        "a final CTA band",
    ],
    "about": ["the story and the mission", "values, three of them", "the team or the founder", "milestones or key figures the brief gives (none when it gives none)", "a CTA"],
    "services": ["the services, one detailed card each", "how it works in three steps", "what is included / packages", "three FAQ entries", "a CTA"],
    "contact": [
        "the contact details from BUSINESS DATA, verbatim: address, phone, email, opening hours",
        "a contact form: name, email, message, one submit button",
        "how to find the place, in words, from the address in BUSINESS DATA",
        "a CTA to call or write",
    ],
    "faq": ["an intro line", "eight questions and answers grouped by theme", "a CTA to contact"],
    "team": ["an intro", "the team members the brief names, as cards with photo placeholders", "a CTA to contact"],
    "blog": ["an intro", "three article teasers with placeholder photos", "a newsletter or CTA band"],
    "testimonials": ["an intro", "the testimonials the brief gives, one card each (without any: an invitation to share one, never a made-up quote)", "a CTA"],
    "shop": ["an intro to the catalogue", "featured products with placeholders", "why buy here", "a CTA to the products list at /all-products"],
    "pricing": ["an intro", "the prices the brief gives, as plans or a list (without prices in the brief: how prices are set and how to get one, no amount)", "what is included", "FAQ", "a CTA"],
    "portfolio": ["an intro", "a project grid with placeholder photos", "the way of working", "a CTA"],
    "features": ["an intro", "the features as an alternating rows layout with icons", "a comparison, or figures the brief gives", "a CTA"],
    "one_page": ["hero", "services", "about", "proof the brief gives (none when it gives none)", "contact details and form", "final CTA"],
    "generic": ["an intro", "the page's content in two or three sections", "a CTA"],
    # //// Neoffice — a legal page is read, not looked at (2026-09-15): no hero, no photograph, no
    # //// CTA band. Headings and paragraphs, numbered clauses, and the merchant's own details from
    # //// BUSINESS DATA — never a company number, a jurisdiction or a provider nobody gave.
    "legal": [
        "an intro: what this document covers and the date it takes effect",
        "the clauses, each one a heading and its paragraphs, numbered, in the order the law of the "
        "site's country reads them",
        "who to write to: the details from BUSINESS DATA, verbatim",
    ],
    # //// Neoffice — a legal page is one column of reading (2026-09-15): written with the site's
    # //// two-column habit, the first one came out with its clauses squeezed into the left third
    # //// of the screen and the right half empty, and a numeral of the logo stamped over every
    # //// heading. The plan above is the content; this is its shape.
}

# //// Neoffice ▼▼▼ — an image-led site: the photographs carry the page and the copy steps
# //// back to names and a line. A brief saying "less is more", "not much text", "people
# //// consume through the image" still got the standard plan above: value propositions
# //// with icons, testimonials, an about teaser, every one of them a paragraph
# //// (2026-09-10). These plans build the same pages out of pictures.
# //// Neoffice — few words is not few shapes (2026-09-15). These plans were a stack of full-bleed
# //// photographs with a black bar under each name, on every page: "c'est comme si on n'avait jamais
# //// travaillé sur une cohérence graphique". The copy stays minimal; the composition comes back —
# //// tiles of unequal weight, a two-column band, a quiet strip — and a name sits ON its photograph.
IMAGE_LED_PLANS = {
    "accueil": [
        "hero: one full-bleed photograph, the site's name or promise in two to five words over it, one button",
        "who they are: a short introduction, a heading of a few words and two or three lines saying what the place "
        "is and what it carries — a visitor who lands here must know what this is",
        "the categories, segments or collections the activity names, as photo tiles of unequal weight — one large "
        "beside smaller ones — each showing its name ON the photograph over a veil, never in a bar under it",
        "a two-column band: a statement of three to eight words in large type on one side, one photograph on the other",
        "the brands the brief names, as one quiet row of their names (no such section when it names none)",
        "one wide photograph with a single short line over it (at most twelve words)",
        "a closing band: one line and one button",
    ],
    "shop": [
        "the collections as photo tiles of unequal weight, each name ON its photograph",
        "a strip of products",
        "a two-column band: one short line beside one photograph",
        "one line and a button",
    ],
    "about": [
        "one large photograph of the people, with the name or one short line over it",
        "two columns: three short lines on who they are on one side, one photograph on the other",
        "the categories or segments the brief names, one photo tile each, the name ON the photograph",
        "a quiet strip: the brands the brief names, or three short facts it gives (nothing invented; none given: no such section)",
        "one line and a button",
    ],
    "contact": ["the contact details from BUSINESS DATA, verbatim, with no introduction", "a contact form: name, email, message, one submit button"],
    "generic": [
        "one large photograph with the page's point in one line over it",
        "the content as photo tiles with short captions, each caption ON its photograph",
        "a two-column band: one short line beside one photograph",
        "one line and a button",
    ],
}
# //// Neoffice — a brands page shows the brands the brief names (2026-09-14): given inside the
# //// activity, they never reached an image-led brands page, which laid out the site's segments
# //// and named no brand. The categories keep their tiles below, where the home's tiles lead.
BRAND_WORDS = re.compile(r"\bbrands?\b|\bmarques?\b|\bmarken\b", re.I)
BRAND_PLAN = [
    "an intro line",
    "the brands the brief names, one card each: the brand's name as its title and one line on what it makes",
    "the categories the brief names, one card each with its photograph (none named: no such section)",
    "a CTA",
]
BRAND_PLAN_IMAGE_LED = [
    "the brands the brief names, as a grid of cards, two or three to a row: the brand's name as the card's title, "
    "one short line under it, and its logo when the brief gives one",
    "one wide photograph with a single short line over it",
    "the categories the brief names, one photo tile each, the name ON the photograph (none named: no such section)",
    "one line and a button",
]


def brands_page(page: dict) -> bool:
    return page.get("type") == "brands" or bool(BRAND_WORDS.search(f"{page.get('title', '')} {page.get('route', '')}"))


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


def pages_to_replace(classes: dict, replace_existing: str, routes: set[str] | None = None) -> list[str]:
    """The existing pages a build replaces: the untouched AI pages unless the user keeps
    everything ('none'), the hand-made ones too only when they said so ('force').

    'keep_edited' is what "keep them" means after a CONFIRM_NEEDED: the hand-made pages
    stay and the rest goes as usual. Answered with 'none', a question about one page kept
    the whole previous site beside the new one: two home pages, the new pages' routes
    suffixed, their calls to action on the old contact page (2026-09-11).

    //// Neoffice — `routes` added 2026-09-15: a build of ONE page asked to replace what it
    replaces, and got back every AI page of the site. Rebuilding a privacy policy would have
    deleted the home, the brands, the about and the contact to write it — with the default
    setting, and without a word. When the build writes only part of the site (scope="pages"),
    it replaces only the routes it writes; the rest is not its business."""
    if replace_existing == "none":
        return []
    pages = list(classes.get("untouched") or [])
    if replace_existing == "force":
        pages += list(classes.get("protected") or [])
    if routes is not None:
        pages = [p for p in pages if str(p.get("route") or "").strip("/") in routes]
    return [p["name"] for p in pages]


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
        _write_token(doc_id, label, ttype, value, group)
        handles[key] = f"var(--{doc_id})"
    frappe.db.commit()
    return handles


# //// Neoffice — a token collision does not kill a build (2026-09-15). Two builds running at once on
# //// the same instance — two operators, or one relaunched — write the same six token documents, and
# //// the loser died on TimestampMismatchError in step 4, twenty-five minutes of work thrown away for
# //// a colour that both were writing the same way. The write is retried on the fresh document.
def _write_token(doc_id: str, label: str, ttype: str, value, group: str) -> None:
    """Writes one Builder Token, retrying once on a concurrent write."""
    fields = {"type": ttype, "value": value, "token_name": label, "group": group}
    for attempt in (1, 2):
        try:
            if frappe.db.exists("Builder Token", doc_id):
                doc = frappe.get_doc("Builder Token", doc_id)
                doc.update(fields)
                doc.save(ignore_permissions=True)
            else:
                frappe.get_doc({"doctype": "Builder Token", **fields}).insert(ignore_permissions=True, set_name=doc_id)
            return
        except (frappe.TimestampMismatchError, frappe.DuplicateEntryError):
            if attempt == 2:
                raise
            frappe.db.rollback()


# //// Neoffice ▼▼▼ — the site grid the chrome shares with the pages (2026-09-14). Header, footer and top
# //// page band sat on 1280 px / 24 px while an editorial grid's pages sat on 1440 px / 48 px: a 36 px
# //// staircase at 1400 px, and 16 px against 24 px on a phone. The container of each layout system
# //// (builder/ai/prompts.py, "Layout systems") becomes three Dimension tokens that the chrome reads
# //// (theme_variables.html) and that the pages are told to use (site_grid_line).
SITE_GRIDS = {
    "editorial-grid": ("1440px", "48px"),
    "classic-centered": ("1200px", "64px"),
    "bento": ("1280px", "24px"),
}
DEFAULT_GRID = ("1280px", "24px")
# the craft floor's section padding on a phone, '64px 24px' (builder/ai/prompts.py)
PHONE_GUTTER = "24px"


def site_grid(layout_system: str) -> dict:
    """The container width, the gutter and the phone gutter of a layout system."""
    width, gutter = SITE_GRIDS.get(layout_system, DEFAULT_GRID)
    return {"container": width, "gutter": gutter, "gutter-phone": PHONE_GUTTER}


def mint_grid_tokens(prefix: str, group: str, layout_system: str) -> dict:
    """The site grid as three Dimension tokens with stable ids; returns their handles."""
    handles = {}
    for key, value in site_grid(layout_system).items():
        doc_id = f"{prefix}-{key}"
        label = f"{group} {key.replace('-', ' ').title()}"
        if frappe.db.exists("Builder Token", doc_id):
            doc = frappe.get_doc("Builder Token", doc_id)
            doc.update({"type": "Dimension", "value": value, "token_name": label, "group": group})
            doc.save(ignore_permissions=True)
        else:
            frappe.get_doc(
                {"doctype": "Builder Token", "token_name": label, "type": "Dimension", "value": value, "group": group}
            ).insert(ignore_permissions=True, set_name=doc_id)
        handles[key] = f"var(--{doc_id})"
    frappe.db.commit()
    return handles


def site_grid_line(handles: dict) -> str:
    """The page brief's line on the site grid, when the site has one."""
    if not handles.get("container"):
        return ""
    return (
        f"SITE GRID: when a section has an inner container, it is maxWidth {handles['container']}, margin '0 auto', "
        f"paddingLeft and paddingRight {handles['gutter']} (m_style {handles['gutter-phone']}). The header, the top page "
        "band and the footer sit on this grid, so the content lines up with them."
    )
# //// Neoffice ▲▲▲


def placeholder_photos(page: dict, activity: str, categories=(), listing: bool = False) -> list[str]:
    """The photo slots a page is written with when the client gave no photograph. The home and
    the page that lists the offer get one per category besides: given two for four services, a
    practice's services grid came out with photos on some cards and icons on the others
    (2026-09-13)."""
    subject = (activity or "").strip()[:60] or page["title"]
    shots = {
        "accueil": [f"{subject}, hero", f"{subject}, in action", f"{subject}, team"],
        "about": [f"{subject}, at work", f"{subject}, workshop"],
        "services": [f"{subject}, service detail", f"{subject}, result"],
        "contact": [f"{subject}, storefront", f"{subject}, welcome"],
        "team": [f"{subject}, team member portrait", f"{subject}, team member portrait 2", f"{subject}, team member portrait 3"],
        "blog": [f"{subject}, article 1", f"{subject}, article 2", f"{subject}, article 3"],
        "portfolio": [f"{subject}, project 1", f"{subject}, project 2", f"{subject}, project 3", f"{subject}, project 4"],
        "shop": [f"{subject}, product 1", f"{subject}, product 2", f"{subject}, product 3"],
        "one_page": [f"{subject}, hero", f"{subject}, in action", f"{subject}, storefront"],
    }.get(page["type"], [f"{subject}, {page['title']}"])
    # one slot per category where the categories are shown, after the page's first photograph
    if categories and (page["type"] == "accueil" or listing):
        shots = [shots[0], *(f"{subject}, {name}" for name in categories), *shots[1:2]]
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
# //// Neoffice — "legal": 0 (2026-09-15): terms and a privacy policy are read, and a
# //// photograph on them spends one of the client's pictures to decorate small print.
PAGE_PHOTO_COUNT = {"about": 2, "contact": 1, "shop": 3, "portfolio": 4, "services": 3, "legal": 0}

# //// Neoffice ▼▼▼ — what each page is looking for in a photograph (2026-09-15). The page type and
# //// the title alone matched nothing in what the vision read of the client's pictures ("about
# //// about"), so a page took whatever was left: a workshop scene opened the page about the people
# //// who run the shop. These words are matched against what each photograph shows.
PAGE_PHOTO_WORDS = {
    "about": ("team", "crew", "people", "staff", "portrait", "workshop", "shop", "store"),
    "contact": ("shop", "store", "front", "entrance", "counter", "building", "street"),
    "team": ("team", "crew", "people", "staff", "portrait"),
    "services": ("work", "hands", "tool", "detail", "workshop"),
    "shop": ("product", "shelf", "rack", "display", "shop", "store"),
    "testimonials": ("people", "customer", "portrait"),
}
# //// Neoffice ▲▲▲

# a business whose contact details nobody verified gets none written: asked for "clearly
# generic placeholders the client will replace", the model wrote a real Zurich street and a
# plausible phone number, a different one at each build, on a contact page published at once
# (2026-09-12)
UNVERIFIED_CONTACT = (
    " Contact details: none are verified for this business. Write no address, phone number or e-mail anywhere on "
    "the site, not even a placeholder (a visitor takes a made-up one for real), and never another company's name, "
    "logo, address or e-mail: the contact form is the way to reach it."
)


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
        fields=["file", "original_filename", "summary", "tags", "orientation", "quality", "extracted_text", "suggested_section", "understanding"],
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
                "has_text": bool((row.extracted_text or "").strip()) or _vision_saw_text(row.understanding),
            }
        )
    return photos


def _vision_saw_text(understanding) -> bool:
    """Whether the vision pass found the picture carrying text (ImageUnderstanding's
    contains_text). A photograph's reading lives in `understanding`; `extracted_text` is a
    document's only: read from it alone, a beach photograph lettered "Thank You!" counted as
    plain and went onto a category tile (2026-09-12)."""
    try:
        return bool(json.loads(understanding or "{}").get("contains_text"))
    except (TypeError, ValueError, AttributeError):
        return False


LISTING_WORDS = re.compile(r"brand|shop|catalog|collection|product|boutique|store|marque", re.I)


def listing_page(pages: list[dict]) -> dict | None:
    """The page that shows what the site offers (a shop, the brands, the collections): where
    a category tile leads, and a page that shows each category with its own photograph."""
    return next((p for p in pages if p.get("type") == "shop" or LISTING_WORDS.search(f"{p.get('title', '')} {p.get('route', '')}")), None)


# //// Neoffice — a category word and a photograph's word are the same word when one begins the
# //// other (2026-09-18). The categories are nouns ("Snowboard") and the vision files verbs and
# //// gerunds ("snowboarding", "skateboarding", "surfing"): matched on equality, four photographs
# //// of riders in powder scored ZERO for the Snowboard tile, which went to a brand's product shot
# //// that merely mentioned the word in its description. Four letters at least, so "sur" does not
# //// catch "surface".
def _filed_under(word: str, words) -> bool:
    if word in words:
        return True
    if len(word) < 4:
        return False
    return any(len(other) >= 4 and (other.startswith(word) or word.startswith(other)) for other in words)


def _best_photo(library: list[dict], used: dict, wanted=(), landscape=None, avoid=frozenset(), must_fit: bool = False) -> dict | None:
    """The client's photograph that fits `wanted` best, counted as used.

    //// Neoffice — `must_fit` (2026-09-18): nothing rather than anything. max() always returns a
    photograph, even when not one in the library has a word in common with what was asked, so a
    SNOWBOARD tile was given a brand's product shot of a pink plush toy and a SKATE tile a picture
    of a crowd — the judge read the home and said the images do not match their labels. Where the
    caller labels what it shows, a picture that is not about it is worse than no picture."""
    # a picture carrying text (a banner, an advert) goes nowhere while anything else is left
    pool = [p for p in library if not p["has_text"]] or library
    if landscape is not None:
        pool = [p for p in pool if p["landscape"] == landscape] or pool

    def fit_of(p):
        # the client's own filing (file name, tags, section) outweighs a word the vision
        # used in passing, and a photograph filed under another category steps back: a
        # painting "in street-art style" filed under Home won the Street tile over three
        # street photographs, on quality alone (2026-09-12). Filed under the category, a
        # photograph already shown still beats one that is not about it.
        return sum(4 if _filed_under(w, p["words"]) else 1 if w in p["text"] else 0 for w in wanted) - 2 * len(avoid & p["words"])

    def rank(p):
        return fit_of(p) + {"high": 1.0, "medium": 0.5}.get(p["quality"], 0) - 3 * used.get(p["url"], 0)

    best = max(pool, key=rank)
    if must_fit and fit_of(best) <= 0:
        return None
    used[best["url"]] = used.get(best["url"], 0) + 1
    return best


def photos_for_page(page: dict, library: list[dict], used: dict, categories: list[str], minimal: bool, listing: bool = False) -> tuple[list[str], list[str]]:
    """The client's photographs a page is written with, and what each is for.

    The home gets its hero, one photograph per category the brief names (matched on what
    the vision read in it, else the best left), and a wide one. The page that lists the
    offer (`listing`) shows each category with its own photograph too: given two, it drew
    four of its five category panels as flat colour (2026-09-12). A photograph carrying
    text never opens a page, and the ones already used go last, so the pages do not repeat
    each other."""
    if not library:
        return [], []

    category_words = {w for name in categories for w in re.split(r"[^a-z0-9]+", name.lower()) if len(w) > 2}

    def take(wanted=(), landscape=None, avoid=frozenset(), must_fit: bool = False) -> dict | None:
        return _best_photo(library, used, wanted, landscape, avoid, must_fit)

    # the category tiles choose first: each needs one precise photograph, the hero any good
    # one (served first, the hero took the only snow picture and the snow tile got the banner)
    tiles = []
    if categories and (page["type"] == "accueil" or listing):
        for name in categories:
            wanted = [w for w in re.split(r"[^a-z0-9]+", name.lower()) if len(w) > 2]
            # //// Neoffice — the tile of a category shows that category or nothing (2026-09-18):
            # //// a SNOWBOARD tile was given a brand's pink plush toy, a SKATE tile a crowd
            tiles.append((take(wanted, avoid=category_words - set(wanted), must_fit=True), f"the tile of '{name}'"))
    if page["type"] == "accueil":
        picks = [(take(landscape=True), "the hero, full bleed"), *tiles, (take(landscape=True), "a wide photograph")]
    elif tiles:
        picks = [(take(landscape=True), "the first photograph of the page"), *tiles]
    else:
        # //// Neoffice — the page's own subject, in words (2026-09-15): "about about" matched nothing
        # //// in what the vision read, so the About page took whatever was left — a workshop scene,
        # //// on a page about the people who run the shop. PAGE_PHOTO_WORDS says what each page is
        # //// looking for; the title and the type stay in the list, they sometimes carry it.
        wanted = [w for w in re.split(r"[^a-z0-9]+", f"{page['title']} {page['type']}".lower()) if len(w) > 2]
        wanted += list(PAGE_PHOTO_WORDS.get(page["type"], ()))
        picks = [(take(wanted), "the first photograph of the page" if i == 0 else "a photograph") for i in range(PAGE_PHOTO_COUNT.get(page["type"], 2))]
    urls, notes = [], []
    for photo, role in picks:
        if photo is None or photo["url"] in urls:
            continue
        urls.append(photo["url"])
        notes.append(f"{role}; it shows: {photo['shows']}" if photo["shows"] else role)
    return urls, notes


# //// Neoffice — the photograph of each category, for the whole site (2026-09-14): only the home and the
# //// listing page were handed one per category, and an About page that showed the five categories as
# //// tiles drew four of them in flat grey beside one photograph. Every page that shows the categories
# //// as tiles is now told each one's photograph (page_brief_text), and layout.complete_tile_photos
# //// completes a grid the model still leaves half photographed.
def category_photo_map(library: list[dict], categories: list[str]) -> dict[str, str]:
    """The photograph of each category, chosen as the home's tiles are (_best_photo): filed under the
    category first, a different one for each while the library allows."""
    if not library or not categories:
        return {}
    category_words = {w for name in categories for w in re.split(r"[^a-z0-9]+", name.lower()) if len(w) > 2}
    used: dict[str, int] = {}
    mapping = {}
    for name in categories:
        wanted = [w for w in re.split(r"[^a-z0-9]+", name.lower()) if len(w) > 2]
        # //// Neoffice — a tile is ABOUT its category or carries no photograph (2026-09-18)
        chosen = _best_photo(library, used, wanted, avoid=category_words - set(wanted), must_fit=True)
        if chosen:
            mapping[name] = chosen["url"]
    return mapping


def revision_photos(planned: list[str], planned_notes: list[str], blocks_json: str | None, data_script: str | None) -> tuple[list[str], list[str] | None]:
    """The photographs a revision writes with: the ones the page was written with, keeping
    their roles (the tile of each category), then any other the page carries, its data
    script included. Read from the blocks alone, a revised home lost the tile photographs
    its data script held and drew three of its five tiles as gradients (2026-09-12)."""
    found = re.findall(r"/files/[^\"'\s)]+?\.(?:jpe?g|png|webp)", f"{blocks_json or ''}\n{data_script or ''}")
    photos = list(dict.fromkeys([*(planned or []), *found]))
    return photos, (list(planned_notes) if planned and planned_notes else None)


# Jinja includes a page may carry, by page type: the site's own components (a
# working contact form, a map, a team grid) and, where the shop app is installed,
# its live widgets. The old generator listed them per page in its system prompt
# (site_ai/prompts/system_prompts.py); the page brief does the same for the
# upstream page writer. An include is the innerHTML of its own plain block: the
# Builder renderer runs Jinja on block content, so the widget appears at render.
# an include listed here is REQUIRED on its page: the model wrote its own <form> on the
# Contact page of the B2B regeneration, five inputs that post nowhere
# //// Neoffice — PAGE_INCLUDES, REQUIRED_INCLUDES and CAROUSEL_TITLE lived here until 2026-09-15:
# //// seven frozen tag strings that were the generator's whole knowledge of what a page could
# //// carry. They are the component catalogue now (builder/site_ai/components.py), declared by
# //// each app in its own hooks.py, with the parameters each component takes.
# //// Neoffice ▼▼▼ — new: an include a page carries must be the one the brief offered, written exactly as offered; the model wrote the shop's opening hours with builder's path instead of webshop's and the Contact page of a reseller site answered 417 for a template it could not find (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
INCLUDE_TAG = re.compile(r"\{%-?\s*include\s+['\"]([^'\"]+)['\"]\s*-?%\}")
ALWAYS_ALLOWED_INCLUDES = ("{% include 'builder/templates/includes/contact_form.html' %}",)


def repair_includes(blocks: list, allowed) -> tuple[int, int]:
    """A page keeps a component it was offered, with the parameters it chose; anything else goes.

    //// Neoffice — rewritten 2026-09-15. This used to rewrite every include back to the exact
    string the brief offered, which is how a generator told "title of your choice" got its title
    replaced at every build, and why no parameter of any component was reachable. It now asks the
    catalogue: a tag whose component was offered to this page is kept, minus the parameters that
    component does not declare; a tag for a component this page was not offered is removed, which
    is the rule that mattered — the Contact page of a reseller site answered 417 for a template it
    could not find (2026-09-09). Returns (rewritten, removed)."""
    from builder.site_ai import components as catalogue
    from builder.site_ai.nora.layout import _walk

    # //// Neoffice — the file name comes from the include's PATH, not from rsplit on the whole
    # //// tag: that kept the trailing quote ("contact_form.html' %}") and the form was removed
    # //// from every page as an include nobody had offered.
    always = {m.group(1).rsplit("/", 1)[-1] for t in ALWAYS_ALLOWED_INCLUDES if (m := INCLUDE_TAG.search(t))}
    # //// Neoffice — a component the catalogue no longer holds (its app was uninstalled between
    # //// the offer and the write) comes through as None: it is simply not offered, and it must
    # //// not take the page write down with an AttributeError.
    offered = {c.file for c in allowed if c is not None} | always
    rewritten = removed = 0
    for block in _walk(blocks):
        kids = [c for c in (block.get("children") or []) if isinstance(c, dict)]
        kept = []
        for child in kids:
            html = child.get("innerHTML") if isinstance(child.get("innerHTML"), str) else ""
            found = INCLUDE_TAG.search(html) if html and "include" in html else None
            if not found:
                kept.append(child)
                continue
            if found.group(1).rsplit("/", 1)[-1] not in offered:
                removed += 1
                continue
            clean = catalogue.clean_tag(html)
            if clean is None:
                # catalogued nowhere but always allowed (the contact form): keep it as offered
                clean = next((t for t in ALWAYS_ALLOWED_INCLUDES if found.group(1) in t), html)
            if html.strip() != clean:
                child["innerHTML"] = clean
                rewritten += 1
            kept.append(child)
        if len(kept) != len(block.get("children") or []):
            block["children"] = kept
    return rewritten, removed
# //// Neoffice ▲▲▲


def components_prompt(components) -> str:
    """The COMPONENTS section of a page brief, written from the catalogue."""
    from builder.site_ai import components as catalogue

    return catalogue.prompt_block(components)


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


# //// Neoffice — a storefront shows what a storefront has (2026-09-15). A B2C site of the instance's
# //// own business was built with no shop in its menu, no cart and no account: only an "ecommerce"
# //// site type or a B2B profile got them, and the model had chosen another type. The profile's kind
# //// says it — B2B or B2C is a storefront, whatever the type the model picked.
def _profile_sells(profile: str | None) -> bool:
    """Whether the profile is a storefront: a site whose visitors browse a catalogue and order."""
    if not profile:
        return False
    try:
        kind, gated = frappe.db.get_value("Website Profile", profile, ["site_kind", "b2b_only"]) or (None, 0)
    except Exception:
        return False
    return kind in ("B2B", "B2C") or bool(gated)


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


def available_includes(page_type: str, site_type: str = "vitrine", profile: str | None = None, site_name: str = "", lang: str = "fr"):
    """The components this page may carry, from the catalogue (site_ai/components.py).

    //// Neoffice — rewritten 2026-09-15. This used to read PAGE_INCLUDES, a dict of seven frozen
    tag strings: the generator could not learn that a component existed unless it was listed here,
    and could not vary a single parameter, because repair_includes rewrote its tag back. The
    catalogue answers both — it is declared by each app, it carries the parameters, and it is what
    the prompt is written from. The rules that stay here are the ones about THIS site rather than
    about the component: whose data it would show, and which sites may show a shop at all."""
    from builder.site_ai import components

    shop_data = not _other_business(profile, site_name)
    sells = site_type in ("ecommerce", "ecommerce_search") or _profile_is_b2b(profile) or _profile_sells(profile)

    def allowed(component) -> bool:
        # a site built for ANOTHER business must not show this instance's shop, its team or its
        # hours: only its own contact form is left to it (the About page of a B2C test site
        # carried the host's employees and milestones, 2026-09-08)
        if not shop_data and "contact_form" not in component.path:
            return False
        # a component that only makes sense on a site that sells says so itself: the products
        # carousel does, the shop's opening hours do not — they are about the premises, and they
        # belong on the contact page of a plain showcase too
        return not (component.needs_shop and not sells)

    return components.for_page(page_type, profile, allow=allowed)


def page_sections(page: dict, minimal: bool, contact_verified: bool = True, others=(), brands=(), sells: bool = False) -> list[str]:
    """The sections a page is planned with: the image-led plan on an image-led site, else the
    page type's own. Without verified contact details no section asks for them: asked for them
    anyway, the model made them up (see UNVERIFIED_CONTACT).

    `others` are the types of the site's other pages: one page answers the questions and one
    gives the prices. The two FAQs of a site answered the same question two ways (a session of
    45 minutes on one page, of 60 on the other), and its services page listed packages its
    pricing page did not have (2026-09-13)."""
    # //// Neoffice — a page that is text by nature is never image-led (2026-09-15), wherever it is
    # //// planned from: an image-led legal page came back as a photograph and a button.
    if page["type"] in TEXT_BY_NATURE:
        minimal = False
    plan = (IMAGE_LED_PLANS.get(page["type"]) or IMAGE_LED_PLANS["generic"]) if minimal else SECTION_PLANS.get(page["type"], SECTION_PLANS["generic"])
    if brands and brands_page(page):
        plan = BRAND_PLAN_IMAGE_LED if minimal else BRAND_PLAN
    # //// Neoffice — a shop's home sells (2026-09-15): a site built to sell showed no product at
    # //// all. The row comes from the shop's own include, never drawn by hand (PAGE_INCLUDES).
    if sells and page["type"] in ("accueil", "shop"):
        row = (
            "a row of real products from the shop, with the products carousel the COMPONENTS section offers "
            "(never a product drawn by hand); give it the title and the number of products this page wants"
        )
        if not any("product carousel" in s for s in plan):
            plan = plan[:2] + [row] + plan[2:]
    if not contact_verified:
        plan = [s for s in plan if not s.startswith(("the contact details", "how to find the place", "a CTA to call or write"))]
    others = set(others or ())
    if page["type"] == "services" and others & {"faq", "pricing"}:
        plan = [s for s in plan if "FAQ" not in s]
    if page["type"] == "pricing" and "faq" in others:
        plan = [s for s in plan if s != "FAQ"]
    if page["type"] != "pricing" and "pricing" in others:
        plan = [s.replace("what is included / packages", "what is included (prices and packages belong to the pricing page)") for s in plan]
    return list(plan)


def page_headlines(blocks: list, categories: list[str] | None = None) -> list[str]:
    """The headlines a written page uses (its h1 and h2), for the pages written after it:
    each page reached for the home's line, and "Five cultures, one collective." opened the
    home, then Brands, then About (2026-09-13). A label of one or two words (a category,
    "Contact") is left out: the pages share those on purpose."""
    names = {c.strip().lower() for c in categories or []}
    found: list[str] = []

    def walk(block) -> None:
        if not isinstance(block, dict):
            return
        if str(block.get("element") or "").lower() in ("h1", "h2"):
            text = " ".join(re.sub(r"<[^>]+>", " ", str(block.get("innerHTML") or "")).split())
            if len(text.split()) >= 3 and text.lower() not in names and text not in found and "{{" not in text:
                found.append(text[:120])
        for child in block.get("children") or []:
            walk(child)

    for block in blocks or []:
        walk(block)
    return found[:8]


def stored_page(name: str) -> tuple[list, str]:
    """The blocks and the data script a page was saved with."""
    stored = frappe.db.get_value("Builder Page", name, ["blocks", "page_data_script"], as_dict=True) or frappe._dict()
    try:
        blocks = json.loads(stored.get("blocks") or "[]")
    except ValueError:
        blocks = []
    return (blocks if isinstance(blocks, list) else [blocks]), stored.get("page_data_script") or ""


def page_facts(name: str, known: str) -> list[dict]:
    """The facts the stored page states that `known` (what its writer was given) does not
    contain: see facts.py."""
    from builder.site_ai.nora.facts import invented_facts

    blocks, script = stored_page(name)
    return invented_facts(blocks, script, known, today=frappe.utils.today())


def headline_echoes(blocks: list, earlier: list[str]) -> list[dict]:
    """The headlines of a page that say what a page written before it already says, as revision
    issues. Given the lines already taken, a services page still opened on "Des soins adaptés à
    chaque étape de votre récupération" under the home's "Des soins pensés pour chaque étape de
    votre récupération" (2026-09-13)."""
    from builder.site_ai.nora.cards import says_the_same

    issues = []
    for line in page_headlines(blocks):
        twin = next((other for other in earlier if says_the_same(line, other)), None)
        if twin:
            issues.append({
                "severity": "medium",
                "area": "headline",
                "problem": f"'{line}' says what another page already says ('{twin}')",
                "fix": "write a headline of this page's own",
            })
    return issues


def page_brief_text(site: dict, brief, page: dict, handles: dict, contact_prompt: str, layout_system: str, language: str, photos: list[str], cta: tuple[str, str], palette: dict | None = None, revision: str | None = None, photo_notes: list[str] | None = None) -> str:
    from builder.site_ai.nora.facts import FACTS_RULE, today_line

    is_home = page["route"] == "home"
    used_headlines = [h for route, lines in (site.get("headlines_by_route") or {}).items() if route != page["route"] for h in lines]
    # //// Neoffice — an image-led site takes the image-led plans (IMAGE_LED_PLANS); a page
    # //// that is text by nature keeps its own
    minimal = site.get("copy_density") == "minimal" and page["type"] not in TEXT_BY_NATURE
    others = list(site.get("page_types") or [])
    if page["type"] in others:
        others.remove(page["type"])
    plan = page_sections(page, minimal, contact_verified=site.get("contact_verified", True), others=others, brands=site.get("brands") or (), sells=bool(site.get("sells")))
    # //// Neoffice — the site plan's sections for this page, when a plan was written (site_plan.py,
    # //// 2026-09-16): the static list above is the fallback, not the design.
    from builder.site_ai.nora import site_plan as planner

    planned = planner.page_of(site.get("plan"), page["route"])
    if planned:
        plan = planner.section_lines(planned)
    contract = planner.contract_lines(site.get("plan"), is_home)
    sections = "\n".join(f"{i}. {s}" for i, s in enumerate(plan, 1))
    concept = getattr(brief, "design_concept", "") or ""
    signature = getattr(brief, "signature_element", "") or ""
    tone = getattr(brief, "site_tone", "") or ""
    hero = getattr(brief, "hero_style", "") or ""
    # the client's own photographs come with what each shows and what it is for (photos_for_page)
    notes = photo_notes or []
    photo_lines = "\n".join(f"{i}. {u}" + (f"  ({notes[i - 1]})" if i - 1 < len(notes) else "") for i, u in enumerate(photos, 1))
    includes = available_includes(page["type"], site.get("site_type") or "vitrine", site.get("profile"), site.get("site_name") or "", lang=site.get("lang") or "fr")
    page_role = (
        "the HOME page: open with the hero" if is_home
        else "an INTERIOR page: the site renders a title band with the page title above the content, so start directly with the first content section, no hero banner and no repeated page title"
    )
    lines = [
        f"DESIGN DIRECTION: {concept or 'a distinctive direction that fits the brand'} (tone: {tone or 'professional'}; hero style: {hero or 'free'}).",
        f"LAYOUT SYSTEM: {layout_system}. SIGNATURE MOVE: {signature or 'choose one that fits the system'}. Keep the SAME system and move on every page of this site.",
        # //// Neoffice — the ground the client chose, said to the writer on every page and every
        # //// revision (2026-09-17): it was in the brief and the plan, and a revision drifted dark.
        (
            "GROUND: LIGHT, everywhere on this page. Every section's background is white or an off-white and the ink is dark; "
            "no section, band or call-to-action carries a dark or saturated fill. A photograph may be dark, with a scrim for "
            "legibility; the section behind it stays light. The accent belongs to rules, buttons and small marks."
            if site.get("background_mode") == "light"
            else "GROUND: DARK, everywhere on this page: deep backgrounds, light ink, one lighter surface for cards or forms."
            if site.get("background_mode") == "dark"
            else ""
        ),
        # //// Neoffice — the plan's site-wide contract, when there is a plan (site_plan.contract_lines)
        *contract,
        (f"PAGE NOTES from the plan: {planned.notes}" if planned and planned.notes else ""),
        # //// Neoffice — the grid the header, the band and the footer share (site_grid_line)
        site_grid_line(handles),
        ("INSPIRATION (what the client likes; echo the palette and the mood, never copy): " + " | ".join(site["inspiration"])) if site.get("inspiration") else "",
        today_line(frappe.utils.today()),
        f"BRAND: {site['site_name']}. Activity: {site['activity']}",
        f"POSITIONING: {site.get('differentiators') or 'derive it from the activity'}",
        contact_prompt.strip() if contact_prompt else "",
        FACTS_RULE,
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
        (
            # the chrome's band already carries them: a brands page showed "Accueil / Brands"
            # above its own "Home / Brands" (2026-09-12)
            "HEADER: the site's page header already shows the breadcrumb and the page title above this page: "
            "write no breadcrumb of your own."
            if page["type"] != "accueil"
            else ""
        ),
        (
            # //// Neoffice — a legal page is written, not designed (2026-09-15). The model wrote
            # //// marketing copy when given no rule, and a made-up company number on a legal page
            # //// is worse than no page at all.
            "LEGAL PAGE: write the real document, in full, in plain prose — headings and numbered "
            "clauses, ONE column of reading across the page's full width (never a two-column band, "
            "never a narrow column beside an empty half), no photograph, no icon, no ornament, no "
            "button, no coloured band, and no marker of any kind before a heading. Use ONLY the details "
            "BUSINESS DATA gives. Everything the law requires that nobody gave you — company "
            "registration and VAT number, share capital, the payment providers, the host, the court "
            "and the country whose law applies, the delivery and return windows — is written as a "
            "visible blank in square brackets for the merchant to fill in, in their language "
            f"(for example '[{'à compléter' if language == 'French' else 'to be completed'}: …]'). "
            "Never invent one, and never leave a sentence hanging on a detail you do not have — "
            "'the shop at is operated by' is worse than either choice: write the blank, or leave the "
            "phrase out. Close with the date of the last update."
            if page["type"] == "legal" else ""
        ),
        f"SECTIONS, in order, with real copy written in {language}:\n{sections}",
        (
            # the client's categories by name: without them the category wall came out with no
            # name and two repeated photographs (2026-09-12)
            f"CATEGORIES, in the client's words: {', '.join(site['categories'])}. Name each one exactly so, in this order, "
            "and give each its own photograph tile (the PHOTOS notes say which)."
            if site.get("categories") and (page["type"] == "accueil" or page["route"] == site.get("listing_route"))
            else (
                # the other pages invented sets of their own: "Gather, Studio, Trail, Water, Camp" on
                # About and "Roam, Move, Rest, Gather, Create" on Contact, beside five categories
                # that were Snow, Street, Water, Outdoor and Home (2026-09-13)
                f"CATEGORIES of the site, in the client's words: {', '.join(site['categories'])}. When this page names or "
                "lists categories, it names exactly these, in this order; never a set of its own."
                # //// Neoffice — and shown as tiles, each on its own photograph (category_photo_map)
                + (
                    " Shown as tiles, each takes its own photograph, full bleed, its name as its only text: "
                    + "; ".join(f"{name} {url}" for name, url in site["category_photos"].items())
                    + "."
                    if site.get("category_photos") else ""
                )
                if site.get("categories") else ""
            )
        ),
        (
            f"BRANDS the business carries, in the client's words: {', '.join(site['brands'])}. A page that names brands "
            "names exactly these; never a brand of its own."
            if site.get("brands") else ""
        ),
        (
            # //// Neoffice — what the reviewer saw on the pages already written (2026-09-15): the
            # //// same defect was written on every page of a site before anyone looked at one.
            "SEEN BY THE REVIEWER ON THE PAGES ALREADY BUILT, do not repeat them here:\n"
            + "\n".join(f"- {line}" for line in site["seen_before"][-8:])
            if site.get("seen_before") else ""
        ),
        (
            # //// Neoffice — the copy rule of an image-led site (see IMAGE_LED_PLANS)
            "COPY: minimal, the photographs carry the page. Headlines of two to five words, at most one line of twelve "
            "words under a heading, NO paragraph, no list of features, no testimonials, no grid of icons, no band of "
            "figures. When in doubt, cut the text and enlarge the photograph."
            "\nCOMPOSITION: few words is not few shapes. No two sections in a row have the same shape — a full-bleed "
            "photograph, then a two-column band (words on one side, one photograph on the other), then tiles of unequal "
            "weight, then a quiet strip. A name or a caption over a photograph sits ON it, over a veil, never in a bar "
            "under it. Vary the height: a tall section, then a short one. The page must read as one composition, not as "
            "a pile of pictures."
            if minimal else ""
        ),
        (
            # the contact page closed on a "Contact us" button to itself, under its own form
            # (2026-09-13): the page the call to action leads to carries none
            "CTA: this page is where the site's call to action leads: no button to it and no final band inviting to "
            "get in touch; the page closes on its own content."
            if cta[1].rstrip("/") == f"/{page['route']}".rstrip("/")
            else f"CTA: the primary button says '{cta[0]}' and links to '{cta[1]}'; use it once in the hero (home) or the last section, and in the final band."
        ),
        (
            # the pages are written one at a time and each reached for the home's line
            # (page_headlines)
            "HEADLINES ALREADY USED on the site's other pages (write this page's own, never one of these nor a close "
            "variant): " + " | ".join(f"'{h}'" for h in used_headlines[:12])
            if used_headlines else ""
        ),
        (
            "PHOTOS: the client's OWN photographs. Copy each URL exactly, without the note in brackets after it; give each "
            f"a descriptive alt in {language}; use each at most once and follow its note: the hero opens the page, each "
            f"category tile takes the photograph named for it, full bleed, the category's name as its only text; the tiles "
            f"of one grid are alike: each gets a photograph, or none does:\n{photo_lines}"
            if notes
            else "PHOTOS AVAILABLE (placeholders that the site replaces with real photos after the build; use each at most once, "
            f"copy the URL exactly, give it a descriptive alt in {language}; the cards of one grid are alike: each gets a photo, "
            f"or none does):\n{photo_lines}"
        ),
        (
            # //// Neoffice — the brand's own mark as an ornament (2026-09-15): a site whose emblem
            # //// is a shape (a monogram, a circle of parts, a numeral) has a graphic device of its
            # //// own, and inventing another one for the page is how a photo collage ended up
            # //// looking like a lifebuoy. Once per page at most, quiet, and never in the chrome's
            # //// place — the header already carries the logo.
            f"THE BRAND'S MARK: the IMAGE at {site['mark']} — the site's own emblem. You MAY place it ONCE on this "
            "page as a BACKGROUND ornament: a layer behind one section's copy, at least 280px across and at most 0.12 "
            "opacity, or oversized and cropped by that section's edge. It is the image file and nothing else: never a "
            "letter, a digit or a shape copied out of it. It is never an inline picture beside a heading, never a "
            "bullet or an icon, never a logo in the page (the header already shows it), never on the hero, and never "
            "in more than one section. Leave it out when nothing on this page calls for it."
            if site.get("mark") and page["type"] not in TEXT_BY_NATURE else ""
        ),
        (
            f"ACCENT: {handles['accent']} is the site's signature accent (kickers, badges, one highlight per section, "
            "sparingly); use it instead of inventing another bright colour, and no other raw hex."
            if handles.get("accent") else ""
        ),
        (
            # the model wrote "d un", "l écoute": a space where the apostrophe goes (2026-09-13)
            "FRENCH: every elision takes the apostrophe ’ (d’un, l’équipe, qu’il, aujourd’hui), never a space in its place."
            if language.lower().startswith("fr")
            else ""
        ),
        "CLASS CONTRACT: " + CLASS_CONTRACT,
        components_prompt(includes),
        (
            # //// Neoffice — two rules the look kept finding broken (2026-09-17): a brand marquee that
            # //// reads as empty at rest, and a heading promising "three reasons" over a repeater whose
            # //// data never came. What a page shows must be there when it renders.
            "RULES: everything reads at rest: no marquee, no auto-scrolling strip, nothing that only appears on hover, on "
            "scroll or after a script; a brand row is a static row of names or logos. No section is a heading over "
            "nothing: a repeat block carries its `items` inline unless the brief names a live data key, and the content "
            "a heading announces is written in full under it. "
            "no header, navigation or footer sections (the site chrome is rendered around the page); no lorem; "
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


def by_route_page(pages: list[dict], created: dict) -> dict:
    """The planned page a created entry was written from (its title, route and type)."""
    planned = created.get("planned") or str(created.get("route") or "").strip("/")
    return next((p for p in pages if p["route"] == planned), {"title": created.get("title"), "route": planned, "type": created.get("type") or "generic"})


def keeps_own_logo(logo_type, logo_image, host_logo) -> bool:
    """//// Neoffice — whether a profile's chrome carries a logo of its OWN: an image that is not
    the host site's (a new Variant is bootstrapped from the host's Single, logo included, and that
    inherited logo is the one a build must NOT keep). 2026-09-16."""
    return bool(logo_image) and str(logo_type or "") == "Image" and str(logo_image) != str(host_logo or "")


def _host_logo() -> str | None:
    """The host site's own logo (the Single's), the one a profile's Variant inherits."""
    try:
        return frappe.db.get_single_value("Website Header Footer Config", "logo_image")
    except Exception:
        return None


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
# //// Neoffice — 900 since K3 writes the pages (2026-09-16): at reasoning_effort "high" its first
# //// line came after 187 s on a four-section page and the page took 244 s; a home is longer.
PAGE_STREAM_MAX_SECONDS = 900
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
# //// Neoffice — 660 for the same reason (K3 "high": 187 s measured, a home thinks longer); the
# //// limit exists to catch a stall, not to hurry a model that was asked to think.
PAGE_STREAM_THINKING_SECONDS = 660
# //// Neoffice — how much of the previous version a revision carries back to the writer
PREVIOUS_YAML_MAX_CHARS = 60_000


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
            # //// Neoffice — and into the build's own tally (builder/ai/meter.py, 2026-09-15): the
            # //// agent's ctx counts a chat turn, and a scripted build has no ctx worth the name.
            try:
                from builder.ai import meter

                meter.add(model, getattr(chunk, "usage", None))
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
    # //// Neoffice — db.set_value skips on_update, so the route cache is cleared here (2026-09-17):
    # //// a suffixed route, or a page that replaced a deleted one, must be found at once
    try:
        from builder.builder.doctype.builder_page.builder_page import find_page_with_path

        find_page_with_path.clear_cache()
    except Exception:
        pass
    frappe.db.commit()
    return name, route


def _describe(blocks: list) -> str:
    from builder.api import _describe_page

    try:
        return _describe_page(blocks) or ""
    except Exception:
        return ""


def remember_site_language(profile: str | None, lang: str | None) -> bool:
    """The site speaks the language it was written in: the theme renders the chrome of a
    profile's pages (breadcrumb, footer, forms) in the profile's language, where an English
    site built on a French instance showed "Accueil" and a French contact form (2026-09-12)."""
    if not (profile and lang) or not frappe.db.has_column("Website Profile", "language") or not frappe.db.exists("Language", lang):
        return False
    frappe.db.set_value("Website Profile", profile, "language", lang)
    return True


# //// Neoffice — the legal pages of a shop (2026-09-15): their routes, whatever language they were
# //// written in. A storefront links every one it has in its footer, and the build says which are
# //// missing.
LEGAL_ROUTES = {
    "terms": ("terms", "terms-conditions", "terms-and-conditions", "cgv", "cgu", "conditions-generales", "conditions-generales-de-vente", "agb"),
    "privacy": ("privacy", "privacy-policy", "politique-de-confidentialite", "confidentialite", "datenschutz"),
    "legal": ("legal", "legal-notice", "mentions-legales", "impressum"),
}


def legal_pages(profile: str | None) -> list[tuple[str, str]]:
    """The site's legal pages, as (route, title), in the order a footer names them."""
    try:
        filters = {"published": 1}
        if profile:
            filters["neo_website_profile"] = profile
        rows = frappe.get_all("Builder Page", filters=filters, fields=["route", "page_title"])
    except Exception:
        return []
    found: list[tuple[str, str]] = []
    for kind in ("terms", "privacy", "legal"):
        for row in rows:
            route = str(row.get("route") or "").strip("/").lower()
            if route in LEGAL_ROUTES[kind] and not any(route == known.strip("/") for known, _ in found):
                found.append((f"/{route}", row.get("page_title") or route))
                break
    return found


def _is_legal_route(route: str) -> bool:
    """Whether a route is one of the site's legal pages (terms, privacy, legal notice)."""
    bare = str(route or "").strip("/").lower()
    return any(bare in known for known in LEGAL_ROUTES.values())


class BriefAlreadyWritten(Exception):
    """//// Neoffice — the site's design brief was reused, so this build does not write one."""


LEGAL_PLANNED = {
    "terms": ("terms-conditions", "Terms & Conditions"),
    "privacy": ("privacy-policy", "Privacy Policy"),
}


def plan_legal_pages(pages: list[dict], profile: str | None, site_type: str, lang: str = "fr") -> list[dict]:
    """The legal pages a shop must have and does not: neither already planned nor already on
    the site. A showcase site is left alone — it is the shop that cannot trade without them."""
    if site_type not in ("ecommerce", "ecommerce_search") and not (profile and _profile_sells(profile)):
        return []
    planned = {str(p.get("route") or "").strip("/").lower() for p in pages}
    already = {route.strip("/") for route, _ in legal_pages(profile)}
    out: list[dict] = []
    for kind in ("terms", "privacy"):
        known = LEGAL_ROUTES[kind]
        if any(route in known for route in planned | already):
            continue
        route, title = LEGAL_PLANNED[kind]
        out.append({"title": _(title, lang=lang), "route": route, "type": "legal"})
    return out


def missing_legal_pages(profile: str | None) -> list[str]:
    """Which of the legal pages a shop needs it does not have."""
    have = {route.strip("/") for route, _ in legal_pages(profile)}
    return [kind for kind in ("terms", "privacy") if not any(route in LEGAL_ROUTES[kind] for route in have)]


# //// Neoffice ▼▼▼ — the site's root points at the new home as soon as it exists (2026-09-15).
# //// A rebuild deletes the old pages first, and the profile was only told its home page at the very
# //// end: for the twenty-five minutes in between, the root of a live site served the instance's own
# //// welcome screen — "Bienvenue sur Neoffice", with a sign-in button, to the client's visitors.
def point_home_at(profile: str | None, page_name: str) -> None:
    """Tells the site which page is its home, now rather than at the end of the build."""
    if not page_name:
        return
    try:
        if profile and frappe.db.exists("DocType", "Website Profile"):
            frappe.db.set_value("Website Profile", profile, "home_page", page_name)
            frappe.cache.delete_value("nt_website_profiles_by_host")
            frappe.cache.delete_value("website_page")
            # //// Neoffice — and the route lookup (2026-09-17): cached for an hour, it answered
            # //// "home" for this profile with a page deleted at the start of the build
            from builder.builder.doctype.builder_page.builder_page import find_page_with_path

            find_page_with_path.clear_cache()
        else:
            frappe.db.set_value("Website Settings", "Website Settings", "home_page", "home")
            frappe.db.set_value("Builder Settings", "Builder Settings", "home_page", "home")
        frappe.db.commit()
    except Exception:
        # the end of the build sets it again: a failure here is not worth losing the build over
        pass
# //// Neoffice ▲▲▲


# //// Neoffice ▼▼▼ — the menu is made of the site's pages, not of this run's (2026-09-15).
# //// apply_navigation rebuilt the menu from `created` alone, so a build of ONE page left a site
# //// with a one-entry menu. That is why every fix, however small, meant regenerating the whole
# //// site: four full rebuilds in a day, each one paying again for five pages nobody had asked to
# //// change. A run now writes the menu from what the site HAS — the pages it just built, plus the
# //// published ones it left alone, in the order they were created.
def site_pages_for_menu(created: list[dict], profile: str | None, order: list[str] | None = None) -> list[dict]:
    """The site's pages as the menu should name them: the ones just built, plus the published
    ones this run did not touch, IN THE ORDER THE MENU ALREADY HAD.

    //// Neoffice — `order` added 2026-09-16. Without it the pages this run wrote came first, so
    rebuilding the Contact page on its own moved Contact to the third entry of a menu that read
    Home, Shop, Brands, About, Contact — a rule the user had stated twice. A run that writes one
    page has no business reordering a menu: the order the site already has wins, and only a page
    the menu does not know yet is appended. On any failure, just what was built — a menu of this
    run's pages beats no menu."""
    built = {p["name"] for p in created}
    out = list(created)
    try:
        filters = {"published": 1, "is_template": 0}
        if profile and frappe.db.has_column("Builder Page", "neo_website_profile"):
            filters["neo_website_profile"] = profile
        rows = frappe.get_all("Builder Page", filters=filters, fields=["name", "page_title", "route"], order_by="creation")
    except Exception:
        return out
    seen_routes = {str(p.get("route") or "").strip("/") for p in created}
    for row in rows:
        route = str(row.get("route") or "").strip("/")
        if row["name"] in built or route in seen_routes:
            continue
        seen_routes.add(route)
        out.append({"name": row["name"], "title": row.get("page_title") or route, "route": f"/{route}", "planned": route})
    if not order:
        return out
    # the order the menu already had; a route it does not know goes to the end, in the order
    # the pages were created.
    # //// Neoffice — the home answers to three spellings: the menu names it "/" (an empty key
    # //// once stripped), the page's route is "home" or "index". Keyed on the raw string alone,
    # //// the home matched nothing and went to the END of its own menu.
    def key(route: str) -> str:
        bare = str(route or "").strip("/").lower()
        return "" if bare in ("", "home", "index") else bare

    known = {key(route): rank for rank, route in enumerate(order)}
    return sorted(out, key=lambda p: known.get(key(p["route"]), len(known) + out.index(p)))
# //// Neoffice ▲▲▲


def footer_blurb(text: str) -> str:
    """The site's activity as a visitor reads it in the footer: its first paragraph, in plain words.

    The activity a build receives is written for a model, and may carry a brief's scaffolding:
    one arrived ending with the brief's own "## REAL BUSINESS DATA (use EXACTLY these values)"
    section and its list of contact details, and the footer printed "## REAL BUSINESS DATA (u",
    cut at 200 characters, on every page of the site (2026-09-18). What follows a blank line or
    a heading is for the model, never for the footer; a heading or list marker is dropped."""
    import re

    text = (text or "").strip()
    first = re.split(r"\n\s*\n|\n\s*#{1,6}\s", text, maxsplit=1)[0]
    lines = [line.strip() for line in first.splitlines() if not re.match(r"\s*(#{1,6}\s|[-*•]\s)", line)]
    return " ".join(line for line in lines if line)


def apply_navigation(config, created: list[dict], site_type: str, description: str, profile: str | None, lang: str = "fr", site_name: str = "") -> None:
    """Menu, footer and home page from the pages the SITE has (site_pages_for_menu), which is
    the pages this run built plus the published ones it left alone. Labels are translated into
    the site's language, not the operator's session."""
    # //// Neoffice — the order the menu already has, read BEFORE it is cleared (2026-09-16)
    previous_order = [str(getattr(row, "url", "") or "").strip("/") for row in (config.menu_items or [])]
    created = site_pages_for_menu(created, profile, previous_order)
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
        elif _profile_sells(profile) and _webshop_installed():
            # //// Neoffice — a B2C storefront of the same business sells too (see _profile_sells)
            config.append("menu_items", {"label": _("Shop", lang=lang), "url": "/all-products", "is_external": False, "open_in_new_tab": False})
    # //// Neoffice — a shop's menu opens on the home (2026-09-15): the Shop entry came first, and a
    # //// shop before the home is not a menu anyone writes. A showcase keeps its logo as the way
    # //// home; a storefront names both, Home then Shop.
    if config.menu_items and str(getattr(config.menu_items[0], "url", "") or "") == "/all-products":
        shop = config.menu_items[0]
        config.menu_items = []
        config.append("menu_items", {"label": _("Home", lang=lang), "url": "/", "is_external": False, "open_in_new_tab": False})
        config.append("menu_items", {"label": shop.label, "url": "/all-products", "is_external": False, "open_in_new_tab": False})
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
        # //// Neoffice — the legal pages belong to the footer, not the menu (2026-09-15): nobody
        # //// puts their terms between Brands and Contact, and the footer's Legal column already
        # //// names them (legal_pages).
        if _is_legal_route(route):
            continue
        seen.add(route)
        # //// Neoffice — see the block marker above: no more Home relabelling
        config.append("menu_items", {"label": page["title"], "url": route, "is_external": False, "open_in_new_tab": False})
    # //// Neoffice — a mark chosen for the footer stays (2026-09-15): the build copied the header's
    # //// over it at every rebuild, and a site whose footer carries another mark lost it each time.
    own_mark = bool(config.get("footer_logo_image")) and config.get("footer_logo_image") != config.get("logo_image")
    for field, value in (("footer_logo_type", config.get("logo_type")), ("footer_logo_text", config.get("logo_text")), ("footer_logo_image", config.get("logo_image")), ("show_footer_logo", True), ("footer_menu_source", "Custom links")):
        if own_mark and field in ("footer_logo_type", "footer_logo_image"):
            continue
        if hasattr(config, field):
            config.set(field, value)
    if hasattr(config, "footer_description"):
        from builder.api import _shorten_for_footer

        config.footer_description = _shorten_for_footer(footer_blurb(description))
    if hasattr(config, "footer_links"):
        config.footer_links = []
        for page in created:
            home = page["route"] in ("/", "/home", "/index")
            # //// Neoffice — the legal pages are not navigation (2026-09-15): the chrome puts them
            # //// on their own row at the very bottom, quieter and lower than the site's pages
            # //// (hf_utils/header_footer.py::_legal_links). Listed here they would sit between
            # //// Brands and Contact, and on a Centered footer in the same single row as them.
            if _is_legal_route(page["route"]):
                continue
            config.append("footer_links", {"column_name": _("Navigation", lang=lang), "label": _("Home", lang=lang) if home else page["title"], "url": "/" if home else page["route"]})
    config.save(ignore_permissions=True)
    # //// Neoffice — the home is known by what it was planned as, not only by the route it got
    # //// (2026-09-15): a home written beside one that was kept takes a hashed route ("home-b059"),
    # //// which matched none of these, so the profile was never told its home page and the site
    # //// served the instance's default page at its root.
    home_name = next(
        (p["name"] for p in created if p["route"] in ("/", "/home", "/index") or str(p.get("planned") or "") in ("", "home", "index")),
        None,
    )
    if profile and frappe.db.exists("DocType", "Website Profile"):
        if home_name:
            frappe.db.set_value("Website Profile", profile, "home_page", home_name)
        remember_site_language(profile, lang)
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
    from builder.site_ai.nora.facts import facts_issues, invented_facts, known_text
    from builder.site_ai.nora.placeholders import neutral_named_slots, neutral_placeholders
    from builder.site_ai.nora.punctuation import french_elisions, french_spacing, script_elisions
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
    footer_logo_image = clean_logo(spec.get("footer_logo_image"))
    # //// Neoffice — a run that writes only the pages it names, leaving the rest of the site — and
    # //// the rest of its chrome — alone (2026-09-15). Read here: the chrome step needs it too.
    building_part = str(spec.get("scope") or "site") == "pages"
    # //// Neoffice — a site that sells says so to every page (2026-09-15): its home shows real
    # //// products taken from the shop, and its footer is the centred one. Read here, before the
    # //// chrome step, which runs long before the pages.
    _sells_here = bool(
        site_type in ("ecommerce", "ecommerce_search")
        or (profile and _profile_sells(profile) and _webshop_installed() and not _other_business(profile, site_name))
    )
    job_id = f"site_gen_{frappe.generate_hash(length=10)}"
    # //// Neoffice — what this build spends, counted from here (builder/ai/meter.py, 2026-09-15)
    from builder.ai import meter

    meter.start()

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
    # //// Neoffice — a partial build is only asked about the pages it would actually replace
    if building_part:
        wanted = {str(p["route"]).strip("/") for p in pages}
        protected = [p for p in protected if str(p.get("route") or "").strip("/") in wanted]
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
    to_delete = pages_to_replace(
        classes,
        replace_existing,
        routes={str(p["route"]).strip("/") for p in pages} if building_part else None,
    )
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
    # //// Neoffice — a shop is built with its legal pages (2026-09-15): the first storefront the
    # //// pipeline produced had neither terms nor a privacy policy, and a shop without them cannot
    # //// trade. Planned AFTER the pages being replaced are gone — a terms page the build is about
    # //// to delete is not a terms page the site has — then written by the page loop like any
    # //// other, and linked in the footer by the chrome (hf_utils/header_footer.py::_legal_links).
    pages += plan_legal_pages(pages, profile, site_type, lang_code)
    total = len(pages)
    _update_generation_status(job_id, {"status": "running", "progress": 0, "total_pages": total, "current_step": "Starting", "pages_created": [], "error": None, "site_name": site_name, "started_at": now()})
    ai_log("info", "=== NORA SITE BUILD STARTED ===", job_id=job_id, site_name=site_name, profile=profile, lang=lang_code, replace=replace_existing, pages=[p["title"] for p in pages])

    # 2. the chrome basics
    config = _get_site_chrome_config(profile)
    # //// Neoffice — the site-type defaults are for a site being BUILT (2026-09-15): re-applied by
    # //// a run that only writes a page, they undo every chrome choice made since — the footer
    # //// template, the search, the account entry — none of which that run was asked about.
    if not building_part:
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
    # //// Neoffice — and a storefront of the instance's own business carries the cart and the
    # //// account, whatever the site type the model chose (see _profile_sells). On a B2B site the
    # //// cart still waits for the sign-in: that is the cart's audience, not its absence.
    if profile and _profile_sells(profile) and _webshop_installed() and not _other_business(profile, site_name):
        for field in ("show_user", "show_cart"):
            if hasattr(config, field):
                setattr(config, field, True)
    if logo_image:
        config.logo_type = "Image"
        config.logo_image = logo_image
    elif building_part:
        # //// Neoffice — a run that writes part of a site never clears the chrome it was not
        # //// given (2026-09-15). Asked from the chat to redo one page, the assistant calls the
        # //// tool with the page and nothing else: no logo in the arguments meant "this site has
        # //// no logo", and the branch below wiped the client's wordmark out of the header.
        pass
    elif profile and not keeps_own_logo(config.get("logo_type"), config.get("logo_image"), _host_logo()):
        # a profile's Variant is bootstrapped from the main site's Single, logo
        # included: without an upload the new site shows its own name, not the
        # host's logo (on the Single, logo-default.png IS the client's logo)
        # //// Neoffice — but a logo the site ALREADY HAS of its own is kept (2026-09-16): a full
        # //// rebuild asked without a logo in its arguments wiped the client's uploaded wordmark
        # //// out of the header while the footer kept its own. keeps_own_logo tells the host's
        # //// inherited logo (wiped, as before) from the client's (kept).
        config.logo_type = "Text"
        config.logo_image = None
    else:
        config.logo_type = "Image" if config.get("logo_image") else "Text"
    config.logo_text = site_name
    if hasattr(config, "footer_logo_text"):
        config.footer_logo_text = site_name
    # //// Neoffice — the footer's own mark (2026-09-15): a brand hands out two files, the wordmark
    # //// for the header and an emblem or a monochrome version for the foot. Set here, apply_navigation
    # //// leaves it alone (own_mark) instead of copying the header's over it at every rebuild.
    if footer_logo_image and hasattr(config, "footer_logo_image"):
        config.footer_logo_type = "Image"
        config.footer_logo_image = footer_logo_image
        config.show_footer_logo = True
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
    # //// Neoffice — the menu is NOT emptied here (2026-09-15): a rebuild takes twenty-five
    # //// minutes, and for all of them the live site showed a header with no menu at all.
    # //// apply_navigation replaces it in one go at the end, when the new pages exist.
    config.save(ignore_permissions=True)
    frappe.db.commit()

    # 3. the design brief (K3 with design intelligence), grounded in real business data
    # the instance's own company (ERPNext Company, its address, its logo) grounds the
    # site of THAT business; a site built for another business on a secondary profile
    # must not inherit its logo, address, phone or e-mail (the B2B test site carried the
    # host company's logo in its header and its address on every page, 2026-09-08)
    if _other_business(profile, site_name):
        contact_data = {}
        contact_prompt = UNVERIFIED_CONTACT
    else:
        contact_data = get_site_contact_context(profile)
        # the instance's own business without an address on file is no better known
        contact_prompt = _contact_context_prompt(contact_data) or UNVERIFIED_CONTACT
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
        _progress(ctx, job_id, _("Reading the inspirations"), 5)
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
    # //// Neoffice ▼▼▼ — light or dark GROUND is a question for the client, not a taste of the
    # //// model (2026-09-16). Left to the brief, a B2B distributor came out with a near-black
    # //// hero and a near-black call-to-action, and the only way to change it was for an operator
    # //// to say so afterwards — which is exactly what must not be needed. Nora now asks it in the
    # //// recap card and passes the answer here. "auto" keeps the old behaviour: the brief decides.
    background_mode = (spec.get("background_mode") or "auto").strip().lower()
    if background_mode not in ("light", "dark"):
        background_mode = "auto"
    background_prompt = ""
    if background_mode == "light":
        background_prompt = (
            " GROUND: light, everywhere. Every section's background is white or an off-white, and the ink is dark. "
            "No section — hero, call-to-action or band — may carry a dark or saturated fill. A PHOTOGRAPH may be dark, "
            "and a scrim over a photograph is allowed for legibility; the section behind it stays light. "
            "The accent colour belongs to buttons, rules and small marks, never to a whole section."
        )
    elif background_mode == "dark":
        background_prompt = (
            " GROUND: dark, everywhere. Every section's background is a deep near-black or the palette's darkest tone, "
            "and the ink is light. Keep one lighter surface for cards or forms so the page has depth."
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
    prompt = f"{site_name}: {activity}. {spec.get('differentiators') or ''} Style: {spec.get('style_direction') or ''}{contact_prompt}{inspiration_prompt}{monochrome_prompt}{background_prompt}{density_prompt}"

    # the client's own photographs, read into the session's library so the pages can be
    # laid out with them (placed at step 7, after the pages exist)
    library = {"taken": 0, "understood": 0}
    photos = clean_list(spec.get("photos"))
    if photos and getattr(ctx, "session_id", None):
        _progress(ctx, job_id, _("Reading your photos"), 6)
        try:
            from builder.site_ai.ingestion.content_understanding import ingest_and_understand

            library = ingest_and_understand(ctx.session_id, photos)
            ai_log("info", "Client library ready", **library)
        except Exception as e:
            ai_log("warning", "Client library skipped", error=str(e)[:200])
    # the pages are written with the client's own photographs (photos_for_page), and the
    # categories the brief names get their tiles and a link to the page that lists them
    # without a list, a rebuild takes every photograph the conversation already took in: asked
    # for "the same 12 photos", the model hunted them in the File list and found 10 on the pages,
    # or product shots beside them (2026-09-12)
    client_photos = library_photos(getattr(ctx, "session_id", None), only=photos or None)
    # the categories travel as their own list; the brief's own words are only the fallback
    categories = [str(c).strip() for c in (spec.get("categories") or []) if str(c).strip()][:8] or category_names(
        activity, spec.get("differentiators") or "", spec.get("style_direction") or ""
    )
    ai_log("info", "Client photos ready", photos=len(client_photos), categories=categories)
    photos_used: dict[str, int] = {}
    # //// Neoffice — each category's photograph, for every page that shows the categories as tiles
    category_photos = category_photo_map(client_photos, categories)
    # //// Neoffice ▲▲▲
    # announced when the brief is really written: said before the inspirations and the photos
    # were read, it left the panel on "Reading the inspirations" through the brief's minutes
    # of thinking, and the bar went 8, 6, 7 (2026-09-11)
    _progress(ctx, job_id, _("Writing the design brief"), 8)
    settings = get_ai_settings()
    brief = None
    # //// Neoffice ▼▼▼ — a rebuild reuses the brief it already wrote (2026-09-15). The brief is the
    # //// single most expensive call of a build: it carries the logo and three inspiration
    # //// screenshots, measured at 618 kB of pictures per call, and it is written from the same
    # //// inputs every time. Rebuilding a site to change its pages re-read the same six reference
    # //// sites and re-decided the same art direction, for nothing. Pass reuse_brief=False to make
    # //// it think again — that is what changing the direction means.
    if spec.get("reuse_brief", True):
        try:
            stored = _get_site_chrome_config(profile).get("ai_brief")
            if stored:
                from builder.site_ai.schemas.design_brief import DesignBrief

                brief = DesignBrief.model_validate_json(stored)
                ai_log("info", "Design brief reused", profile=profile, tone=getattr(brief, "site_tone", ""))
                _progress(ctx, job_id, _("Reusing this site's design brief"), 9)
        except Exception as e:
            brief = None
            ai_log("info", "Stored design brief unusable, writing a new one", error=str(e)[:160])
    # //// Neoffice ▲▲▲
    try:
        if brief is not None:
            raise BriefAlreadyWritten
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
    except BriefAlreadyWritten:
        pass
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
    # //// Neoffice — and the site grid the chrome shares with the pages (SITE_GRIDS)
    try:
        handles.update(mint_grid_tokens(prefix, profile or site_name, choose_layout_system(spec.get("style_direction"), brief)))
    except Exception as e:
        ai_log("warning", "Grid tokens failed", error=str(e)[:200])
    palette = palette_values(prefix)
    # //// Neoffice — see the block marker above: text made readable on background
    readable = ensure_readable_text(prefix, palette)
    if readable:
        ai_log("info", "Text token made readable on the background", value=readable)
    try:
        apply_brief_site_chrome(brief, website_profile=profile)
        config = _get_site_chrome_config(profile)
        # //// Neoffice — a shop closes on a centred footer (2026-09-15): the brief picked the rich
        # //// multi-column one and a storefront's footer became a directory, with the terms buried
        # //// in a column. A shop's foot is its mark, one row of links, and the legal row under it.
        if _sells_here and hasattr(config, "footer_template") and config.get("footer_template") in ("Standard", "Extended"):
            config.footer_template = "Centered"
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
    # //// Neoffice — the brands the brief names (see BRAND_PLAN)
    brands = [str(b).strip() for b in (spec.get("brands") or []) if str(b).strip()][:24]
    site = {"site_name": site_name, "activity": activity, "differentiators": spec.get("differentiators"), "site_type": site_type, "profile": profile, "inspiration": inspiration["notes"], "copy_density": copy_density, "categories": categories, "brands": brands, "page_types": [p["type"] for p in pages],
            # //// Neoffice — the brand's own mark, offered to the pages as an ornament (2026-09-15):
            # //// the footer's emblem when the client gave one, else the header's logo.
            "mark": footer_logo_image or logo_image or "",
            # //// Neoffice — the site's language reaches the includes too (2026-09-15)
            "lang": lang_code,
            # //// Neoffice — and the ground the client chose reaches every page brief (2026-09-17)
            "background_mode": background_mode}
    site["sells"] = _sells_here
    # //// Neoffice ▼▼▼ — the site plan (site_plan.py, 2026-09-16): every page's sections decided
    # //// once, by the model that thinks best, from the brief and the client's material — logo,
    # //// references, their photographs and what the vision read in them, categories, brands —
    # //// with the geometry of the signature move and what every interior page opens with. The
    # //// pages are then executed from it. Without a plan the static plans apply, as before.
    from builder.site_ai.nora import site_plan as planner

    site["plan"] = None
    if not building_part and spec.get("plan_site", True) and not ctx.is_cancelled():
        # //// Neoffice — a rebuild of the same pages reuses the plan it already has (2026-09-17),
        # //// as it reuses the brief: six minutes of the strong model's thinking, kept 48 h. A
        # //// changed page list, or reuse_brief=False, thinks again.
        plan_key = f"nora_site_plan::{profile or site_name}"
        wanted_routes = sorted(p["route"] for p in pages)
        if spec.get("reuse_brief", True):
            try:
                kept = frappe.cache.get_value(plan_key)
                stored = planner.from_json(kept) if kept else None
                if stored and sorted((p.route or "").strip("/") for p in stored.pages) == wanted_routes:
                    site["plan"] = stored
                    ai_log("info", "Site plan reused", profile=profile, pages=len(stored.pages))
            except Exception:
                site["plan"] = None
        if site["plan"] is None:
            _progress(ctx, job_id, _("Planning the site"), 9)
            try:
                includes_by_route = {
                    p["route"]: [f"{c.path} — {c.shows}" for c in available_includes(p["type"], site_type, profile, site_name, lang=lang_code)]
                    for p in pages
                }
                plan_logo = (frappe.utils.get_url() + logo_image) if logo_image and logo_image.startswith("/") else logo_image
                with meter.kind(meter.WRITING):
                    site["plan"] = planner.plan_site(
                        page_model, site, brief, pages, includes_by_route, client_photos, language,
                        logo_image=plan_logo, inspiration_images=inspiration["images"], background_mode=background_mode,
                    )
                if site["plan"] is not None:
                    frappe.cache.set_value(plan_key, planner.as_json(site["plan"]), expires_in_sec=48 * 3600)
            except Exception as e:
                ai_log("warning", "Site plan step failed, the static plans apply", error=str(e)[:200])
    # //// Neoffice ▲▲▲
    created, failed, cancelled = [], [], False
    # //// Neoffice — what the look decided (2026-09-16): the pages it refused, how many looks each
    # //// page took, what it measured on the chrome, and how many passed at first look
    held, looked, chrome_findings, first_look_accepted, accepted_later = [], {}, [], 0, 0
    judge = visual_check.judge_model(page_model)
    # //// Neoffice — what the reviewer already read, and the page's state when it did (2026-09-15)
    reviewed_already: dict[str, dict] = {}
    # //// Neoffice — the page at which the token budget was passed, if it was (meter.over_budget)
    over_budget_at = ""

    # //// Neoffice — image generation was switched off (the pictures were not good enough):
    # //// gates the neutral-SVG fallback below (65d8f360 "fix(nora): cards never stack in a column, and photo slots without photos are plain blocks")
    images_on = _image_backend_available()

    def write_page(page: dict, photos: list[str], revision: str | None = None, notes: list[str] | None = None) -> tuple[list, str, str | None]:
        """One page through the writer and the mechanical passes: (blocks, data_script, error)."""
        # //// Neoffice — a revision REWRITES the page it revises (2026-09-16). It used to be a fresh
        # //// page from the same brief plus "fix these points and keep everything else" — with
        # //// nothing to keep, since the writer never saw what it had written: the second version
        # //// had other defects (Contact: 3 points, then 4). The previous YAML now travels with the
        # //// points, and the writer reproduces it, changing only what the points require.
        previous = (site.get("last_yaml") or {}).get(page["route"])
        if revision and previous:
            revision = (
                revision
                + "\nPREVIOUS VERSION of this page, in YAML. Reproduce it and change ONLY what the points above "
                "require: the structure, the copy and the photographs stay as they are.\n"
                + previous[:PREVIOUS_YAML_MAX_CHARS]
            )
        brief_text = page_brief_text(site, brief, page, handles, contact_prompt, layout_system, language, photos, cta, palette=palette, revision=revision, photo_notes=notes)
        messages = [
            {"role": "system", "content": Prompts.GENERATION_YAML},
            {"role": "user", "content": f"Build this page now:\n{brief_text}"},
        ]
        blocks, data_script, error = [], "", None
        for attempt in range(2):
            try:
                with meter.kind(meter.WRITING):
                    raw = _stream_text(ctx, page_model, messages, llm.TASK_PARAMS["complex"])
                blocks, data_script = expand_page_yaml(BlockCodec.strip_fences(raw))
                if blocks:
                    # //// Neoffice — kept for the revision (see the top of write_page)
                    site.setdefault("last_yaml", {})[page["route"]] = BlockCodec.strip_fences(raw)
                    # //// Neoffice — new call: repairs includes to the offered tag or drops them (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
                    # an include is one the brief offered, written as offered (a wrong
                    # path is a 417 at render time): see repair_includes
                    fixed, dropped = repair_includes(blocks, available_includes(page["type"], site["site_type"], site["profile"], site["site_name"], lang=site.get("lang") or "fr"))
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
                    # //// Neoffice — nor a grid that ends on a hole it can avoid (layout.balance_grids)
                    from builder.site_ai.nora.layout import balance_grids

                    balanced = balance_grids(blocks, repeater_counts(data_script))
                    if balanced:
                        ai_log("info", "Grids balanced", page=page["title"], edits=balanced)
                    # //// Neoffice — and a grid of equal items gets columns of its own on the phone (layout.phone_columns)
                    from builder.site_ai.nora.layout import phone_columns

                    phoned = phone_columns(blocks, repeater_counts(data_script))
                    if phoned:
                        ai_log("info", "Grids given phone columns", page=page["title"], edits=phoned)
                    # //// Neoffice — and the last item alone on its phone row takes the row (layout.fill_last_phone_row)
                    from builder.site_ai.nora.layout import fill_last_phone_row

                    filled = fill_last_phone_row(blocks)
                    if filled:
                        ai_log("info", "Last phone rows filled", page=page["title"], edits=filled)
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
                    listing = next((r for p, r in zip(pages, routes) if p["route"] == lister_route), None)
                    foreign = repair_foreign_links(blocks, routes, cta[1], categories=categories, listing=listing)
                    if foreign:
                        ai_log("info", "Foreign links brought home", page=page["title"], edits=foreign)
                    # a call to action never leads to the page it is on (buttons.py)
                    from builder.site_ai.nora.buttons import retarget_self_links

                    own = retarget_self_links(blocks, page["route"], cta[1])
                    if own:
                        ai_log("info", "Links to the page itself retargeted", page=page["title"], edits=own)
                    # nor does that page close on a band sending the visitor back to it (buttons.py)
                    if cta[1].rstrip("/") == f"/{page['route']}".rstrip("/"):
                        from builder.site_ai.nora.buttons import drop_closing_band

                        closing = drop_closing_band(blocks, page["route"])
                        if closing:
                            ai_log("info", "Closing band to the page itself dropped", page=page["title"], band=closing)
                    # the routes the data script hands to repeated blocks pass the same check
                    from builder.site_ai.nora.buttons import repair_data_routes

                    data_script, data_moved = repair_data_routes(data_script, routes, cta[1], categories=categories, listing=listing, blocks=blocks)
                    if data_moved:
                        ai_log("info", "Data script links brought home", page=page["title"], edits=data_moved)
                    # a category tile leads to its own panel on the page that lists them, not to
                    # the top of that page (anchors.py)
                    if listing and categories:
                        from builder.site_ai.nora.anchors import (
                            anchor_category_data_links,
                            anchor_category_links,
                            anchor_category_panels,
                            anchor_repeated_panels,
                        )
                        from builder.site_ai.nora.buttons import _href_keys

                        anchored = anchor_category_panels(blocks, categories) if page["route"] == lister_route else []
                        if page["route"] == lister_route:
                            # panels repeated over the data script carry their name bound
                            data_script, repeated = anchor_repeated_panels(blocks, data_script, categories)
                            anchored += repeated
                        pointed = anchor_category_links(blocks, listing, categories)
                        data_script, bound = anchor_category_data_links(data_script, listing, categories, _href_keys(blocks))
                        if anchored or pointed or bound:
                            ai_log("info", "Category anchors", page=page["title"], panels=anchored, links=pointed + bound)
                    # //// Neoffice — a bracketed placeholder never reaches a visitor (facts.drop_placeholders),
                    # //// and a layer over a photograph is a veil, never a wall (contrast.repair_opaque_overlays)
                    from builder.site_ai.nora.contrast import repair_opaque_overlays
                    from builder.site_ai.nora.facts import drop_placeholders

                    scrubbed = drop_placeholders(blocks)
                    if scrubbed:
                        ai_log("info", "Placeholders dropped", page=page["title"], edits=scrubbed[:6])
                    # //// Neoffice — nor a picture whose file does not exist: shown a folder of
                    # //// marque-<brand>.jpg the writer invented the one brand it was missing
                    # //// (facts.drop_missing_pictures)
                    from builder.site_ai.nora.facts import drop_missing_pictures

                    absent = drop_missing_pictures(blocks)
                    if absent:
                        ai_log("info", "Pictures with no file dropped", page=page["title"], edits=absent[:6])
                    # //// Neoffice — and a partner's name is spelled the way the business gave it:
                    # //// given the exact list of the brands a business distributes, a writer
                    # //// published one of them a letter off (facts.spell_names_as_given)
                    from builder.site_ai.nora.facts import spell_names_as_given

                    respelled = spell_names_as_given(blocks, [*(site.get("brands") or []), *(site.get("categories") or [])])
                    if respelled:
                        ai_log("info", "Names spelled as the business gave them", page=page["title"], edits=respelled[:6])
                    # //// Neoffice — nor a contact detail the business data does not give: told to leave one
                    # //// out, the model wrote a plausible e-mail and website instead (facts.drop_invented_contacts)
                    from builder.site_ai.nora.facts import drop_invented_contacts

                    invented = drop_invented_contacts(blocks, known_text(site, contact_prompt))
                    if invented:
                        ai_log("info", "Invented contact details dropped", page=page["title"], edits=invented[:6])
                    veiled = repair_opaque_overlays(blocks, palette)
                    if veiled:
                        ai_log("info", "Opaque layers over photos made scrims", page=page["title"], edits=veiled)
                    # //// Neoffice — and copy laid on a photograph without a veil gets the design system's
                    # //// scrim (contrast.veil_copy_on_photos)
                    from builder.site_ai.nora.contrast import veil_copy_on_photos

                    scrimmed = veil_copy_on_photos(blocks)
                    if scrimmed:
                        ai_log("info", "Copy on photos given a scrim", page=page["title"], edits=scrimmed)
                    # //// Neoffice — and copy inside a scrim reads on it (contrast.read_over_photos): a
                    # //// hero's heading was white and read, its "Shop now" link black and invisible on
                    # //// the same photograph (2026-09-15)
                    from builder.site_ai.nora.contrast import read_over_photos

                    on_scrim = read_over_photos(blocks, palette)
                    if on_scrim:
                        ai_log("info", "Dark copy on a scrim given the reading ink", page=page["title"], edits=on_scrim)
                    # //// Neoffice — and the tiles of one grid are alike: a category tile left flat beside
                    # //// photographed ones takes its category's photograph (layout.complete_tile_photos)
                    from builder.site_ai.nora.layout import complete_tile_photos

                    completed = complete_tile_photos(blocks, site.get("category_photos") or {})
                    if completed:
                        ai_log("info", "Category tiles given their photographs", page=page["title"], edits=completed)
                    # //// Neoffice — and no photograph twice on one page (layout.one_photo_once): a home
                    # //// opened on a skateboarder and showed the same skateboarder again three sections
                    # //// down, beside its statement (2026-09-15)
                    from builder.site_ai.nora.layout import one_photo_once

                    swapped = one_photo_once(blocks, photos)
                    if swapped:
                        ai_log("info", "Repeated photographs replaced", page=page["title"], edits=swapped)
                    # //// Neoffice — and the emblem is an ornament or nothing (layout.drop_small_marks): offered
                    # //// as a quiet background layer, it came back as a 30px bullet beside a heading (2026-09-15)
                    if site.get("mark"):
                        from builder.site_ai.nora.layout import drop_small_marks, settle_bleeding_marks

                        dropped_marks = drop_small_marks(blocks, site["mark"])
                        # //// Neoffice — and a mark laid as a background layer stays INSIDE its
                        # //// section: right:-112px sliced a fifth of the glyph off (2026-09-16)
                        dropped_marks += settle_bleeding_marks(blocks, site["mark"])
                        if dropped_marks:
                            ai_log("info", "Emblem used as a bullet removed", page=page["title"], edits=dropped_marks)
                    # //// Neoffice — and a site whose mark is a circle of segments shows them in that
                    # //// shape: one circle, one part per category (layout.category_wheel). The brief
                    # //// picks it; every other site keeps its tiles.
                    if page["type"] == "accueil" and str(getattr(brief, "category_showcase", "") or "") == "Wheel":
                        from builder.site_ai.nora.layout import category_wheel

                        mark = ""
                        try:
                            mark = str(config.get("logo_image") or "") if hasattr(config, "get") else ""
                        except Exception:
                            mark = ""
                        from builder.site_ai.nora.layout import repeater_rows

                        rows = repeater_rows(data_script)
                        if category_wheel(blocks, site.get("category_photos") or {}, hub_image=mark, data_rows=rows):
                            ai_log("info", "Categories drawn as a circle of parts", page=page["title"])
                    variants = repair_button_variants(blocks, palette)
                    if variants:
                        ai_log("info", "Button variants repaired", page=page["title"], edits=variants)
                    # no photo will come: the slots become plain blocks in the site's colours
                    if not images_on:
                        neutral = neutral_placeholders(blocks, palette, prefix)
                        if neutral:
                            ai_log("info", "Photo slots neutralised", page=page["title"], edits=neutral)
                    # a picture that would state something false is not drawn: a stranger's face
                    # for the practitioner the page names, a map with made-up streets (placeholders.py)
                    else:
                        withheld = neutral_named_slots(blocks, palette, prefix, names=[site_name, *categories])
                        if withheld:
                            ai_log("info", "Photo slots kept from the image job", page=page["title"], slots=withheld)
                    # one photo treatment for the whole site: on a black-and-white site every
                    # photograph is black and white, on every page (photo_treatment.py)
                    if palette_mode == "monochrome":
                        from builder.site_ai.nora.photo_treatment import grayscale_photos

                        treated = grayscale_photos(blocks, keep={logo_image} if logo_image else frozenset())
                        if treated:
                            ai_log("info", "Photos in black and white", page=page["title"], edits=len(treated))
                    # an interior page opens under the site's own title band (page_header.py)
                    if page["route"] != "home":
                        stripped = strip_title_band(blocks, page["title"])
                        if stripped:
                            ai_log("info", "Repeated title dropped", page=page["title"], edits=stripped)
                        # //// Neoffice — and no h1 of its own at all (layout.interior_top, 2026-09-16):
                        # //// the band steps aside for a leading h1, and five page tops out of six
                        # //// came out without it
                        from builder.site_ai.nora.layout import interior_top

                        demoted = interior_top(blocks, page["title"])
                        if demoted:
                            ai_log("info", "Interior page h1 demoted", page=page["title"], edits=demoted)
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
                        # nor an elision written with a space for its apostrophe (punctuation.py)
                        elided = french_elisions(blocks)
                        data_script, script_elided = script_elisions(data_script)
                        if elided or script_elided:
                            ai_log("info", "French apostrophes restored", page=page["title"], blocks=elided, data=script_elided)
                    # //// Neoffice — measured, so "less text" is a number and not an impression
                    ai_log("info", "Page copy measured", page=page["title"], words=page_word_count(blocks), density=site.get("copy_density"))
                if blocks:
                    break
                error = "the model returned no usable blocks"
            except Exception as e:
                error = str(e)[:200]
                ai_log("warning", "Page generation attempt failed", page=page["title"], attempt=attempt + 1, error=error)
        return blocks, data_script, error

    # the page that lists the offer: where the category tiles lead, and a page of tiles itself
    lister = listing_page(pages)
    lister_route = lister["route"] if lister else None
    site["listing_route"] = lister_route
    site["category_photos"] = category_photos
    site["contact_verified"] = contact_prompt != UNVERIFIED_CONTACT
    # the photographs each page was written with, and their roles: its revision keeps them
    planned_photos: dict[str, tuple[list[str], list[str]]] = {}
    for idx, page in enumerate(pages):
        if ctx.is_cancelled():
            cancelled = True
            break
        # //// Neoffice — the token ceiling stops the build BEFORE the next page, not in the middle
        # //// of one (meter.over_budget, 2026-09-15): what is written stays, the chrome and the menu
        # //// are still set below, and the summary names the page it stopped at.
        if over_budget_at:
            failed.append({"title": page["title"], "error": "the build's token budget was passed"})
            continue
        _progress(ctx, job_id, _("Writing page {0} of {1}: {2}").format(idx + 1, total, page["title"]), 10 + int(80 * idx / max(total, 1)), {"current_page": page["title"], "pages_created": created})
        page_photos, page_notes = photos_for_page(page, client_photos, photos_used, categories, copy_density == "minimal", listing=page["route"] == lister_route)
        blocks, data_script, error = write_page(page, page_photos or placeholder_photos(page, activity, categories, listing=page["route"] == lister_route), notes=page_notes or None)
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
        planned_photos[name] = (page_photos, page_notes)
        # //// Neoffice — "type" travels with the page (2026-09-15): the reviewer needs it to know
        # //// that the bracketed blanks of a legal page are deliberate (visual_check.LEGAL_CONTEXT).
        # //// Neoffice — the ground travels with the page (2026-09-17): the look measures it
        created.append({"name": name, "title": page["title"], "route": f"/{route}", "planned": page["route"], "type": page["type"], "background_mode": background_mode})
        # //// Neoffice — the ceiling, checked between pages (builder/ai/meter.py, 2026-09-15): the
        # //// build finishes what it has rather than dying, and says so in its summary.
        if (over := meter.over_budget()) and not over_budget_at:
            over_budget_at = page["title"]
            ai_log("warning", "Token budget passed", page=page["title"], over_by_k=over)
        ai_log("info", "Page written", page=page["title"], name=name, route=route, model=page_model)
        # //// Neoffice — the root follows the new home at once (see point_home_at): the old one was
        # //// deleted at the start of the build, and until this was set the site served the
        # //// instance's own welcome screen to its visitors.
        if page["route"] in ("home", "index") or f"/{route}" in ("/", "/home", "/index"):
            point_home_at(profile, name)
        # the next pages are told the headlines this one took (page_headlines)
        site.setdefault("headlines_by_route", {})[page["route"]] = page_headlines(blocks, categories)
        # //// Neoffice — the page is looked at as soon as it is written (2026-09-15). The model saw
        # //// its own work only at the very end, once every page was written the same way: a site came
        # //// out as four pages with the same defect. Now each page is rendered, screenshotted and read
        # //// the moment it is published; what the reviewer says fixes it on the spot, and the pages
        # //// that follow are told what was seen. The final pass stays for what this one cannot see
        # //// yet: the pictures are generated after the pages.
        if visual_check.enabled() and not ctx.is_cancelled():
            # //// Neoffice ▼▼▼ — the look has authority (2026-09-16). It used to be: one look, one
            # //// unread rewrite, publish. Three pages of a site went live with the judge's own
            # //// "not professional" on them. Now: measure and look; if refused or not clean,
            # //// rewrite on the points (the previous version in hand) and look AGAIN, up to
            # //// MAX_REVISIONS times; a page still refused at the end is HELD — not published,
            # //// not in the menu — and the user is asked. The judge is not the writer
            # //// (visual_check.judge_model).
            look, attempts = None, 0
            page_pictures = page_photos or placeholder_photos(page, activity, categories, listing=page["route"] == lister_route)
            for attempt in range(visual_check.MAX_REVISIONS + 1):
                if ctx.is_cancelled():
                    break
                with meter.kind(meter.READING):
                    # //// Neoffice — the page's own headlines: the render must show them (2026-09-17)
                    look = visual_check.review_page(created[-1], profile, judge, site_name=site_name, activity=activity, expect=site["headlines_by_route"].get(page["route"]) or [page["title"]])
                attempts += 1
                # //// Neoffice — a measured contrast is repaired on the spot and looked at again,
                # //// without a model call (contrast.repair_measured_contrast, 2026-09-17)
                if any(g.get("kind") == "unreadable-text" for g in look.get("gate") or []) and not look.get("error"):
                    from builder.site_ai.nora.contrast import repair_measured_contrast

                    stored_blocks, stored_script = stored_page(name)
                    measured_fixes = repair_measured_contrast(stored_blocks, look.get("gate") or [], palette)
                    if measured_fixes:
                        _write_page(page, stored_blocks, stored_script, profile, name, _describe(stored_blocks))
                        # the previous YAML stays the revision's anchor: a colour set here is
                        # measured and set again if the writer loses it
                        ai_log("info", "Measured contrast repaired", page=page["title"], fixes=measured_fixes[:4])
                        with meter.kind(meter.READING):
                            look = visual_check.review_page(created[-1], profile, judge, site_name=site_name, activity=activity, expect=site["headlines_by_route"].get(page["route"]) or [page["title"]])
                # the report is kept, with the page's state when it was read: the final pass
                # re-reads only what changed since (the pictures land after the pages)
                reviewed_already[name] = {"report": look, "modified": str(frappe.db.get_value("Builder Page", name, "modified") or "")}
                seen = visual_check.points_to_fix(look)
                if seen:
                    site.setdefault("seen_before", []).extend(f"{page['title']}: {i['problem']}" for i in seen[:3])
                for finding in look.get("chrome") or []:
                    if finding not in chrome_findings:
                        chrome_findings.append(finding)
                # //// Neoffice — medium points are revised once, then the page is accepted if the
                # //// judge calls it professional and nothing is measured against it (visual_check.accepted)
                if visual_check.accepted(look, lenient=attempt >= 1):
                    if attempt == 0:
                        first_look_accepted += 1
                    else:
                        accepted_later += 1
                    break
                if look.get("error") and not look.get("http_error"):
                    # a page that could not be read is not rewritten on nothing
                    break
                if attempt == visual_check.MAX_REVISIONS:
                    break
                _progress(ctx, job_id, _("Fixing {0} after looking at it ({1}/{2})").format(page["title"], attempt + 1, visual_check.MAX_REVISIONS), 10 + int(80 * idx / max(total, 1)), {"pages_created": created})
                fixed, fixed_script, fix_error = write_page(page, page_pictures, notes=page_notes or None, revision=visual_check.revision_instructions(seen, look.get("gate")))
                if not fixed:
                    ai_log("warning", "The look found points but the fix failed", page=page["title"], error=fix_error)
                    break
                _write_page(page, fixed, fixed_script, profile, name, _describe(fixed))
                site["headlines_by_route"][page["route"]] = page_headlines(fixed, categories)
                reviewed_already.pop(name, None)
                ai_log("info", "Page revised after the look", page=page["title"], attempt=attempt + 1, points=len(seen), measured=len(look.get("gate") or []))
            if look is not None:
                looked[name] = attempts
                if visual_check.refused(look):
                    essential = page["route"] in ("home", "index") or f"/{route}".rstrip("/") == (cta[1] or "").rstrip("/")
                    why = visual_check.why_refused(look)
                    held.append({"name": name, "title": page["title"], "route": f"/{route}", "attempts": attempts, "why": why, "essential": essential})
                    ai_log("warning", "Page refused after its revisions", page=page["title"], attempts=attempts, essential=essential, why=why[:300])
            # //// Neoffice ▲▲▲
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

    # //// Neoffice — a refused page is not published and not in the menu (2026-09-16), unless the
    # //// site cannot stand without it (the home, the page the call to action leads to): those stay
    # //// up, flagged, and the user is asked. Nothing the judge refused goes live in silence.
    hidden = {h["name"] for h in held if not h["essential"]}
    for h in held:
        if h["name"] not in hidden:
            continue
        try:
            frappe.db.set_value("Builder Page", h["name"], "published", 0, update_modified=False)
            frappe.db.commit()
        except Exception as e:
            ai_log("warning", "Refused page not unpublished", page=h["title"], error=str(e)[:120])
    shown = [p for p in created if p["name"] not in hidden]
    # //// Neoffice — a link to a held page would be a dead link (2026-09-17): a home's category tile
    # //// pointed at /nos-marques#snow while that page was held. Those links go to the home until
    # //// the page is rebuilt, and the summary says so.
    if hidden:
        from builder.site_ai.nora.buttons import repoint_links

        held_routes = [h["route"] for h in held if h["name"] in hidden]
        for p in shown:
            try:
                stored_blocks, stored_script = stored_page(p["name"])
                moved_links = repoint_links(stored_blocks, held_routes, "/")
                if moved_links:
                    _write_page(by_route_page(pages, p), stored_blocks, stored_script, profile, p["name"], _describe(stored_blocks))
                    ai_log("info", "Links to a held page repointed", page=p["title"], edits=moved_links)
            except Exception as e:
                ai_log("warning", "Links to a held page not repointed", page=p["title"], error=str(e)[:160])
    # 6. menu, footer, home
    _progress(ctx, job_id, _("Menu, footer and home page"), 92, {"pages_created": created})
    apply_navigation(config, shown, site_type, activity, profile, lang_code, site_name=site_name)

    # 7. the images: the client's own photographs first, drawings only for what is left
    # //// Neoffice ▼▼▼ — a client who supplies photographs wants THEM on the page, and a
    # //// drawn stand-in beside them is the tell that nobody read the brief. The library
    # //// (Builder Content Asset) and its matcher already existed for the old onboarding
    # //// wizard and no caller reached them; the build now places from the library, then
    # //// draws only the slots no photograph fits.
    placed = 0
    if client_photos:
        try:
            # after the menu (92), not before it: the bar went 92, 90 (2026-09-13)
            _progress(ctx, job_id, _("Placing your photos"), 93, {"pages_created": created})
            from builder.site_ai.ingestion.image_matcher import match_and_apply

            report = match_and_apply(ctx.session_id, [p["name"] for p in created])
            placed = report.get("matched") or 0
            ai_log("info", "Client photos placed", placed=placed, slots=report.get("slots"), assets=report.get("assets"))
        except Exception as e:
            ai_log("warning", "Client photos not placed", error=str(e)[:200])
    # //// Neoffice ▲▲▲
    pending, image_job = 0, None
    try:
        slots = _scan_placeholder_images([p["name"] for p in created], subject=activity[:180], avoid=(site_name,))
        pending = len(slots)
        if slots and _image_backend_available():
            image_job = _enqueue_image_generation(slots)
    except Exception as e:
        ai_log("warning", "Image generation not started", error=str(e)[:200])

    # 8. the final look: each page rendered, screenshotted and read against the brief by the
    # vision model; the body defects come back as one revision pass (visual_check.py). A fact
    # the brief never gave (a price, a year, a testimonial) sends the page back too (facts.py)
    reviews, revised, facts_left = [], {}, {}

    def item_for(name: str) -> dict:
        return next(p for p in created if p["name"] == name)

    if created and not cancelled:
        try:
            by_name = {p["name"]: p for p in pages_by_name(pages, created)}
            if visual_check.enabled():
                _progress(ctx, job_id, _("Visual check: waiting for the images"), 95, {"pages_created": created})
                # //// Neoffice — the text-to-image backend answers in 60 to 70 s per picture (Codex behind the ComfyUI proxy): the wait budget follows the number of slots (77601a8e "fix(images): prompts with photographic direction only, and budgets sized on the slot count")
                # a picture takes 60 to 70 s on the Codex backend: the wait follows the slot count
                visual_check.wait_for_images(image_job, timeout=min(1800, max(visual_check.IMAGE_WAIT_SECONDS, 75 * pending + 120)))
                for item in created:
                    if ctx.is_cancelled():
                        break
                    # //// Neoffice — a page the look refused and unpublished is not read again here
                    if item["name"] in hidden:
                        continue
                    # //// Neoffice — a page the reviewer already read, and that nothing has touched
                    # //// since, is not screenshotted and read a second time (2026-09-15). The
                    # //// reason this pass exists is that the generated pictures land AFTER the
                    # //// pages are written — so it re-reads the pages that actually changed, and
                    # //// reuses the report for the rest. Reading a page costs six times writing it.
                    earlier_read = reviewed_already.get(item["name"])
                    # //// Neoffice — NOT named `now`: frappe.utils.now is imported at module level,
                    # //// and a local of that name shadows it for the WHOLE function — the build
                    # //// died on UnboundLocalError at its first status update (2026-09-15).
                    last_change = str(frappe.db.get_value("Builder Page", item["name"], "modified") or "")
                    if earlier_read and earlier_read["modified"] == last_change:
                        reviews.append(earlier_read["report"])
                        continue
                    _progress(ctx, job_id, _("Visual check: {0}").format(item["title"]), 96, {"pages_created": created})
                    with meter.kind(meter.READING):
                        # //// Neoffice — read by the judge, not the writer (2026-09-16)
                        reviews.append(visual_check.review_page(item, profile, judge, site_name=site_name, activity=activity))
            known = known_text(site, contact_prompt)
            earlier: list[str] = []
            for item in created:
                stored_blocks, stored_script = stored_page(item["name"])
                found = invented_facts(stored_blocks, stored_script, known, today=frappe.utils.today())
                # a page written later does not say again what an earlier one said (headline_echoes)
                echoes = headline_echoes(stored_blocks, earlier)
                earlier += page_headlines(stored_blocks, categories)
                if not found and not echoes:
                    continue
                if found:
                    ai_log("info", "Invented facts found", page=item["title"], facts=[f["text"] for f in found][:12])
                if echoes:
                    ai_log("info", "Headlines another page already says", page=item["title"], lines=[e["problem"][:120] for e in echoes])
                review = next((r for r in reviews if r["name"] == item["name"]), None)
                if review is None:
                    review = {"name": item["name"], "title": item["title"], "route": item["route"], "professional": None, "issues": [], "error": None, "overall": ""}
                    reviews.append(review)
                review["issues"] = facts_issues(found) + echoes + review["issues"]
                if found:
                    review["facts"] = len(found)
            # every page stating made-up facts is revised; the designer's points take the places
            # left: the pages that failed the first glance first, then the ones with most defects
            # //// Neoffice — the final pass revises what is WORTH a rewrite (2026-09-17): a refusal, a
            # //// high point, a measured break, an invented fact. The medium leftovers of a page the loop
            # //// accepted are not chased again: the first full run rewrote three accepted pages here on
            # //// their leftovers, after their last look, and shipped them unread.
            def worth_a_rewrite(r):
                return (
                    r.get("facts")
                    or r["professional"] is False
                    or any(i.get("severity") == "high" for i in r["issues"])
                    or any(g.get("severity") == "high" for g in r.get("gate") or [])
                )

            ranked = sorted(
                # //// Neoffice — a measured point counts like a seen one, and a hidden page is left alone (2026-09-16)
                [r for r in reviews if worth_a_rewrite(r) and r["name"] in by_name and r["name"] not in hidden],
                key=lambda r: (r["professional"] is not False, -len(r["issues"]) - len(r.get("gate") or [])),
            )
            todo = [r for r in ranked if r.get("facts")] + [r for r in ranked if not r.get("facts")][: visual_check.MAX_REVISIONS]
            for r in todo:
                if ctx.is_cancelled():
                    break
                _progress(ctx, job_id, _("Fixing {0} after the visual check").format(r["title"]), 97, {"pages_created": created})
                page = by_name[r["name"]]
                stored = frappe.db.get_value("Builder Page", r["name"], ["blocks", "page_data_script"], as_dict=True) or frappe._dict()
                # the photographs the page was written with, their roles kept, then the ones it
                # carries besides (the client's own included, not only the drawn ones)
                planned, planned_notes = planned_photos.get(r["name"], ([], []))
                photos, notes = revision_photos(planned, planned_notes, stored.get("blocks"), stored.get("page_data_script"))
                blocks, data_script, error = write_page(page, photos or placeholder_photos(page, activity, categories, listing=page["route"] == lister_route), notes=notes, revision=visual_check.revision_instructions(r["issues"], r.get("gate")))
                if not blocks:
                    ai_log("warning", "Revision pass failed", page=r["title"], error=error)
                    continue
                _write_page(page, blocks, data_script, profile, r["name"], _describe(blocks))
                revised[r["name"]] = len(r["issues"])
                ai_log("info", "Page revised after the visual check", page=r["title"], issues=len(r["issues"]))
                # //// Neoffice — and looked at again (2026-09-17): a rewrite nobody reads is the fault
                # //// this whole gate exists to end. A rewrite the look refuses is held like any other.
                with meter.kind(meter.READING):
                    again = visual_check.review_page(item_for(r["name"]), profile, judge, site_name=site_name, activity=activity, expect=page_headlines(blocks, categories) or [page["title"]])
                r.update({k: again.get(k) for k in ("professional", "issues", "overall", "gate", "chrome", "error", "http_error", "all_issues")})
                if visual_check.refused(again) and r["name"] not in {h["name"] for h in held}:
                    essential = page["route"] in ("home", "index") or f"/{page['route']}".rstrip("/") == (cta[1] or "").rstrip("/")
                    held.append({"name": r["name"], "title": r["title"], "route": item_for(r["name"])["route"], "attempts": looked.get(r["name"], 0) + 1, "why": visual_check.why_refused(again), "essential": essential})
                    if not essential:
                        hidden.add(r["name"])
                        frappe.db.set_value("Builder Page", r["name"], "published", 0, update_modified=False)
                        frappe.db.commit()
                    ai_log("warning", "Page refused after the final revision", page=r["title"], essential=essential, why=visual_check.why_refused(again)[:300])
            # what the revision still left made up is said in the summary, not revised again
            for r in todo:
                if r.get("facts") and r["name"] in revised:
                    left = page_facts(r["name"], known)
                    if left:
                        facts_left[r["title"]] = [f["text"] for f in left][:6]
                        ai_log("warning", "Invented facts left after the revision", page=r["title"], facts=facts_left[r["title"]])
            if revised:
                slots = _scan_placeholder_images([n for n in revised], subject=activity[:180], avoid=(site_name,))
                if slots:
                    _enqueue_image_generation(slots)
                    ai_log("info", "Images re-queued after the revision pass", slots=len(slots))
        except Exception as e:
            ai_log("warning", "Visual check skipped", error=str(e)[:200])
    # //// Neoffice — a page held by the final pass leaves the menu too (2026-09-17)
    if any(h["name"] in hidden for h in held) and len([p for p in created if p["name"] not in hidden]) != len(shown):
        shown = [p for p in created if p["name"] not in hidden]
        try:
            apply_navigation(config, shown, site_type, activity, profile, lang_code, site_name=site_name)
        except Exception as e:
            ai_log("warning", "Menu not rebuilt after the final pass", error=str(e)[:160])

    duration = int(time.time() - started)
    _update_generation_status(job_id, {
        "status": "completed", "progress": 100, "total_pages": total, "current_step": "Completed", "current_page": None,
        "pages_created": created, "remaining_image_slots": pending, "image_job_id": image_job, "error": None,
        "site_name": site_name, "completed_at": now(), "duration_seconds": duration,
        # //// Neoffice — what the look refused, for the panel (2026-09-16)
        "held": [{"title": h["title"], "route": h["route"], "why": h["why"][:200]} for h in held],
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
    # //// Neoffice — what it cost, in the summary the operator reads (2026-09-15): four full
    # //// rebuilds emptied a prepaid balance in a day and nothing anywhere said where it went.
    spent = meter.stop()
    if over_budget_at:
        lines.append(
            f"The build stopped writing new pages after '{over_budget_at}': it passed the token budget set "
            "for this site (nora_build_token_budget in site_config). Raise it, or build the rest in a second run."
        )
    if line := meter.summary_line(spent):
        lines.append(line)
        ai_log("info", "Build spend", **{k: v for k, v in spent.items() if k != "by_kind"}, by_kind=spent.get("by_kind"))
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
    if contact_prompt == UNVERIFIED_CONTACT:
        lines.append(
            "No contact details are verified for this business, so the site shows none, only the contact form. "
            "Ask the client for the address, phone and e-mail to show, then add them."
        )
    # //// Neoffice — the blanks a legal page still carries, named in the summary (2026-09-15): the
    # //// reviewer once erased them and the list of what the merchant must supply went with them.
    # //// On the page they are honest; in the summary they are actionable.
    for item in created:
        if str(item.get("type") or "") != "legal":
            continue
        try:
            blocks, _script = stored_page(item["name"])
            blanks = sorted({b.strip() for b in re.findall(r"\[[^\]\[]{3,90}\]", json.dumps(blocks, ensure_ascii=False))})
        except Exception:
            blanks = []
        if blanks:
            lines.append(
                f"'{item['title']}' leaves {len(blanks)} blank(s) only the merchant can fill: "
                + "; ".join(b[:70] for b in blanks[:6])
            )

    # //// Neoffice ▼▼▼ — what a shop still needs from its owner (2026-09-15). The build can write
    # //// the legal pages and place the product row, but it cannot invent the merchant's own phone
    # //// number, nor photograph their articles: those are asked for here, in the summary the
    # //// operator reads, instead of shipping silently without them.
    if _sells_here:
        still_missing = missing_legal_pages(profile)
        if still_missing:
            names = {"terms": "terms and conditions", "privacy": "privacy policy"}
            lines.append(
                "This shop still has no " + " and no ".join(names[k] for k in still_missing)
                + ": no payment provider and no ad network accepts a shop without them. Offer to write them."
            )
        try:
            from builder.empty_includes import include_has_data

            if include_has_data("webshop/templates/includes/product_carousel.html", profile) is False:
                lines.append(
                    "None of the shop's published articles carries a photograph, so no product row was placed: "
                    "ask the client for product pictures, then the home can show what they sell."
                )
        except Exception:
            pass
    if contact_prompt != UNVERIFIED_CONTACT and str(getattr(config, "business_name", "") or "").strip():
        if not contact_data.get("phone") or not contact_data.get("email"):
            lines.append(
                f"'{config.business_name}' publishes no phone or e-mail of its own, and the company's belong to "
                "another business, so the site shows none: ask the client for the line this shop answers on."
            )
    # //// Neoffice ▲▲▲
    # //// Neoffice — the quality line (2026-09-16): the one number that says whether the writing
    # //// improves, build after build — how many pages passed at first look.
    if looked:
        # a page the look could not read (the judge down, the render failing) is none of the
        # three: it is said as such, never counted as revised
        unread = max(0, len(looked) - first_look_accepted - accepted_later - len(held))
        lines.append(
            f"Quality: {first_look_accepted} of {len(looked)} page(s) accepted at first look, "
            f"{accepted_later} after a revision, {len(held)} refused" + (f", {unread} not read (the look failed)." if unread else ".")
        )
    if chrome_findings:
        lines.append(
            "Measured on the site's chrome, not on a page: " + "; ".join(f"{c['where']}: {c['detail']}" for c in chrome_findings[:3])
            + ". The header and footer are set in Settings > Theme: tell the user (a logo is uploaded there), do not rewrite a page for it."
        )
    lines += visual_check.summary_lines(reviews, revised, held)
    rewritten = [r["title"] for r in reviews if r.get("facts") and r["name"] in revised]
    if rewritten:
        lines.append(
            "Facts the brief did not give (prices, durations, years, figures, testimonials) were found on "
            + ", ".join(rewritten) + ": those pages were rewritten without them."
        )
    for title, texts in facts_left.items():
        lines.append(f"Still on {title} after that rewrite, to confirm with the client or remove: " + ", ".join(texts))
    return "\n".join(lines)
