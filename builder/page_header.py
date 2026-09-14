# //// Neoffice — added file (no upstream equivalent): the shared band at the top of pages the editor
# //// does not build (blog index, 404, listings). builder/templates/includes/header_footer/** = the
# //// Neoffice site chrome (Website Header Footer Config). First commit b7271612 2026-08-04.
"""The band at the top of pages the editor does not build.

A generated page opens on a hero the AI composed for it. Every other page —
the blog index, a category listing, the 404, a section that is coming — arrived
with whatever heading its own app happened to print. That is why /blog read as
a different website: no breadcrumb, a bare `<h1>` in someone else's markup, and
none of the site's rhythm.

This is the third piece of the site chrome, beside the header and the footer:
one band, decided once in the Theme, rendered above the content of every page
Builder does not own.

It deliberately skips article pages. Those open on a cover hero that already
carries the title and the category — a page header there would be a title above
a title.
"""

import json
# //// Neoffice — re: the colour allowlist added below (_COLOUR_RE).
import re

import frappe
from frappe import _
# //// Neoffice — escape_html: frappe's Jinja has no autoescape and this band is
# //// rendered through `| safe`, so the title and subtitle printed raw markup.
from frappe.utils import escape_html

# The band is a preset plus a fill — the same shape as the header and the
# footer, and for the same reason.
#
# It used to be one enum: None / Simple / Centered / Tinted. "Centered" is a
# composition and "Tinted" is a background, so mixing them in one field made
# half the combinations unsayable — there was no way to ask for a centred title
# over a photograph. And letting the model invent a band per site would repeat
# the mistake the interior pages already made.
#
# So: WE design the presets, the AI picks one and picks a fill. `footer_template`
# works exactly this way.
# //// Neoffice — "Builder": the band is a component the site designs in the Builder (2026-09-14)
TEMPLATES = ("Minimal", "Standard", "Centered", "Split", "None", "Builder")
BACKGROUNDS = ("None", "Tinted", "Solid", "Image")

DEFAULTS = {
	"page_header_template": "Standard",
	"page_header_background": "None",
	"page_header_bg_color": "",     # empty: Tinted washes the primary colour
	"page_header_image": "",
	"page_header_excluded_routes": "",
	"show_breadcrumbs": 1,
	"page_header_component": "",
}

# Fills that put the title over something dark enough to need light text.
_DARK_BACKGROUNDS = ("Image", "Solid")

# The band carries its own CSS, the way the header and the footer do.
#
# `web_include_css` only reaches pages frappe renders. A Builder page loads its
# own assets, so a stylesheet rule for the band would style it on the blog and
# leave it unstyled — breadcrumbs flush against the window edge — on every page
# the AI generated. Shipping the rules with the markup is what makes one band
# actually mean one band.
#
# On a Builder page the title and the text take the page's own faces when it has some
# (--sph-*, see _page_fonts): the theme's fonts are the fallback, not the rule.
#
# //// Neoffice — the inner column sits on the site grid with the header and the footer
# //// (theme_variables.html, --container-*), at their thresholds: 24px then 16px without the grid tokens.
_CSS = (
	"<style>.site-page-header{border-bottom:1px solid var(--footer-border,rgba(0,0,0,0.08))}.site-page-header__inner{max-width:var(--container-width,1280px);margin:0 auto;padding:44px var(--container-padding,24px) 36px;font-family:var(--sph-body-font,inherit)}.site-page-header__crumbs{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:0.8125rem;color:var(--text-muted,var(--muted-color,#6b7280));margin-bottom:12px}.site-page-header__crumbs a{color:inherit;text-decoration:none}.site-page-header__crumbs a:hover{color:var(--primary-color,#111)}.site-page-header__sep{opacity:0.5}.site-page-header__title{font-size:clamp(1.9rem,1.2rem + 2.2vw,3rem);font-weight:var(--sph-heading-weight,700);font-family:var(--sph-heading-font,var(--heading-font,inherit));line-height:1.15;margin:0}.site-page-header__subtitle{max-width:62ch;margin:10px 0 0;color:var(--text-muted,var(--muted-color,#6b7280));line-height:1.6}.site-page-header--minimal .site-page-header__inner{padding-top:32px;padding-bottom:24px}.site-page-header--centered .site-page-header__inner{text-align:center}.site-page-header--centered .site-page-header__crumbs{justify-content:center}.site-page-header--centered .site-page-header__subtitle{margin-left:auto;margin-right:auto}.site-page-header__split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:32px;align-items:end}.site-page-header__split .site-page-header__subtitle{margin-top:0}@media (max-width:768px){.site-page-header__split{grid-template-columns:1fr;gap:12px}}.site-page-header--bg-image .site-page-header__inner,.site-page-header--bg-solid .site-page-header__inner{padding-top:72px;padding-bottom:64px}.site-page-header--on-dark{border-bottom-color:transparent}.site-page-header--on-dark .site-page-header__title{color:#fff}.site-page-header--on-dark .site-page-header__subtitle,.site-page-header--on-dark .site-page-header__crumbs{color:rgba(255,255,255,0.82)}.site-page-header--on-dark .site-page-header__crumbs a:hover{color:#fff}.site-page-header--bg-tinted{border-bottom-color:transparent}.site-page-header--crumbs .site-page-header__inner{padding-top:14px;padding-bottom:14px}.site-page-header--crumbs .site-page-header__crumbs{margin-bottom:0}@media (max-width:768px){.site-page-header .site-page-header__inner{padding-left:var(--container-padding-tablet,16px);padding-right:var(--container-padding-tablet,16px)}}@media (max-width:576px){.site-page-header .site-page-header__inner{padding-left:var(--container-padding-phone,16px);padding-right:var(--container-padding-phone,16px)}}</style>"
)


