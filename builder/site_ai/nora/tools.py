"""The generate_site tool: our site pipeline, callable by the editor agent."""

from __future__ import annotations

import frappe

from builder.ai.agent.registry import Tool

# vitrine_user: a showcase whose customers sign in (account entry in the header); ecommerce:
# the online shop (account, cart, search); ecommerce_search: the same with an inline search bar
SITE_TYPES = ["vitrine", "vitrine_user", "one_page", "blog", "ecommerce", "ecommerce_search", "saas", "portfolio"]


def run_generate_site(ctx, args: dict) -> str:
    from builder.site_ai.nora.site_builder import build_site

    try:
        return build_site(ctx, args or {})
    except Exception as e:
        frappe.log_error("generate_site failed", frappe.get_traceback())
        return f"FAILED: the site generation stopped with an error: {str(e)[:300]}. Tell the user, and suggest trying again."


generate_site = Tool(
    name="generate_site",
    side="server",
    handler=run_generate_site,
    description=(
        "Build a COMPLETE site for this business: the design brief, the site's design tokens, the header and "
        "footer (chrome), every requested page written and published, the menu and the footer links, the home "
        "page, and the images (generated afterwards in the background). Call it ONLY after the user approved "
        "the recap card of the site playbook. Runs for several minutes and streams its progress; returns the "
        "list of created pages, or CONFIRM_NEEDED when existing hand-made pages would be replaced (then ask the "
        "user and call again with replace_existing set to their choice)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "site_name": {"type": "string", "description": "The business or project name, as the site should show it."},
            "activity": {"type": "string", "description": "What the business does, in one to three sentences, in the user's words."},
            "differentiators": {"type": "string", "description": "What makes it different: positioning, tone, values, signature offer."},
            "pages": {
                "type": "array",
                "description": "The pages to build, in menu order. Each {title, route?, type?}; route and type are derived from the title when omitted.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "route": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["title"],
                },
            },
            "site_type": {"type": "string", "enum": SITE_TYPES, "description": "Kind of site: vitrine (showcase, default), vitrine_user (showcase with customer accounts), ecommerce (online shop: account, cart, search), ecommerce_search (shop with an inline search bar), blog, portfolio, saas, one_page. It sets the header and footer (account entry, cart, search, footer template)."},
            "primary_color": {"type": "string", "description": "Hex colour chosen by the user, or the primary of the palette they picked."},
            "secondary_color": {"type": "string", "description": "Hex colour, optional."},
            "style_direction": {"type": "string", "description": "The layout direction the user picked, in a few words (e.g. 'editorial grid, calm', 'bold poster')."},
            "logo_image": {"type": "string", "description": "Site file URL of the uploaded logo (/files/...), if any."},
            # //// Neoffice — inspiration bounds widened from 3 to 8 (a screenshot and a colour
            # //// count are cheap), and two new fields: `photos` for the client's own pictures
            # //// to place in the pages, `palette_mode` for an explicit "no colour" direction
            # //// (918629eb "feat(site build): the client's own photographs, every reference site, and a monochrome direction")
            "inspiration_urls": {"type": "array", "items": {"type": "string"}, "description": "Public sites the user likes (up to 8 URLs): each is screenshotted and read for its colours, and the brief sees the pictures. Pass EVERY site the user named, not a selection."},
            "inspiration_images": {"type": "array", "items": {"type": "string"}, "description": "Pictures the user likes, as REFERENCES for the look (up to 8 site file URLs). Not the site's own photographs: those go in `photos`."},
            "photos": {"type": "array", "items": {"type": "string"}, "description": "The client's OWN photographs, to be placed in the pages (site file URLs, up to 40). Each is read for what it shows, its shape and its quality, then laid into the matching image slots; only the slots no photo fits are drawn. Send everything the client supplied."},
            # //// Neoffice — the categories travel as their own list: summarised into the activity
            # //// by the model, "five segments: Snow, Street, Water, Outdoor, Home" was lost, and the
            # //// home's category wall came out with two repeated photographs and no name (2026-09-12)
            "categories": {"type": "array", "items": {"type": "string"}, "description": "The categories, segments or collections the site is organised in, in the user's own words (an image-led home gives each one a photo tile). Pass every one the user named."},
            "palette_mode": {"type": "string", "enum": ["auto", "monochrome"], "description": "'monochrome' when the client wants NO colour: black, white and greys only, the photographs carrying the page. Default 'auto', which also turns monochrome by itself when every inspiration site read has no colour."},
            "copy_density": {"type": "string", "enum": ["auto", "standard", "minimal"], "description": "'minimal' when the photographs must carry the site and the copy step back: headlines of a few words, a line at most under each, no paragraphs. Default 'auto', which turns minimal by itself when the brief or the chosen direction asks for little text ('less is more', 'through the image')."},
            "website_profile": {"type": "string", "description": "The Website Profile (site) to build for; the open page's profile when omitted."},
            # //// Neoffice — the language is required: the recap step listed every field but this
            # //// one, and the default filled in (the instance's, else French) wrote a site asked
            # //// for in English in French (2026-09-11).
            "language": {"type": "string", "description": "The language the site is WRITTEN in (ISO code or name): the one the user asked for, else the language of their messages. Always pass it: the instance default is only a guess."},
            # //// Neoffice — keep_edited: "keep them" after a CONFIRM_NEEDED meant keeping the
            # //// hand-made pages, and 'none' kept the whole previous site beside the new one.
            "replace_existing": {
                "type": "string",
                "enum": ["auto", "force", "keep_edited", "none"],
                "description": "What to do with the site's existing pages: auto (replace untouched AI pages, ask before touching hand-made ones), force (replace all), keep_edited (keep the hand-made pages, replace the untouched AI pages: the answer 'keep them' to a CONFIRM_NEEDED), none (keep every existing page and add the new ones beside, only when the user asks for exactly that).",
            },
        },
        "required": ["site_name", "activity", "pages", "language"],
    },
)

