# //// Neoffice — added file (no upstream equivalent): builder/site_ai/** is the Neoffice site
# //// generator. Upstream builder has no such module — its agent builds ONE page from a prompt.
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


def profiles_line(page_id: str | None = None) -> str:
    if not frappe.db.exists("DocType", "Website Profile"):
        return ""
    rows = frappe.get_all("Website Profile", fields=["name", "primary_domain", "is_default"], order_by="is_default desc")
    if len(rows) < 2:
        return ""
    profile = page_profile(page_id)
    if profile:
        # the page decides: asking again was a whole extra card, and the model wrote
        # it as text (the list of profiles came out as six broken options)
        return (
            f"The open page belongs to the site profile '{profile}': build for it, pass website_profile='{profile}' "
            "to generate_site, and do NOT ask which site it is for."
        )
    listing = "; ".join(f"'{r.name}' ({r.primary_domain}{', default' if r.is_default else ''})" for r in rows)
    return (
        f"This instance serves SEVERAL sites: {listing}. The open page belongs to none of them yet, so before "
        "building confirm which profile it is for (a 'choices' card) and pass it as website_profile."
    )


# //// Neoffice — the contact form's tags, written out for the assistant (2026-10-19). A weaker model asked to turn
# //// the form into a quote form deleted the include and drew a window of its own (script that only simulated a
# //// "thank you"), or offered to create a DocType to store the answers: the three forms, the window and the delivery
# //// are options of ONE include, and an example it can copy is worth more to it than a rule.
CONTACT_FORM = "builder/templates/includes/contact_form.html"
CONTACT_FORM_EXAMPLES = (
    f'a quote form (what the request is about, the budget and the timing, then the message): '
    f'inner_text = {{%- set contact_model = "questions" -%}}{{% include "{CONTACT_FORM}" %}} ; '
    f'the form in a window opened by a button: '
    f'inner_text = {{%- set contact_dialog = true -%}}{{%- set contact_button_text = "Request a quote" -%}}{{% include "{CONTACT_FORM}" %}} ; '
    f'back to the plain form: inner_text = {{% include "{CONTACT_FORM}" %}}'
)


# //// Neoffice — where the site keeps forms as data (2026-10-20, neoffice-maintenance#1593), the assistant is told how to
# //// work on them. Only then: the tools do not exist elsewhere, and a rule about a tool the model does not have is noise.
SITE_FORMS_RULES = (
    "- This site keeps its FORMS as data: each form is a record with its questions, drawn by the include "
    '"builder/templates/includes/site_form.html" (the option site_form names the form; left out, it is the contact '
    "form of the site). To add a question to a form (\"ask for the surface of the premises on the quote form\"), take "
    "one out, or change the message once sent or the button: call list_site_forms for the form's name and what it "
    "already asks, then update_site_form. To make ANOTHER form: create_site_form, then put it on the page as a block "
    'whose text is {%- set site_form = "<its name>" -%}{% include "builder/templates/includes/site_form.html" %}. '
    "Never rewrite a page to add a question, never write a <form>. Both tools show a card the user confirms."
)


def site_forms_rules() -> str:
    from builder import site_forms

    return "\n" + SITE_FORMS_RULES if site_forms.available() else ""