# Pages that carry their own opening and must not get a second one.
#
# This is the DEFAULT, not the law: the list lives in a setting so an owner can
# add a route without touching the code. It mattered the day the shop arrives —
# a product page opens on its gallery, a cart is not an editorial page — but
# also for any one-off landing page a client wants bare.
SKIP_PATHS = ("", "home", "index")

# //// Neoffice — a home never gets the band, whatever its route. The band told a home by
# //// SKIP_PATHS alone: a home the generator wrote beside an existing one gets a hashed route
# //// ("home-c98e", site_builder), the menu of a test site linked it as its "Accueil", and the
# //// page opened on a band that said "Accueil" above its own hero (2026-09-13).
HOME_ROUTE = re.compile(r"^(?:home|index)(?:-[0-9a-f]{4})?$")


def _is_home(route: str) -> bool:
	"""Whether a page is a home: served at the site's root, the home of the resolved site
	profile or of the site's settings, or a home the generator wrote beside another one."""
	route = (route or "").strip("/")
	if not route or HOME_ROUTE.match(route):
		return True
	try:
		path = getattr(getattr(frappe.local, "request", None), "path", None)
		if isinstance(path, str) and not path.strip("/"):
			return True
		profile = getattr(frappe.local, "website_profile_doc", None)
		homes = {
			profile.get("home_route") if profile is not None and hasattr(profile, "get") else None,
			getattr(frappe.local.flags, "home_page", None),
			frappe.get_cached_value("Builder Settings", "Builder Settings", "home_page"),
			frappe.db.get_single_value("Website Settings", "home_page", cache=True),
		}
	except Exception:
		return False
	return route in {str(home).strip("/") for home in homes if home}


def _excluded_routes(config: dict) -> tuple:
	"""Routes that get no band: the setting, or the default when it is empty.

	One route per line, `*` allowed at the end of a pattern.
	"""
	raw = (config.get("page_header_excluded_routes") or "").strip()
	if not raw:
		return SKIP_PATHS
	return tuple(line.strip().strip("/") for line in raw.splitlines() if line.strip())


def _is_excluded(path: str, routes: tuple) -> bool:
	path = (path or "").strip("/")
	for pattern in routes:
		if pattern.endswith("*"):
			if path.startswith(pattern[:-1]):
				return True
		elif path == pattern:
			return True
	return False


def _config():
	try:
		from builder.hf_utils.header_footer import get_header_footer_config

		return get_header_footer_config()
	except Exception:
		return None


def settings() -> dict:
	config = _config()
	if not config:
		return dict(DEFAULTS)
	out = {}
	for field, fallback in DEFAULTS.items():
		value = config.get(field)
		out[field] = fallback if value in (None, "") else value
	return out


# //// Neoffice — the shop's trail (2026-09-14): the band followed frappe's `parents` and read "Home /
# //// Shop by Category / Products / T-Shirt", while the shop's own breadcrumb (webshop
# //// templates/includes/breadcrumbs.html), hidden under the band, reads "Home / Shop / Products /
# //// T-Shirt". On a shop page the band now follows the shop's rules: Home, Shop (/all-products), the
# //// last two parents that are neither the listing nor the categories page, then the page itself.
_SHOP_DOCTYPES = ("Website Item", "Item Group")
_SHOP_ROUTES = ("all-products", "shop-by-category", "cart", "wishlist", "product_search", "checkout")
_SHOP_LISTING_ROUTES = ("", "home", "all-products", "shop-by-category")
_SHOP_LISTING_TITLES = ("Home", "All Products", "Shop", "Shop by Category")


def _is_shop_page(context, path: str) -> bool:
	if getattr(context.get("doc"), "doctype", None) in _SHOP_DOCTYPES:
		return True
	return (path.split("/")[0] if path else "") in _SHOP_ROUTES