# The site chrome (header, menu, footer, CTA, logo text, social links, opening hours) is
# the theme's, rendered around every page from Website Header Footer Config / Variant.
# These two tools let the assistant read and change it by dialogue, per profile.
CHROME_READ_FIELDS = (
    "header_layout", "header_style", "sticky_header", "header_height", "logo_type", "logo_text", "show_cta", "cta_text",
    "cta_url", "cta_style", "search_type", "show_user", "show_wishlist", "show_cart", "footer_template",
    "footer_menu_source", "footer_description", "copyright_text", "show_social_links", "facebook_url", "instagram_url",
    "linkedin_url", "youtube_url", "twitter_url", "show_newsletter", "newsletter_title", "show_opening_hours",
    "opening_hours_display", "show_breadcrumbs", "page_header_template", "menu_items", "footer_links",
)


def chrome_payload(settings: dict) -> dict:
    """What update_site_chrome accepts: the readable fields only, menu and footer rows as
    lists of {label, url}; anything else the model invents is dropped."""
    from builder.hf_utils.chrome_api import SIMPLE_FIELDS

    allowed = set(SIMPLE_FIELDS) | {"menu_items", "footer_links"}
    out = {}
    for key, value in (settings or {}).items():
        if key not in allowed:
            continue
        if key in ("menu_items", "footer_links"):
            rows = []
            for row in value or []:
                if isinstance(row, dict) and (row.get("label") or "").strip() and (row.get("url") or "").strip():
                    rows.append({k: row.get(k) for k in ("label", "url", "open_in_new_tab", "column_name") if row.get(k) is not None})
            out[key] = rows
        else:
            out[key] = value
    return out


def run_get_site_chrome(ctx, args: dict) -> str:
    import json

    from builder.hf_utils.chrome_api import get_chrome_settings
    from builder.site_ai.nora.prompts import page_profile
    from builder.site_ai.nora.site_builder import PAGE_INCLUDES, available_includes

    profile = page_profile(ctx.page_id) or None
    settings = get_chrome_settings(profile)
    chrome = {k: settings.get(k) for k in CHROME_READ_FIELDS if k in settings}
    site_name = settings.get("logo_text") or ""
    includes = {}
    for page_type in PAGE_INCLUDES:
        offered = available_includes(page_type, "ecommerce" if page_type in ("accueil", "shop") else "vitrine", profile, site_name)
        if offered:
            includes[page_type] = [{"include": tag, "purpose": purpose} for tag, purpose in offered]
    return json.dumps({"profile": profile or "main site", "chrome": chrome, "options": settings.get("_options", {}), "page_includes": includes}, ensure_ascii=False)


