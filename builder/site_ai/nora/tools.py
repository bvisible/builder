"""The generate_site tool: our site pipeline, callable by the editor agent."""

from __future__ import annotations

import frappe

from builder.ai.agent.registry import Tool

SITE_TYPES = ["vitrine", "one_page", "blog", "ecommerce", "saas", "portfolio"]


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
            "site_type": {"type": "string", "enum": SITE_TYPES, "description": "Kind of site; vitrine (showcase) by default."},
            "primary_color": {"type": "string", "description": "Hex colour chosen by the user, or the primary of the palette they picked."},
            "secondary_color": {"type": "string", "description": "Hex colour, optional."},
            "style_direction": {"type": "string", "description": "The layout direction the user picked, in a few words (e.g. 'editorial grid, calm', 'bold poster')."},
            "logo_image": {"type": "string", "description": "Site file URL of the uploaded logo (/files/...), if any."},
            "website_profile": {"type": "string", "description": "The Website Profile (site) to build for; the open page's profile when omitted."},
            "language": {"type": "string", "description": "Language of the site copy (ISO code or name); the site default when omitted."},
            "replace_existing": {
                "type": "string",
                "enum": ["auto", "force", "none"],
                "description": "What to do with the site's existing pages: auto (replace untouched AI pages, ask before touching hand-made ones), force (replace all), none (keep everything, add the new pages).",
            },
        },
        "required": ["site_name", "activity", "pages"],
    },
)

TOOLS = [generate_site]