def _shop_trail(context, current: str) -> list:
	"""Home, Shop, the last two categories, then the page: the trail of the shop's own breadcrumb."""
	listing = {t.lower() for t in _SHOP_LISTING_TITLES} | {_(t).lower() for t in _SHOP_LISTING_TITLES}
	crumbs = [{"label": _("Home"), "url": "/"}, {"label": _("Shop"), "url": "/all-products"}]
	parents = []
	for parent in context.get("parents") or []:
		label = str(parent.get("label") or parent.get("title") or parent.get("name") or "")
		route = str(parent.get("route") or parent.get("url") or "").strip("/")
		if label and route not in _SHOP_LISTING_ROUTES and label.strip().lower() not in listing:
			parents.append({"label": label, "url": "/" + route})
	crumbs += parents[-2:]
	if current and current.strip().lower() not in listing:
		crumbs.append({"label": current, "url": ""})
	else:
		# the listing itself: the Shop crumb is the page
		crumbs[-1] = {"label": crumbs[-1]["label"], "url": ""}
	deduped = []
	for crumb in crumbs:
		if deduped and deduped[-1]["label"].strip().lower() == crumb["label"].strip().lower():
			deduped[-1] = crumb
			continue
		deduped.append(crumb)
	return deduped


def _breadcrumbs(context, path: str, current: str) -> list:
	"""Home, the trail, then the page itself — each label once.

	Frappe builds `parents` for some pages (the blog does) and it knows the real
	titles, so it wins when present. It also already starts at Home, which is
	why this cannot simply prepend one: /blog was reading "Home / Home / Portal".
	"""
	if _is_shop_page(context, path):
		return _shop_trail(context, current)
	crumbs = []
	parents = context.get("parents") or []

	if parents:
		for parent in parents:
			label = parent.get("label") or parent.get("title") or parent.get("name")
			route = parent.get("route") or parent.get("url") or ""
			if label:
				crumbs.append({"label": str(label), "url": "/" + str(route).lstrip("/")})
	else:
		walked = []
		for segment in [s for s in path.split("/") if s][:-1]:
			walked.append(segment)
			crumbs.append({
				"label": segment.replace("-", " ").replace("_", " ").capitalize(),
				"url": "/" + "/".join(walked),
			})

	home = _("Home")
	if not crumbs or crumbs[0]["label"].strip().lower() not in {home.lower(), "home"}:
		crumbs.insert(0, {"label": home, "url": "/"})

	# the page itself closes the trail, unless the trail already ends on it
	if current and (not crumbs or crumbs[-1]["label"].strip().lower() != current.strip().lower()):
		crumbs.append({"label": current, "url": ""})

	# consecutive duplicates come from apps that repeat the section name
	deduped = []
	for crumb in crumbs:
		if deduped and deduped[-1]["label"].strip().lower() == crumb["label"].strip().lower():
			deduped[-1] = crumb
			continue
		deduped.append(crumb)
	return deduped


def _band_parts(context) -> tuple[str, str]:
	"""(the band, the breadcrumb trail as JSON-LD) for a page; either may be empty.

	The trail is there whenever the page has one. It stays for the search engines when the
	band is switched off, when the trail is not shown, and when the page opens on a title of
	its own (see _opens_with_own_title).
	"""
	config = settings()
	template = config.get("page_header_template") or "Standard"

	# A page may say it opens on its own composition — our 404 is a centred
	# statement, and a band above it would be the same words twice.
	if context.get("show_page_header") is False:
		return "", ""

	path = (getattr(frappe.local, "page_header_route", None) or (frappe.request.path if frappe.request else "")).strip("/")
	if _is_excluded(path, _excluded_routes(config)):
		return "", ""

	# an article opens on its cover; that hero already is the page header
	doc = context.get("doc")
	doctype = getattr(doc, "doctype", None) if doc else None
	if doctype == "Blog Post":
		return "", ""

	title = context.get("page_header_title") or context.get("title") or ""
	if not title:
		return "", ""
	# //// Neoffice — a title frappe hands over untranslated (a generic list's doctype name) is
	# //// translated: /addresses closed its trail on "Address" after "Adresse" (2026-09-14). Only a
	# //// plain title: frappe's _() strips the tags of a message it takes for HTML, and a title with
	# //// markup must reach the escaping below as it was typed.
	if "<" not in str(title):
		title = _(str(title))

	# //// Neoffice — the trail stays in the page whatever is drawn (2026-09-14): switching the
	# //// breadcrumb off, or the whole band, took it out of the markup, and the search engines
	# //// with it.
	trail = _breadcrumbs(context, path, title)
	seo = _breadcrumb_ld(trail)
	if template == "None":
		return "", seo
	# //// Neoffice — a page that opens on its own title keeps a visible trail (2026-09-14): it kept only
	# //// the JSON-LD, and a visitor saw no breadcrumb at all on most generated pages. The trail alone
	# //// is drawn above the page, on the band's grid; a page set to go without the band keeps the
	# //// JSON-LD only.
	if context.get("page_opens_itself"):
		if context.get("page_hides_band") or not config.get("show_breadcrumbs") or len(trail) < 2:
			return "", seo
		return _CSS + frappe.render_template(
			"builder/templates/includes/header_footer/page_header.html",
			{
				"template": "Crumbs",
				"background": "None",
				"fill": "",
				"on_dark": False,
				"fonts": context.get("page_fonts") or "",
				"title": "",
				"subtitle": "",
				"breadcrumbs": [{"label": escape_html(c["label"]), "url": escape_html(c["url"])} for c in trail],
			},
		), seo

	# //// Neoffice — a band designed in the Builder: the component chosen for the site, drawn with
	# //// the page's title, subtitle, trail and picture (render_component_band). Without a component
	# //// yet, the standard preset stands in.
	if template == "Builder":
		designed = render_component_band(
			config.get("page_header_component"),
			{
				"page_title": escape_html(title),
				"page_subtitle": escape_html(context.get("page_header_subtitle") or ""),
				"breadcrumbs": [
					{"label": escape_html(c["label"]), "url": escape_html(c["url"])}
					for c in (trail if config.get("show_breadcrumbs") else [])
				],
				"page_image": escape_html(context.get("page_image") or ""),
			},
		)
		if designed:
			return designed, seo
		template = "Standard"

	background = config.get("page_header_background") or "None"
	# //// Neoffice — escaped here, at the seam, rather than in the template. frappe's Jinja
	# //// environment has NO autoescape, and webpage.html renders this band through `| safe`
	# //// — so `{{ title }}` printed raw markup. The title is a page title (a Blog Post's, a
	# //// Builder Page's) and the subtitle its meta description: both are plain text that
	# //// authors, and on generated sites the LLM, supply. Escaping is done in Python so the
	# //// template stays one composition and cannot forget a field.
	crumbs = trail if config.get("show_breadcrumbs") else []
	return _CSS + frappe.render_template(
		"builder/templates/includes/header_footer/page_header.html",
		{
			"template": template,
			"background": background,
			"fill": _fill(background, config),
			"on_dark": background in _DARK_BACKGROUNDS,
			# custom properties already checked by _page_fonts
			"fonts": context.get("page_fonts") or "",
			# //// Neoffice — escaped (see the marker above `crumbs`).
			"title": escape_html(title),
			"subtitle": escape_html(context.get("page_header_subtitle") or ""),
			"breadcrumbs": [
				{"label": escape_html(c["label"]), "url": escape_html(c["url"])} for c in crumbs
			],
		},
	), seo