def run_update_site_chrome(ctx, args: dict) -> str:
    from builder.hf_utils.chrome_api import update_chrome_settings
    from builder.site_ai.nora.prompts import page_profile

    payload = chrome_payload((args or {}).get("settings") or {})
    if not payload:
        return "FAILED: nothing to change (only the fields listed by get_site_chrome are accepted)."
    profile = page_profile(ctx.page_id) or None
    try:
        update_chrome_settings(payload, profile)
    except Exception as e:
        frappe.log_error("update_site_chrome failed", frappe.get_traceback())
        return f"FAILED: {str(e)[:200]}"
    frappe.db.commit()
    try:
        ctx.emit("refetch", resources=["canvas"], after_commit=False)
    except Exception:
        pass
    return "DONE: " + ", ".join(sorted(payload)) + " updated on " + (f"profile '{profile}'" if profile else "the main site") + "; the header and footer of every page follow."


get_site_chrome = Tool(
    name="get_site_chrome",
    side="server",
    handler=run_get_site_chrome,
    description=(
        "Read the site chrome of the open page's site: header layout and style, logo text, CTA button, search/user/"
        "wishlist/cart toggles, menu items, footer template, description, links, social links, newsletter, the "
        "opening-hours block, plus the shortcodes (Jinja includes) a page may embed, by page type. Call it before "
        "update_site_chrome, and whenever the user asks what the header, menu or footer contains."
    ),
    parameters={"type": "object", "properties": {}},
)

update_site_chrome = Tool(
    name="update_site_chrome",
    side="server",
    handler=run_update_site_chrome,
    description=(
        "Change the site chrome of the open page's site: pass ONLY the fields to change, with the names and option "
        "values get_site_chrome returned (menu_items and footer_links are full lists of {label, url}; the opening "
        "hours block is show_opening_hours 0/1 with opening_hours_display). The header and the footer of every page "
        "follow at once. Never build a header, menu or footer inside a page instead."
    ),
    parameters={
        "type": "object",
        "properties": {
            "settings": {
                "type": "object",
                "description": "The chrome fields to change, e.g. {\"cta_text\": \"Devis gratuit\", \"cta_url\": \"/contact\", \"show_opening_hours\": 1, \"menu_items\": [{\"label\": \"Accueil\", \"url\": \"/\"}]}.",
                "additionalProperties": True,
            }
        },
        "required": ["settings"],
    },
)

def run_inspect_inspiration(ctx, args: dict) -> str:
    from builder.site_ai.nora.inspiration import clean_list, describe, gather
    from builder.site_ai.nora.site_builder import _page_model

    urls, images = clean_list((args or {}).get("urls")), clean_list((args or {}).get("images"))
    if not urls and not images:
        return "FAILED: give at least one public URL or one site file URL (/files/...)."
    try:
        found = gather(urls, images)
    except Exception as e:
        frappe.log_error("inspect_inspiration failed", frappe.get_traceback())
        return f"FAILED: the inspirations could not be read: {str(e)[:200]}"
    try:
        model = _page_model(ctx)
    except Exception:
        model = None
    return describe(found, model=model)


inspect_inspiration = Tool(
    name="inspect_inspiration",
    side="server",
    handler=run_inspect_inspiration,
    description=(
        "Look at the sites and pictures the user likes: each URL is screenshotted, each picture read for its "
        "dominant colours, and the vision model describes their palette, typography and layout. Call it when the "
        "user shares a link or an image as something they like (in the playbook or in a free conversation), "
        "then keep the same URLs and file paths for generate_site (inspiration_urls, inspiration_images)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "urls": {"type": "array", "items": {"type": "string"}, "description": "Public http(s) URLs of sites the user likes, up to 3."},
            "images": {"type": "array", "items": {"type": "string"}, "description": "Site file URLs (/files/... or /private/files/...) of pictures the user likes, up to 3."},
        },
    },
)


TOOLS = [generate_site, inspect_inspiration, get_site_chrome, update_site_chrome]
