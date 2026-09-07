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
import time
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import now

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


def normalise_pages(pages: list, site_type: str) -> list[dict]:
    """Every page gets a route and a type; the home page comes first."""
    out, seen = [], set()
    for raw in pages or []:
        if isinstance(raw, str):
            raw = {"title": raw}
        title = (raw.get("title") or "").strip()
        if not title:
            continue
        route, ptype = KNOWN_PAGES.get(_bare(title), (None, None))
        route = (raw.get("route") or route or _slug(title)).strip("/") or _slug(title)
        ptype = raw.get("type") or ptype or "generic"
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


def mint_tokens(prefix: str, group: str, brief, primary: str, secondary: str) -> dict:
    """Six Builder Tokens with stable ids: the site's design system, referenced by
    the pages as var(--<prefix>-<key>) and by the chrome through its aliases."""
    background = (getattr(brief, "section_backgrounds", None) or ["#ffffff"])[0] or "#ffffff"
    spec = [
        ("primary", "Color", primary or getattr(brief, "primary_color", "") or "#1a1a1a"),
        ("secondary", "Color", secondary or getattr(brief, "secondary_color", "") or "#444444"),
        ("background", "Color", background),
        ("text", "Color", getattr(brief, "body_color", "") or getattr(brief, "heading_color", "") or "#1a1a1a"),
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


def page_brief_text(site: dict, brief, page: dict, handles: dict, contact_prompt: str, layout_system: str, language: str, photos: list[str], cta: tuple[str, str]) -> str:
    is_home = page["route"] == "home"
    plan = SECTION_PLANS.get(page["type"], SECTION_PLANS["generic"])
    sections = "\n".join(f"{i}. {s}" for i, s in enumerate(plan, 1))
    concept = getattr(brief, "design_concept", "") or ""
    signature = getattr(brief, "signature_element", "") or ""
    tone = getattr(brief, "site_tone", "") or ""
    hero = getattr(brief, "hero_style", "") or ""
    photo_lines = "\n".join(f"{i}. {u}" for i, u in enumerate(photos, 1))
    page_role = (
        "the HOME page: open with the hero" if is_home
        else "an INTERIOR page: the site renders a title band with the page title above the content, so start directly with the first content section, no hero banner and no repeated page title"
    )
    lines = [
        f"DESIGN DIRECTION: {concept or 'a distinctive direction that fits the brand'} (tone: {tone or 'professional'}; hero style: {hero or 'free'}).",
        f"LAYOUT SYSTEM: {layout_system}. SIGNATURE MOVE: {signature or 'choose one that fits the system'}. Keep the SAME system and move on every page of this site.",
        f"BRAND: {site['site_name']}. Activity: {site['activity']}",
        f"POSITIONING: {site.get('differentiators') or 'derive it from the activity'}",
        contact_prompt.strip() if contact_prompt else "",
        (
            f"PALETTE (token handles, use them for every brand colour): primary {handles['primary']}, secondary {handles['secondary']}, "
            f"background {handles['background']}, text {handles['text']}. Literal hex only for derived shades (rgba() tints)."
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
        f"CTA: the primary button says '{cta[0]}' and links to '{cta[1]}'; use it once in the hero (home) or the last section, and in the final band.",
        (
            "PHOTOS AVAILABLE (placeholders that the site replaces with real photos after the build; use each at most once, "
            f"copy the URL exactly, give it a descriptive alt in {language}):\n{photo_lines}"
        ),
        (
            "RULES: no header, navigation or footer sections (the site chrome is rendered around the page); no lorem; "
            f"business data verbatim; spell the brand name exactly '{site['site_name']}'; every text in {language}; "
            "no em dashes; mobile-first m_style on every grid."
        ),
    ]
    return "\n".join(line for line in lines if line)


def _progress(ctx, job_id: str, message: str, progress: int, extra: dict | None = None) -> None:
    from builder.api import _update_generation_status

    try:
        ctx.emit("progress", message=message)
    except Exception:
        pass
    _update_generation_status(job_id, {"status": "running", "progress": progress, "current_step": message, **(extra or {})})


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
    frappe.db.set_value(
        "Builder Page",
        name,
        {"route": route, "ai_generated_at": now(), "ai_blocks_hash": _blocks_fingerprint(payload)},
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


def apply_navigation(config, created: list[dict], site_type: str, description: str, profile: str | None) -> None:
    """Menu, footer and home page from the pages just built (the worker's step 5)."""
    config.menu_items = []
    seen = set()
    for page in created:
        route = page["route"]
        if route in seen:
            continue
        seen.add(route)
        home = route in ("/", "/home", "/index")
        config.append("menu_items", {"label": _("Home") if home else page["title"], "url": "/" if home else route, "is_external": False, "open_in_new_tab": False})
        if site_type in ("ecommerce", "ecommerce_search") and home:
            config.append("menu_items", {"label": _("Shop"), "url": "/all-products", "is_external": False, "open_in_new_tab": False})
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
            config.append("footer_links", {"column_name": _("Navigation"), "label": _("Home") if home else page["title"], "url": "/" if home else page["route"]})
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
    from builder.site_ai.nora.prompts import page_profile

    started = time.time()
    site_name = (spec.get("site_name") or "").strip()
    activity = (spec.get("activity") or "").strip()
    if not site_name or not activity:
        return "FAILED: site_name and activity are required."
    site_type = spec.get("site_type") if spec.get("site_type") in SECTION_PLANS or spec.get("site_type") in ("vitrine", "ecommerce", "saas", "blog", "portfolio", "one_page") else "vitrine"
    pages = normalise_pages(spec.get("pages") or [], site_type)
    profile = (spec.get("website_profile") or "").strip() or page_profile(ctx.page_id)
    if profile and not frappe.db.exists("Website Profile", profile):
        return f"FAILED: unknown website_profile '{profile}'."
    replace_existing = spec.get("replace_existing") or "auto"
    language = (spec.get("language") or frappe.db.get_single_value("Builder Settings", "default_language") or "fr").strip()
    language = {"fr": "French", "en": "English", "de": "German", "it": "Italian"}.get(language.lower(), language)
    primary = (spec.get("primary_color") or "").strip() or None
    secondary = (spec.get("secondary_color") or "").strip() or None
    logo_image = (spec.get("logo_image") or "").strip() or None
    job_id = f"site_gen_{frappe.generate_hash(length=10)}"
    total = len(pages)
    _update_generation_status(job_id, {"status": "running", "progress": 0, "total_pages": total, "current_step": "Starting", "pages_created": [], "error": None, "site_name": site_name, "started_at": now()})
    ai_log("info", "=== NORA SITE BUILD STARTED ===", job_id=job_id, site_name=site_name, profile=profile, pages=[p["title"] for p in pages])

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
        return (
            f"CONFIRM_NEEDED: {len(protected)} existing page(s) were designed or edited by hand ({names}). "
            "Ask the user whether to replace them (replace_existing='force'), keep them and add the new pages beside "
            "(replace_existing='none'), then call generate_site again with the same arguments plus their choice."
        )
    to_delete = [] if replace_existing == "none" else [p["name"] for p in classes["untouched"]]
    if replace_existing == "force":
        to_delete += [p["name"] for p in classes["protected"]]
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
    config.logo_type = "Image" if (logo_image or config.get("logo_image")) else "Text"
    if logo_image:
        config.logo_image = logo_image
    config.logo_text = site_name
    if hasattr(config, "footer_logo_text"):
        config.footer_logo_text = site_name
    if primary and hasattr(config, "primary_color"):
        config.primary_color = primary
    if secondary and hasattr(config, "secondary_color"):
        config.secondary_color = secondary
    contact_page = next((p for p in pages if p["type"] == "contact"), None)
    cta = (_("Contact us"), f"/{contact_page['route']}" if contact_page else "/")
    config.cta_text, config.cta_url = cta
    if primary and hasattr(config, "cta_button_color"):
        config.cta_button_color = primary
    config.menu_items = []
    config.save(ignore_permissions=True)
    frappe.db.commit()

    # 3. the design brief (K3 with design intelligence), grounded in real business data
    _progress(ctx, job_id, _("Writing the design brief"), 8)
    contact_data = get_site_contact_context(profile)
    contact_prompt = _contact_context_prompt(contact_data) or ""
    if not logo_image and contact_data.get("logo"):
        logo_image = contact_data["logo"]
    prompt = f"{site_name}: {activity}. {spec.get('differentiators') or ''} Style: {spec.get('style_direction') or ''}{contact_prompt}"
    settings = get_ai_settings()
    brief = None
    try:
        logo_url = (frappe.utils.get_url() + logo_image) if logo_image and logo_image.startswith("/") else logo_image
        brief, validation = BriefGenerator(provider="litellm", model=ctx.model, config=settings).generate_brief_with_validation(
            prompt=prompt,
            site_name=site_name,
            site_type=site_type,
            theme="modern",
            primary_color=primary,
            secondary_color=secondary,
            pages_config=pages,
            max_retries=2,
            logo_image=logo_url,
        )
        ai_log("info", "Design brief ready", tone=brief.site_tone, valid=validation.is_valid)
    except Exception as e:
        ai_log("warning", "Design brief failed, using defaults", error=str(e)[:200])
        frappe.log_error("Nora site build: design brief failed", frappe.get_traceback())
        brief = get_default_brief(theme="modern", primary_color=primary, secondary_color=secondary)
    primary = primary or getattr(brief, "primary_color", None)
    secondary = secondary or getattr(brief, "secondary_color", None)

    # 4. the design system as tokens, and the chrome from the brief
    prefix = token_prefix(profile or site_name)
    handles = mint_tokens(prefix, profile or site_name, brief, primary, secondary)
    try:
        apply_brief_site_chrome(brief, website_profile=profile)
        config = _get_site_chrome_config(profile)
        if getattr(brief, "heading_font", None):
            config.heading_font = brief.heading_font
            config.body_font = brief.body_font or "Inter"
        # the brief behind the site, shown under Settings > Theme ("what the AI decided")
        if hasattr(config, "ai_brief"):
            try:
                config.ai_brief = brief.model_dump_json() if hasattr(brief, "model_dump_json") else json.dumps(brief.__dict__, default=str)
            except Exception:
                pass
        for field in ("primary_color", "secondary_color", "background_color", "text_color"):
            value = {"primary_color": primary, "secondary_color": secondary, "background_color": (brief.section_backgrounds or [None])[0] if getattr(brief, "section_backgrounds", None) else None, "text_color": getattr(brief, "body_color", None)}.get(field)
            if value and hasattr(config, field):
                config.set(field, value)
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
    site = {"site_name": site_name, "activity": activity, "differentiators": spec.get("differentiators")}
    created, failed, cancelled = [], [], False
    for idx, page in enumerate(pages):
        if ctx.is_cancelled():
            cancelled = True
            break
        _progress(ctx, job_id, _("Writing page {0} of {1}: {2}").format(idx + 1, total, page["title"]), 10 + int(80 * idx / max(total, 1)), {"current_page": page["title"], "pages_created": created})
        brief_text = page_brief_text(site, brief, page, handles, contact_prompt, layout_system, language, placeholder_photos(page, activity), cta)
        messages = [
            {"role": "system", "content": Prompts.GENERATION_YAML},
            {"role": "user", "content": f"Build this page now:\n{brief_text}"},
        ]
        blocks, data_script, error = [], "", None
        for attempt in range(2):
            try:
                raw = llm.complete(page_model, messages, llm.TASK_PARAMS["complex"], stream=False)
                blocks, data_script = expand_page_yaml(BlockCodec.strip_fences(raw))
                if blocks:
                    break
                error = "the model returned no usable blocks"
            except Exception as e:
                error = str(e)[:200]
                ai_log("warning", "Page generation attempt failed", page=page["title"], attempt=attempt + 1, error=error)
        if not blocks:
            failed.append({"title": page["title"], "error": error})
            frappe.log_error(f"Nora site build: page failed: {page['title']}", error or "no blocks")
            continue
        use_host = host_page if (host_reusable and page["route"] == "home") else None
        name, route = _write_page(page, blocks, data_script, profile, use_host, _describe(blocks))
        created.append({"name": name, "title": page["title"], "route": f"/{route}"})
        ai_log("info", "Page written", page=page["title"], name=name, route=route, model=page_model)
        if use_host:
            try:
                ctx.emit("refetch", resources=["page", "page_data"], after_commit=True)
            except Exception:
                pass

    if not created:
        _update_generation_status(job_id, {"status": "failed", "progress": 0, "error": "no page could be generated", "pages_created": []})
        return "FAILED: no page could be generated (" + "; ".join(f"{f['title']}: {f['error']}" for f in failed) + "). Tell the user and offer to try again."

    # 6. menu, footer, home
    _progress(ctx, job_id, _("Menu, footer and home page"), 92, {"pages_created": created})
    apply_navigation(_get_site_chrome_config(profile), created, site_type, activity, profile)

    # 7. the images, in the background
    pending, image_job = 0, None
    try:
        slots = _scan_placeholder_images([p["name"] for p in created], subject=activity[:180])
        pending = len(slots)
        if slots and _image_backend_available():
            image_job = _enqueue_image_generation(slots)
    except Exception as e:
        ai_log("warning", "Image generation not started", error=str(e)[:200])

    duration = int(time.time() - started)
    _update_generation_status(job_id, {
        "status": "completed", "progress": 100, "total_pages": total, "current_step": "Completed", "current_page": None,
        "pages_created": created, "remaining_image_slots": pending, "image_job_id": image_job, "error": None,
        "site_name": site_name, "completed_at": now(), "duration_seconds": duration,
    })
    ai_log("info", "=== NORA SITE BUILD COMPLETED ===", job_id=job_id, pages=len(created), failed=len(failed), duration=duration)
    lines = [f"DONE in {duration // 60} min {duration % 60} s. Site '{site_name}'" + (f" on profile '{profile}'" if profile else "") + ":"]
    lines += [f"- {p['title']} -> {p['route']} (page {p['name']})" for p in created]
    if failed:
        lines.append("Pages that failed (offer to retry them one by one with generate_page on their page): " + ", ".join(f"{f['title']} ({f['error']})" for f in failed))
    if cancelled:
        lines.append("The build was cancelled by the user before every page was written.")
    lines.append(f"Design tokens minted with prefix '{prefix}': " + ", ".join(handles.values()) + ".")
    lines.append(f"{pending} photo slot(s) are being filled with generated images in the background" + (f" (job {image_job})" if image_job else " (no image backend configured: they stay placeholders)") + ".")
    if host_reusable and any(p["name"] == host_page for p in created):
        lines.append("The page open in the editor is now the home page; the canvas has been refreshed.")
    lines.append("The header, the menu and the footer are set from the brief (Settings > Theme).")
    return "\n".join(lines)