def render(context) -> str:
	"""The band with its breadcrumb trail, or an empty string when this page should not have one."""
	band, seo = _band_parts(context)
	return band + seo


# //// Neoffice — colour allowlist. `page_header_bg_color` was interpolated straight into a
# //// style attribute while the Image branch two lines below carefully escaped its URL — so
# //// the one field an editor types by hand (and that a generation writes) was the one that
# //// could close the declaration and open another. A colour is a small, closed language:
# //// state it, and anything else is simply not a colour.
_COLOUR_RE = re.compile(
	r"""^(
		\#[0-9a-fA-F]{3,8}                      # #rgb #rgba #rrggbb #rrggbbaa
		| (rgb|rgba|hsl|hsla)\(\s*[0-9a-zA-Z.,%\s/+-]{1,60}\)   # functional notation
		| var\(--[a-zA-Z0-9_-]{1,60}(\s*,\s*\#[0-9a-fA-F]{3,8})?\)  # token, optional hex fallback
		| [a-zA-Z]{3,20}                        # named colour (currentColor, transparent, …)
	)$""",
	re.VERBOSE,
)


def _colour(value: str) -> str:
	"""`value` if it is a CSS colour we recognise, otherwise an empty string."""
	value = (value or "").strip()
	return value if value and _COLOUR_RE.match(value) else ""


def _fill(background: str, config: dict) -> str:
	"""The `background` declaration for the chosen fill, or an empty string.

	Written here rather than in the template so the image URL is quoted once, in
	Python, instead of being interpolated into a style attribute by hand.
	"""
	# //// Neoffice — was `(config.get(...) or "").strip()`, pasted raw into a style
	# //// attribute. _colour() is the allowlist (see the marker above _COLOUR_RE).
	colour = _colour(config.get("page_header_bg_color"))

	if background == "Solid":
		return f"background-color:{colour};" if colour else ""

	if background == "Tinted":
		wash = colour or "var(--primary-color, #111)"
		return f"background:color-mix(in srgb,{wash} 8%,transparent);"

	if background == "Image":
		image = (config.get("page_header_image") or "").strip()
		if not image:
			return ""
		# the scrim is not decoration: the title is light on top of a photograph
		# nobody chose, and without it the words vanish on a bright sky
		safe = image.replace("\\", "").replace("'", "%27").replace('"', "%22")
		return (
			"background-image:linear-gradient(rgba(0,0,0,0.55),rgba(0,0,0,0.35)),"
			f"url('{safe}');background-size:cover;background-position:center;"
		)

	return ""