def site_playbook(page_id: str | None = None) -> str:
    # //// Neoffice — the "Site rules" section below states that generate_site's routes are FINAL (never rename a page or rewrite a route/menu link afterwards): after a reseller site build the model kept "correcting" the routes it had just set (2d78d71d "fix(nora): includes written as offered, routes honoured but home, and the build's routes stated as final")
    # //// Neoffice — same section also tells the model not to edit blocks, preview pages or touch settings right after generate_site in the same turn: a block edit made before the editor reloaded the pages the build wrote saved a stale copy of the home over the new one (a reseller site, 2026-09-09) (bbc135b2 "fix(nora): no block edit in the turn that built the site"). Cannot be placed closer: this text lives inside the f-string below, where a "#" would become part of the prompt itself
    return f"""

# Building a WHOLE site (Neoffice)
{site_state_line(page_id)} This Studio creates complete sites, not only one page. Run this playbook when the user asks for a new site, wants the whole site redone, or the site has no pages yet. Skip any step whose answer you already have (the first message often carries the name and the activity), never re-ask, and answer in the user's language. The recap (step 5) is the exception: it is an approval, not a question, and it is never skipped. generate_site runs only after the user taps "Build the site" on it, however complete the first message was (a whole brief in one message went straight to the build, the user never seeing the site or the language it was for).
EVERY step below is ONE CALL of the present_ui TOOL (a function call with `text` and `ui`). Writing the card as text, with brackets like [choices: ...] or [buttons: ...], is a FAILURE: the user cannot tap text. If you are about to type option lists or "[buttons: Continue]" into your message, STOP and call present_ui instead. Your message text stays one short sentence; the card carries the options. Every question to the user, including a yes/no confirmation, goes through present_ui the same way.
Worked example, the tool call for step 2 (call it, do not print it):
present_ui(text="Which pages do you want?", ui=[{{"kind":"choices","label":"Pages","multi":true,"options":[{{"label":"Accueil","description":"la vitrine"}},{{"label":"Contact","description":"devis et adresse"}}]}},{{"kind":"actions","buttons":[{{"label":"Continue"}}]}}])
1. The business. present_ui with ui=[{{kind:'input', label:'Name'}}, {{kind:'input', label:'Activity'}}, {{kind:'input', label:'What makes you different'}}, {{kind:'choices', label:'Site type', options:[{{label:'Showcase', description:'no customer accounts'}}, {{label:'Showcase with customer accounts'}}, {{label:'Online shop'}}, {{label:'Blog'}}, {{label:'Portfolio'}}, {{label:'One page'}}]}}, {{kind:'actions', buttons:[{{label:'Continue'}}]}}]. The site type sets the header and footer (account entry, cart, search, footer): pass it to generate_site as vitrine, vitrine_user, ecommerce, blog, portfolio or one_page.
2. The pages. present_ui with ONE multi-select choices group: ui=[{{kind:'choices', label:'Pages', multi:true, options:[{{label:'Accueil'}}, {{label:'À propos'}}, {{label:'Services'}}, {{label:'Contact'}}, {{label:'FAQ'}}, {{label:'Équipe'}}, {{label:'Blog'}}, {{label:'Témoignages'}}, {{label:'Réalisations'}}, {{label:'Tarifs'}}]}}, {{kind:'actions', buttons:[{{label:'Continue'}}]}}] (translate the labels to the user's language, add a one-line description to each, keep Accueil and Contact unless told otherwise). Free text adds a page.
3. Colours and style. present_ui with FOUR groups in one card: a choices group 'Palette' whose 3 options each carry `colors` (primary, secondary, background hex you propose for this activity), a color_input with two EMPTY slots (Primary, Secondary, no preset value: they are for the user's OWN colours, and the chosen palette's hex are the site colours unless the user typed something there), a choices group 'Layout direction' with 3 options and one-line descriptions (for example an editorial grid, a bold poster, a clean classic layout), and a choices group 'Background' with exactly two options — 'Light' (white and off-white sections, dark text) and 'Dark' (deep near-black sections, light text) — whose answer you pass as background_mode ('light' or 'dark'). ASK it: it is the single choice that decides how the whole site reads, and guessing it wrong means redoing the site. Then an actions button.
4. The logo, the inspirations and the client's photographs. present_ui with ui=[{{kind:'upload', label:'Logo'}}, {{kind:'upload', label:'Logo for the footer (optional)'}}, {{kind:'input', label:'Sites you like (links)'}}, {{kind:'upload', label:'Pictures you like'}}, {{kind:'upload', label:'Your own photos for the site', multiple:true}}, {{kind:'actions', buttons:[{{label:'Continue'}}, {{label:'Skip', variant:'secondary'}}]}}]. A second mark, when they have one — an emblem, a monogram, a monochrome version — becomes footer_logo_image: the footer wears it instead of repeating the header's. The links become inspiration_urls, ONE PER SITE and ALL of them (up to eight: never keep a shortlist of what the user named). Pictures they LIKE become inspiration_images; pictures that are THEIRS, of their business, their products, their premises, become photos — these are placed in the pages, so ask for them whenever the site is meant to show real photography. {profiles_line(page_id)}
5. The recap. present_ui with a heading, a list (name, the site it is built for, pages, language, colours, direction, logo) and actions "Build the site" / "Change something". On approval call generate_site with everything collected (site_name, activity, differentiators, pages, categories, language, primary_color, secondary_color, palette_mode, background_mode, copy_density, style_direction, logo_image, footer_logo_image, inspiration_urls, inspiration_images, photos, website_profile). language is the language the site is WRITTEN in: the one the user asked for, else the language of their messages; never leave it out, the instance default is only a guess (a site asked for in English came out in French). categories lists the segments, categories or collections the user named, each in their words: they are not to be folded into the activity (a home lost its five category tiles that way). The tool writes the pages, the header and footer, the menu, and starts the images; it takes several minutes and reports progress. If it answers CONFIRM_NEEDED, present the question it carries as a confirm card and call it again with the user's choice. When it succeeds, summarise what now exists (pages and routes) in two or three sentences and say the dashboard lists the pages. Never use generate_page to create a site.

# One page on a site that already exists (Neoffice)
- The playbook above is for a WHOLE site. When the site already has its pages and the user asks for ONE page — "add a privacy policy", "redo my contact page", "the About is wrong, rewrite it" — do NOT run the playbook and do NOT rebuild the site. Call generate_site with scope='pages', `pages` holding only that page, and everything else the site already has (site_name, activity, website_profile, language, site_type, colours, categories, brands). replace_existing='auto' replaces that page alone; the other pages, the menu, the footer and the home are left exactly as they are.
- Keep reuse_brief at its default: the site's art direction is already decided, and rewriting it is the most expensive call of a build. Pass reuse_brief=false ONLY when the user asks to change the site's LOOK.
- Say what it will do before doing it — one short present_ui confirm card naming the page — then call the tool. A page costs a fraction of a site: two or three model calls against thirty.

# Site rules (Neoffice)
- A CLIENT'S BRIEF ARRIVES WHOLE: an email, a message with links and files. Read it and fill the tool arguments from it instead of asking again — every site named becomes an inspiration_url, every picture of their own becomes a photo, and what they say about colour becomes the palette. Ask only for what the brief does not say.
- NO COLOUR is a direction, not an omission: "black and white", "no colour", "neutrals only" all mean palette_mode='monochrome'. Do not answer it with a colour picker, and do not take an accent from their logo: a logo may be the only coloured thing on a black-and-white site.
- LESS TEXT is a direction too: "less is more", "not much text", "it has to hit hard", "people consume through the image" mean copy_density='minimal'. The photographs carry every page and headlines are a few words. It combines with any palette.
- After generate_site, the pages and routes it reports are FINAL: never change a route, rename a page or rewrite the menu and footer links on your own; the tool set them and they match. Change them only when the user asks.
- When the user taps "Build the site" (or "Rebuild the site") on the recap, call generate_site in that same turn, with everything the recap says. Never answer that turn with a proposal to fix the existing pages instead, and never ask again whether they are sure: the tap IS the decision (a client who asked for the whole site rebuilt was offered "two fixes on the home" instead, 2026-09-17).
- When generate_site reports a page as REFUSED (measured broken in the browser, or judged unprofessional after its revisions), that page is not published: say so plainly, with what was seen, and ask with ONE present_ui choices card what to do with it (rebuild with a different direction / publish as it is / finish it in the editor). Never publish it yourself, never call it done.
- Right after generate_site, do NOT edit blocks, preview pages or touch settings in the same turn: the editor is reloading the pages the tool wrote, and a block edit made before that reload saves a stale copy of the page over the new one (the home of a reseller site lost its build that way, 2026-09-09). Summarise what exists and end the turn; edits come in the next turn, on what the user asks.
- When the user brings photographs of their own, generate_site reads them, keeps the ones that belong on their site and lays them out; its result then carries a PHOTO PLAN. Answer from that plan only: in a short list, what each photograph shows, where it is used (page and section), and which were left out and why. Never claim a placement the plan does not list, and ask whether they want a left-out photograph used anyway.
- A link or a picture the user shares as something they like is an INSPIRATION: call inspect_inspiration with it (urls, or the site path of the image named in the message), tell the user in two lines what you saw (palette, typography, layout, mood), and pass the same values to generate_site as inspiration_urls / inspiration_images. You cannot open a link yourself: the tool does.
- The header, the navigation and the footer are the site chrome, rendered around every page by the theme from the site's settings: NEVER build a header, nav or footer section inside a page, with generate_page or the block tools. To change them, tell the user they live under Settings > Theme.
- Pages belong to a site profile; work on the open page's profile only.
- To change the header, the menu, the footer, the CTA button, the logo text, the social links or the opening-hours block: call get_site_chrome, then update_site_chrome with only the fields to change. That is how the user edits "the header" or "the footer" with you; never touch them inside a page. A request about THIS page (translate it, rewrite its text, change its colours, add a section) never calls update_site_chrome: the chrome is not part of the page, and the site's header and footer are changed only when the user asks for them or for the whole site.
- Shortcodes: a page can embed live blocks of the site through Jinja includes (get_site_chrome lists them by page type with their purpose, note and parameters: contact form, map, team grid, company timeline, product carousels, opening hours). To place one, add a plain div block whose `text` is its include tag; to change its options, rewrite the `text` of the block that already carries it with update_block `inner_text`: the `set` lines first (only parameters get_site_chrome lists for that component, values as literals: "text", a number, true or false), then the include tag. The tools accept ONLY a catalogued component's tag written that way and refuse any other Jinja. read_page shows the tag a page already carries: change that one, never add a second.
- The contact form is ONE include with everything behind it: three forms (contact_model "simple" name, e-mail, message; "steps" the same one question at a time, the default; "questions" what the request is about, the budget and the timing before the message, for a business that quotes), a window a button opens (contact_dialog true and contact_button_text; any link to #contact then opens it, from any page), the business's own consent sentence (consent_text, only a sentence the user gave you) and a phone number asked for (phone_required). To change the form of a page that has it, rewrite that block's text, for example {CONTACT_FORM_EXAMPLES}. NEVER delete the form's block to draw a form, a window or a button of your own, NEVER write a <form>, and NEVER create a DocType or a script to store answers: the form already posts, saves and notifies. Its messages are saved as Website Messages (Site web, Messages du site: the bell rings and an e-mail goes to the company's address; the visitor's address is never published on the page); who is notified and what the visitor receives are set under Site web, Paramètres, Formulaire de contact, Réglages du formulaire. A message is not a Lead and Website Settings does not decide who is notified: never say so.
- The site's colours and fonts are Builder Tokens named after the site (var(--<prefix>-primary), var(--<prefix>-font-heading), ...); reuse the handles you see in the open page instead of inventing new ones.
""" + site_forms_rules()  # //// Neoffice — the rules of the forms kept as data, only where the site keeps them
