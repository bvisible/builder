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

import frappe
from frappe import _

DEFAULTS = {
	"page_header_style": "Simple",
	"show_breadcrumbs": 1,
}

# Pages that carry their own opening and must not get a second one.
SKIP_PATHS = ("", "home", "index")


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


def _breadcrumbs(context, path: str, current: str) -> list:
	"""Home, the trail, then the page itself — each label once.

	Frappe builds `parents` for some pages (the blog does) and it knows the real
	titles, so it wins when present. It also already starts at Home, which is
	why this cannot simply prepend one: /blog was reading "Home / Home / Portal".
	"""
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


def render(context) -> str:
	"""The band, or an empty string when this page should not have one."""
	config = settings()
	style = config.get("page_header_style") or "Simple"
	if style == "None":
		return ""

	# A page may say it opens on its own composition — our 404 is a centred
	# statement, and a band above it would be the same words twice.
	if context.get("show_page_header") is False:
		return ""

	path = (frappe.request.path if frappe.request else "").strip("/")
	if path in SKIP_PATHS:
		return ""

	# an article opens on its cover; that hero already is the page header
	doc = context.get("doc")
	doctype = getattr(doc, "doctype", None) if doc else None
	if doctype == "Blog Post":
		return ""

	title = context.get("page_header_title") or context.get("title") or ""
	if not title:
		return ""

	return frappe.render_template(
		"builder/templates/includes/header_footer/page_header.html",
		{
			"style": style,
			"title": title,
			"subtitle": context.get("page_header_subtitle") or "",
			"breadcrumbs": _breadcrumbs(context, path, title) if config.get("show_breadcrumbs") else [],
		},
	)


@frappe.whitelist(allow_guest=True)
def render_page_header() -> str:
	"""Jinja entry point — the Web Template calls this with the page context.

	Reads `frappe.local.page_header_context`, which `blog_chrome`/`site_chrome`
	stash for it: a Web Template renders in its own scope and cannot see the
	page's context dict.
	"""
	context = getattr(frappe.local, "page_header_context", None)
	if context is None:
		return ""
	return render(context)