# //// Neoffice — whitelist REMOVED (was @frappe.whitelist(allow_guest=True)). hooks.py
# //// exposes this as a Jinja method, and a Jinja method needs no whitelist: the templates
# //// call it in-process. The decorator only added an HTTP door onto a renderer that emits
# //// raw markup, for no caller that exists.
def render_page_header() -> str:
	"""Jinja entry point — the Web Template calls this with the page context.

	Reads `frappe.local.page_header_context`, which `blog_chrome`/`site_chrome`
	stash for it: a Web Template renders in its own scope and cannot see the
	page's context dict.
	"""
	context = getattr(frappe.local, "page_header_context", None)
	if context is None:
		return ""
	# the band alone: frappe hoists the <script> tags of a web template into a <script
	# data-web-template> without their type, so the trail's JSON-LD ran as JavaScript (a
	# SyntaxError on every page) and no search engine read it (2026-09-14). The trail goes into
	# the page's <head> instead: see breadcrumb_ld and site_chrome._inject_config_chrome.
	return _band_parts(context)[0]


def breadcrumb_ld(context) -> str:
	"""The breadcrumb trail of a page frappe renders, as JSON-LD for its <head>."""
	return _band_parts(context)[1]


# //// Neoffice — one trail per page (2026-09-14): site_chrome keeps the page's own breadcrumb out of
# //// the markup when the band draws one (context.no_breadcrumbs, which the shop's and frappe's
# //// breadcrumb includes already honour).
def band_draws_trail(context) -> bool:
	"""Whether the band draws the page's breadcrumb trail, visibly."""
	return 'class="site-page-header__crumbs"' in _band_parts(context)[0]


def band_draws(context) -> dict:
	"""What the band draws on the page: its trail and its title (the page's h1), each True or False.
	site_chrome hands them to the page's own templates (no_breadcrumbs, band_prints_title)."""
	band = _band_parts(context)[0]
	return {
		"trail": 'class="site-page-header__crumbs"' in band,
		# a designed band (template Builder) is the component's own markup: its h1 counts as the title
		"title": 'class="site-page-header__title"' in band or ("site-page-header--builder" in band and "<h1" in band),
	}


# //// Neoffice — the band's subtitle is never a line the page already prints
# //// (neoffice-maintenance#393). A generated page's meta description IS its first paragraph
# //// (builder.api._describe_page takes it so that the band does not echo the headline), so the
# //// band printed that sentence and the page repeated it just below, on every interior page.
# //// The three helpers below serve that check in render_builder_page_header.
_SHORTEST_REPEAT = 25


def _plain(text) -> str:
	"""The words a block shows: tags and Jinja out, entities decoded, spaces collapsed, no case."""
	import html

	clean = re.sub(r"<[^>]+>", " ", str(text or ""))
	clean = re.sub(r"\{%.*?%\}|\{\{.*?\}\}|\{#.*?#\}", " ", clean, flags=re.S)
	clean = html.unescape(clean).replace("\u00a0", " ")
	return re.sub(r"\s+", " ", clean).strip().casefold()


def _page_prints(blocks, line: str) -> bool:
	"""Whether one of `blocks` (the block tree, or its JSON as stored) prints `line`.

	The line may end on the ellipsis builder.api._shorten_for_footer puts on a cut. A
	line of a few words is never called a repeat: it could sit inside any sentence.
	"""
	import json

	wanted = _plain(line).rstrip("…").rstrip()
	if len(wanted) < _SHORTEST_REPEAT:
		return False
	if isinstance(blocks, str):
		try:
			blocks = json.loads(blocks)
		except ValueError:
			return False
	if not isinstance(blocks, list):
		return False

	def prints(node, depth=0) -> bool:
		if depth > 16 or not isinstance(node, dict):
			return False
		text = node.get("innerHTML") or node.get("innerText") or ""
		if text and wanted in _plain(text):
			return True
		return any(prints(child, depth + 1) for child in node.get("children") or [])

	return any(prints(block) for block in blocks)


def _rendered_blocks(doc):
	"""The blocks this request shows: the draft in a preview, the published ones otherwise,
	as BuilderPage.get_context chooses them."""

	def value(name):
		return (doc.get(name) if hasattr(doc, "get") else getattr(doc, name, None)) or ""

	request = getattr(frappe.local, "request", None)
	if getattr(request, "for_preview", None) and value("draft_blocks"):
		return value("draft_blocks")
	return value("blocks")


# //// Neoffice — the page's own opening wins over the band (2026-09-14). A generated interior page
# //// may open on a section of its own that carries its h1, a page top composed in the site's style.
# //// The band then drew a second title above it, in the theme's faces: a services page showed
# //// "Services" in one serif, then "Our services" in another, two h1 in a row. The page's first
# //// section decides. With an h1 there, the page brings its own top and the band steps aside,
# //// leaving the breadcrumb trail as JSON-LD; without one, the band carries the title.
_INVISIBLE = {"script", "style", "link", "meta", "template"}


