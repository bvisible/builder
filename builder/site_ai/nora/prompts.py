"""The site-creation playbook appended to the agent's system prompt.

Upstream's agent builds ONE page. On a Neoffice instance the same agent also
creates whole sites: it collects the brief with present_ui cards, then calls
generate_site, which runs the site pipeline (brief, tokens, chrome, pages on
upstream's page engine, menu, images). The playbook is English like every
other prompt; the agent answers in the user's language.
"""

from __future__ import annotations

import frappe

DEFAULT_PAGE_TITLES = ["Accueil", "À propos", "Services", "Contact"]
OPTIONAL_PAGE_TITLES = ["FAQ", "Équipe", "Blog", "Témoignages", "Boutique", "Tarifs", "Projets"]


def site_state_line(page_id: str | None) -> str:
    profile = page_profile(page_id)
    filters = {"is_template": 0, "published": 1}
    if frappe.db.has_column("Builder Page", "neo_website_profile"):
        filters["neo_website_profile"] = profile if profile else ("is", "not set")
    count = frappe.db.count("Builder Page", filters)
    where = f" on site profile '{profile}'" if profile else ""
    return f"This site{where} currently has {count} published page(s)." if count else f"This site{where} has NO pages yet."


def page_profile(page_id: str | None) -> str | None:
    if not page_id or not frappe.db.has_column("Builder Page", "neo_website_profile"):
        return None
    return frappe.db.get_value("Builder Page", page_id, "neo_website_profile") or None


def profiles_line() -> str:
    if not frappe.db.exists("DocType", "Website Profile"):
        return ""
    rows = frappe.get_all("Website Profile", fields=["name", "primary_domain", "is_default"], order_by="is_default desc")
    if len(rows) < 2:
        return ""
    listing = "; ".join(f"'{r.name}' ({r.primary_domain}{', default' if r.is_default else ''})" for r in rows)
    return (
        f"This instance serves SEVERAL sites: {listing}. A page belongs to one of them (the open page's site "
        "profile is what you edit). Before building a site, confirm which profile it is for (a 'choices' card) "
        "unless the open page already belongs to the intended one, and pass it as website_profile."
    )


def site_playbook(page_id: str | None = None) -> str:
    return f"""

# Building a WHOLE site (Neoffice)
{site_state_line(page_id)} This Studio creates complete sites, not only one page. Run this playbook when the user asks for a new site, wants the whole site redone, or the site has no pages yet. Skip any step whose answer you already have (the first message often carries the name and the activity), never re-ask, and answer in the user's language.
EVERY step below is ONE CALL of the present_ui TOOL (a function call with `text` and `ui`). Writing the card as text, with brackets like [choices: ...] or [buttons: ...], is a FAILURE: the user cannot tap text. If you are about to type option lists or "[buttons: Continue]" into your message, STOP and call present_ui instead. Your message text stays one short sentence; the card carries the options.
1. The business. present_ui with ui=[{{kind:'input', label:'Name'}}, {{kind:'input', label:'Activity'}}, {{kind:'input', label:'What makes you different'}}, {{kind:'actions', buttons:[{{label:'Continue'}}]}}].
2. The pages. present_ui with ONE multi-select choices group: ui=[{{kind:'choices', label:'Pages', multi:true, options:[{{label:'Accueil'}}, {{label:'À propos'}}, {{label:'Services'}}, {{label:'Contact'}}, {{label:'FAQ'}}, {{label:'Équipe'}}, {{label:'Blog'}}, {{label:'Témoignages'}}, {{label:'Réalisations'}}, {{label:'Tarifs'}}]}}, {{kind:'actions', buttons:[{{label:'Continue'}}]}}] (translate the labels to the user's language, add a one-line description to each, keep Accueil and Contact unless told otherwise). Free text adds a page.
3. Colours and style. present_ui with THREE groups in one card: a choices group 'Palette' whose 3 options each carry `colors` (primary, secondary, background hex you propose for this activity), a color_input with two slots (Primary, Secondary) for their own colours, and a choices group 'Layout direction' with 3 options and one-line descriptions (for example an editorial grid, a bold poster, a clean classic layout); then an actions button.
4. The logo. present_ui with ui=[{{kind:'upload', label:'Logo'}}, {{kind:'actions', buttons:[{{label:'Continue'}}, {{label:'Skip', variant:'secondary'}}]}}]. {profiles_line()}
5. The recap. present_ui with a heading, a list (name, pages, colours, direction, logo) and actions "Build the site" / "Change something". On approval call generate_site with everything collected (site_name, activity, differentiators, pages, primary_color, secondary_color, style_direction, logo_image, website_profile). The tool writes the pages, the header and footer, the menu, and starts the images; it takes several minutes and reports progress. If it answers CONFIRM_NEEDED, present the question it carries as a confirm card and call it again with the user's choice. When it succeeds, summarise what now exists (pages and routes) in two or three sentences and say the dashboard lists the pages. Never use generate_page to create a site.

# Site rules (Neoffice)
- The header, the navigation and the footer are the site chrome, rendered around every page by the theme from the site's settings: NEVER build a header, nav or footer section inside a page, with generate_page or the block tools. To change them, tell the user they live under Settings > Theme.
- Pages belong to a site profile; work on the open page's profile only.
- The site's colours and fonts are Builder Tokens named after the site (var(--<prefix>-primary), var(--<prefix>-font-heading), ...); reuse the handles you see in the open page instead of inventing new ones.
"""
