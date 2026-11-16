# //// Neoffice — REWRITTEN. Upstream's 404.py rendered a published Builder Page whose route
# //// is "404" and otherwise fell through to frappe's bare not-found page. Ours keeps the
# //// site chrome and tells apart a wrong address from a route the site deliberately
# //// carries for a section that is not built yet (RESERVED). At the merge: read upstream's
# //// find_page_with_path seam again before taking either side wholesale.
"""The page a visitor lands on when the address is wrong — or not built yet.

Frappe's own 404 blocks the navbar and the footer, so it arrives as a bare
sentence on a grey field: the visitor loses the site at the exact moment they
need a way back into it.

It also cannot tell apart the two things that produce a 404 on a young site.
One is a wrong address. The other is a link the site deliberately carries for a
section that is coming — the shop menu on an Unpress site, which the generator
writes because the site will have one. That second case deserves a different
sentence and no apology.
"""

import frappe

# //// Neoffice — see the module header.
from frappe import _

# //// Neoffice — no module-level `no_cache` (neoffice-maintenance#2727): it kept every not-found page out of frappe's
# //// page cache, so each robot probe (/.env, /wp-login.php…) rendered the whole site chrome again, ~200 ms of a
# //// worker. get_context decides instead, page by page (see `_kept_out_of_the_cache`).

# Routes an app we have not installed yet will own. The generator writes these
# links on purpose, so the site keeps them and says what they are.
RESERVED = {
	"all-products": {"app": "webshop", "label": "Shop"},
	"cart": {"app": "webshop", "label": "Cart"},
	"orders": {"app": "webshop", "label": "Orders"},
	"wishlist": {"app": "webshop", "label": "Wishlist"},
	"me": {"app": "webshop", "label": "My Account"},
}


# //// Neoffice — see the module header.
def _translatable_labels():
	"""Extraction markers — never called. Keep in sync with RESERVED."""
	_("Shop")
	_("Cart")
	_("Orders")
	_("Wishlist")
	_("My Account")


def get_context(context):
	# //// Neoffice — see the module header.
	path = (frappe.request.path if frappe.request else "").strip("/")
	root = path.split("/", 1)[0] if path else ""

	# //// Neoffice — the installed apps are read for every address now, not only for a reserved route: the cache
	# //// decision below needs them (neoffice-maintenance#2727).
	installed = _installed_apps()
	reserved = RESERVED.get(root)
	# once the app is really there, a 404 under its route is a genuine 404
	if reserved and reserved["app"] in installed:
		reserved = None

	# //// Neoffice — frappe's page cache (neoffice-maintenance#2727), see `_kept_out_of_the_cache`.
	context.no_cache = 1 if _kept_out_of_the_cache(installed) else 0
	# This page is its own opening statement, centred on the page: the shared
	# band above it would print the same words a second time.
	context.show_page_header = False
	# //// Neoffice — ...nor a breadcrumb of its own (2026-09-14): frappe's web.html then drew the shop's
	# //// (webshop templates/includes/breadcrumbs.html), which always names the shop, so a wrong address
	# //// read "Home > Shop > Page not found". A trail to a page that does not exist leads nowhere.
	context.no_breadcrumbs = 1
	context.is_reserved = bool(reserved)
	context.reserved_label = _(reserved["label"]) if reserved else ""
	context.title = _("Coming soon") if reserved else _("Page not found")

	# the menu, so the visitor has somewhere to go from here
	try:
		from builder.hf_utils.header_footer import get_header_footer_config

		config = get_header_footer_config()
		context.menu_items = list(config.menu_items or []) if config else []
	except Exception:
		context.menu_items = []

	return context


# //// Neoffice — see the module header.
def _installed_apps() -> set:
	try:
		return set(frappe.get_installed_apps())
	except Exception:
		return set()


# //// Neoffice — neoffice-maintenance#2727.
def _kept_out_of_the_cache(installed: set) -> bool:
	"""Whether this rendering must stay out of frappe's page cache.

	The cache holds ONE not-found page per language and per website profile (the key of our frappe fork's
	cache_html), whatever the address asked, and it is read before get_context runs. So the page may go into it only
	when it does not depend on the address, and only from a visitor's rendering:
	- while an app of RESERVED is missing, a reserved route says « Coming soon » and any other address « Page not
	  found »: one cached page would answer both, so none is cached on such a site;
	- a signed-in person's rendering is never written: the page cache is the anonymous visitor's.
	"""
	if frappe.session.user != "Guest":
		return True
	return any(spec["app"] not in installed for spec in RESERVED.values())