def _page_tree(blocks) -> list:
	"""The block tree, parsed from its stored JSON when needed; empty when it cannot be read."""
	if isinstance(blocks, str):
		try:
			blocks = json.loads(blocks or "[]")
		except ValueError:
			return []
	return blocks if isinstance(blocks, list) else []


def _first_section(blocks):
	"""The first section a visitor sees: the first shown child of the body block Builder roots
	every page on (or the first shown top-level block of a tree without one)."""
	tree = _page_tree(blocks)
	if len(tree) == 1 and isinstance(tree[0], dict) and "body" in (tree[0].get("originalElement"), tree[0].get("element")):
		tree = tree[0].get("children") or []
	for block in tree:
		if not isinstance(block, dict) or block.get("element") in _INVISIBLE:
			continue
		if str((block.get("baseStyles") or {}).get("display") or "").strip() == "none":
			continue
		return block
	return None


def _has_h1(node, depth=0) -> bool:
	if depth > 16 or not isinstance(node, dict):
		return False
	if node.get("element") == "h1" or "<h1" in str(node.get("innerHTML") or "").lower():
		return True
	return any(_has_h1(child, depth + 1) for child in node.get("children") or [])


def _has_any_h1(blocks) -> bool:
	"""Whether any block of the page carries an h1."""
	return any(_has_h1(block) for block in _page_tree(blocks))


def _opens_with_own_title(blocks) -> bool:
	"""Whether the page's first section carries its h1: the page brings its own top."""
	first = _first_section(blocks)
	return first is not None and _has_h1(first)


# A face is a font stack or a token; a weight is a number or a keyword. Anything else could
# leave the custom property it is written into, so it is not a face.
_FONT_RE = re.compile(r"""^(?:var\(--[\w-]{1,60}\)|[\w\s,'-]{1,120})$""")
_WEIGHT_RE = re.compile(r"^(?:[1-9]00|normal|bold|lighter|bolder)$")


def _page_fonts(blocks) -> str:
	"""The page's own heading and text faces, as custom properties for the band (`--sph-*`).

	A page whose blocks name their fonts drew its band in the theme's instead: the band read as
	another website on top of the page (2026-09-14). The first heading and the first paragraph
	that name a face give it.
	"""
	found = {}

	def walk(node, depth=0):
		if depth > 16 or not isinstance(node, dict) or ("heading" in found and "body" in found):
			return
		styles = node.get("baseStyles") or {}
		family = str(styles.get("fontFamily") or "").strip().replace('"', "'")
		if family and _FONT_RE.match(family):
			element = node.get("element")
			if element in ("h1", "h2", "h3") and "heading" not in found:
				found["heading"] = family
				weight = str(styles.get("fontWeight") or "").strip()
				if _WEIGHT_RE.match(weight):
					found["weight"] = weight
			elif element == "p" and "body" not in found:
				found["body"] = family
		for child in node.get("children") or []:
			walk(child, depth + 1)

	for block in _page_tree(blocks):
		walk(block)
	declarations = [
		f"--sph-{name}:{found[key]};"
		for name, key in (("heading-font", "heading"), ("heading-weight", "weight"), ("body-font", "body"))
		if found.get(key)
	]
	return "".join(declarations)


def _absolute(url: str) -> str:
	"""`url` on the host this request is served on. A site profile answers on its own domain,
	which frappe.utils.get_url() does not know when the site's config names one host."""
	if url.startswith(("http://", "https://")):
		return url
	request = getattr(frappe.local, "request", None)
	host = getattr(request, "host", None) if request is not None else None
	if isinstance(host, str) and host:
		try:
			forwarded = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip()
		except Exception:
			forwarded = ""
		scheme = forwarded or getattr(request, "scheme", None) or "https"
		return f"{scheme}://{host}{url}"
	return frappe.utils.get_url(url)


def _breadcrumb_ld(trail) -> str:
	"""The trail as schema.org JSON-LD, for the search engines. The last crumb is the page
	itself and needs no link."""
	if not trail or len(trail) < 2:
		return ""
	items = []
	for position, crumb in enumerate(trail, 1):
		item = {"@type": "ListItem", "position": position, "name": str(crumb.get("label") or "")}
		if crumb.get("url") and position < len(trail):
			item["item"] = _absolute(str(crumb["url"]))
		items.append(item)
	data = json.dumps(
		{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items},
		ensure_ascii=False,
	)
	# a label is a page title: nothing in it may close the script or open a comment
	data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
	return f'<script type="application/ld+json">{data}</script>'


# //// Neoffice — whitelist REMOVED (was @frappe.whitelist(allow_guest=True)). Same reason as
# //// render_page_header above, plus one of its own: `doc` came from the caller, so over HTTP
# //// this rendered a band out of whatever dict was posted.
def render_builder_page_header(doc=None, own_top=None) -> str:
	"""The same band, for a page the editor built.

	Called from the Builder page template. The homepage keeps the hero the AI
	composed for it; every interior page opens on this instead of a title band
	each generation improvises differently — which is the whole point of having
	one. An interior page that opens on its own title keeps it too: the band then
	leaves only the breadcrumb trail, drawn in a slim strip and given as JSON-LD.
	"""
	if doc is None:
		return ""

	route = (doc.get("route") if hasattr(doc, "get") else getattr(doc, "route", "")) or ""
	route = str(route).strip("/")
	if _is_excluded(route, _excluded_routes(settings())):
		return ""
	# //// Neoffice — a home keeps the hero composed for it (see _is_home)
	if _is_home(route):
		return ""

	title = (
		(doc.get("page_title") if hasattr(doc, "get") else getattr(doc, "page_title", ""))
		or ""
	)
	if not title:
		return ""

	def _field(name):
		return (doc.get(name) if hasattr(doc, "get") else getattr(doc, name, None)) or ""

	# The page's meta description is already one descriptive line about this
	# page, written by whoever made it. Reusing it beats adding a second field
	# that says the same thing and that nothing fills.
	subtitle = _field("page_header_subtitle")
	description = _field("meta_description")
	blocks = _rendered_blocks(doc)
	# //// Neoffice — ...unless the page prints that line itself (neoffice-maintenance#393, see
	# //// _page_prints). A subtitle written for the band is kept as it is.
	if not subtitle and description and not _page_prints(blocks, description):
		subtitle = description

	# //// Neoffice — a page that opens on its own title keeps it, and the band writes in the
	# //// page's faces (2026-09-14, see _opens_with_own_title and _page_fonts).
	# `own_top` False draws the band whatever the first section is: the editor's preview hides it
	# itself while the live page carries its own h1 (header_footer.get_editor_page_header_html)
	quiet_title = ""
	opens_itself = _opens_with_own_title(blocks) if own_top is None else bool(own_top)
	# a page set to go without the band keeps only its trail, like a page with a top of its own
	# (the page settings' "No top page on this page", patches/add_page_top_fields.py)
	if _field("hide_page_header") and own_top is None:
		opens_itself = True
		# ...but a page keeps its title: without the band and with no h1 of its own it had none at all
		# (2026-09-14). The title stays as a visually hidden h1, read by screen readers and search engines.
		if not _has_any_h1(blocks):
			quiet_title = (
				'<h1 class="site-page-header__quiet" style="position:absolute;width:1px;height:1px;margin:-1px;'
				'padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0">'
				f"{escape_html(title)}</h1>"
			)
	context = frappe._dict(
		{
			"title": title,
			"page_header_subtitle": subtitle,
			"page_opens_itself": opens_itself,
			# the page setting "No top page on this page": not even the trail's strip is drawn
			"page_hides_band": bool(_field("hide_page_header")) and own_top is None,
			"page_fonts": _page_fonts(blocks),
			"page_image": _field("meta_image"),
		}
	)
	# a Builder page has no `parents`; the route is the trail
	frappe.local.page_header_route = route
	try:
		band = render(context)
	finally:
		frappe.local.page_header_route = None

	band = quiet_title + band if (band or quiet_title) else band
	if not band:
		return ""
	# only the trail, for the search engines: nothing drawn needs room under the header,
	# unless the page opens on a top of its own
	if not opens_itself and "site-page-header" not in band:
		return band

	# Two header presets deliberately pull the page up underneath themselves,
	# because a generated homepage opens on a tall hero built to sit under the
	# bar. An interior page now opens on this band instead — without a spacer
	# the floating header lands squarely on its title. A frappe page gets its
	# spacer from render_site_header(standalone=True); this is the Builder side
	# of the same rule.
	config = _config()
	style = (config.get("header_style") if config else "") or "Classic"
	if style in ("Floating", "Transparent"):
		# ...and its height travels with it, for the same reason the band's own
		# rules do: `web_include_css` never reaches a Builder page, so the rule
		# in web_pages.css would leave this div at zero height here — present in
		# the markup, invisible in effect, header still on the title.
		# The floating height cannot ride on `.site-header--floating + .spacer`
		# here: on a frappe page the spacer follows the header directly, but on
		# a Builder page it is the band that emits it, so it is no longer the
		# header's adjacent sibling. Measured before fixing: /blog got 104px and
		# /about 64px — the same band sitting 40px higher on half the site. A
		# modifier class says it outright instead of inferring it from position.
		band = (
			"<style>.site-header__spacer{height:var(--header-height,64px)}"
			".site-header__spacer--floating"
			"{height:calc(var(--header-height,64px) + 40px)}</style>"
			'<div class="site-header__spacer site-header__spacer--floating"'
			' aria-hidden="true"></div>'
		) + band

	return band


# //// Neoffice — the band designed in the Builder (2026-09-14): "comme si c'était une page, mais c'est juste
# //// le top". The site picks a Builder Component (page_header_component, template "Builder"); it is drawn
# //// on every inner page with the page's data bound by its blocks, the same way a page binds its data
# //// script: page_title, page_subtitle, breadcrumbs (a list of label and url) and page_image.
def render_component_band(component, data: dict) -> str:
	"""The chosen component rendered as the band, or an empty string when there is none or it fails.
	`data` must already be escaped: frappe's Jinja does not escape."""
	if not component:
		return ""
	block = frappe.db.get_value("Builder Component", component, "block")
	if not block:
		return ""
	from builder.builder.doctype.builder_page.builder_page import get_block_html, get_google_font_urls

	try:
		html, style, fonts, _dual = get_block_html(frappe.parse_json(block))
		body = frappe.render_template(html, data)
		style = frappe.render_template(style, data) if style else ""
	except Exception:
		frappe.log_error("Top page component could not be drawn", frappe.get_traceback())
		return ""
	links = "".join(
		f'<link rel="stylesheet" href="{escape_html(url)}" media="screen">' for url in get_google_font_urls(fonts or {})
	)
	return f'{links}{style}<section class="site-page-header site-page-header--builder">{body}</section>'


def default_band_block(prefix: str = "") -> dict:
	"""The top page a site starts from when it designs its own: the trail, the title and the subtitle of
	the page, bound to the band's data and set in the site's tokens. The trail is a Jinja loop in the
	block's text, the way the Builder's shortcodes are written."""
	def token(name: str, fallback: str) -> str:
		return f"var(--{prefix}-{name})" if prefix else fallback

	def uid() -> str:
		return frappe.generate_hash(length=10)

	trail = (
		"{% for crumb in breadcrumbs %}{% if not loop.first %}<span aria-hidden=\"true\"> / </span>{% endif %}"
		"{% if crumb.url %}<a href=\"{{ crumb.url }}\">{{ crumb.label }}</a>"
		"{% else %}<span aria-current=\"page\">{{ crumb.label }}</span>{% endif %}{% endfor %}"
	)
	text = {"color": token("text", "#111111"), "fontFamily": token("font-body", "inherit")}
	return {
		"blockId": uid(),
		"element": "section",
		"blockName": "top-page",
		"baseStyles": {
			"display": "flex", "flexDirection": "column", "width": "100%", "paddingTop": "56px",
			"paddingBottom": "48px", "background": token("background", "#ffffff"),
		},
		"children": [{
			"blockId": uid(),
			"element": "div",
			"blockName": "top-page-inner",
			# the column of the header and the footer (theme_variables.html): the width and the gutter on
			# the same box, down to the phone. The gutter on the outer section put the text 24px left of
			# the logo (2026-09-14).
			"baseStyles": {
				"display": "flex", "flexDirection": "column", "gap": "12px", "width": "100%",
				"maxWidth": "var(--container-width, 1280px)", "marginLeft": "auto", "marginRight": "auto",
				"paddingLeft": "var(--container-padding, 24px)", "paddingRight": "var(--container-padding, 24px)",
				"boxSizing": "border-box",
			},
			"mobileStyles": {
				"paddingLeft": "var(--container-padding-phone, 16px)",
				"paddingRight": "var(--container-padding-phone, 16px)",
			},
			"children": [
				{"blockId": uid(), "element": "nav", "blockName": "trail", "innerHTML": trail,
				 "attributes": {"aria-label": "Breadcrumb"},
				 "baseStyles": {**text, "fontSize": "13px", "opacity": "0.7"}, "children": []},
				{"blockId": uid(), "element": "h1", "blockName": "title", "innerHTML": "Page title",
				 "baseStyles": {"margin": "0", "fontSize": "clamp(2rem, 1.2rem + 2.4vw, 3.2rem)", "lineHeight": "1.1",
				                "color": token("text", "#111111"), "fontFamily": token("font-heading", "inherit")},
				 "dynamicValues": [{"key": "page_title", "property": "innerHTML", "type": "key", "comesFrom": "dataScript"}],
				 "children": []},
				{"blockId": uid(), "element": "p", "blockName": "subtitle", "innerHTML": "One line under the title.",
				 "baseStyles": {**text, "margin": "0", "maxWidth": "62ch", "fontSize": "17px", "lineHeight": "1.6", "opacity": "0.8"},
				 "dynamicValues": [{"key": "page_subtitle", "property": "innerHTML", "type": "key", "comesFrom": "dataScript"}],
				 "visibilityCondition": {"key": "page_subtitle", "comesFrom": "dataScript"},
				 "children": []},
			],
		}],
	}


def clear_band_cache(doc, method=None) -> None:
	"""A component in use as a site's band changes every page: the page cache holds the old one."""
	for doctype in ("Website Header Footer Config", "Website Header Footer Variant"):
		try:
			if not frappe.get_meta(doctype).has_field("page_header_component"):
				continue
			if doctype == "Website Header Footer Config":
				used = frappe.db.get_single_value(doctype, "page_header_component") == doc.name
			else:
				used = bool(frappe.db.exists(doctype, {"page_header_component": doc.name}))
		except Exception:
			continue
		if used:
			from frappe.website.utils import clear_cache

			clear_cache()
			return

