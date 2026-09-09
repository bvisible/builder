# //// Neoffice — added file (no upstream equivalent): the one answer to "does this visitor see
# //// the offline site?", shared by the chrome (hf_utils/header_footer.py, overrides/site_chrome.py)
# //// and the page lookup (builder_page.find_page_with_path).
"""The website switch, seen from one request.

An offline site (Website Profile.website_online = 0, the fleet default) hides its
pages and its chrome from visitors: the login page and every remaining web page render
bare, deep links 404, the root goes to /app. Staff keeps everything: that IS the
preview before going live. So does the server-side render of the site build: the
visual check screenshots the pages through the loopback, naming the profile, and the
theme flags that request (`frappe.local.flags.server_side_render`); before that flag
the check reviewed the login page as the home of both League sites and revised the
real home on that critique (2026-09-09).
"""

import frappe


def hidden_from_visitor() -> bool:
	"""True when the resolved profile is offline and the request is a visitor's."""
	profile = getattr(frappe.local, "website_profile_doc", None)
	if profile is None or "website_online" not in profile or profile.get("website_online"):
		return False
	if frappe.local.flags.get("server_side_render"):
		return False
	roles = frappe.get_roles()
	return "System Manager" not in roles and "Website Manager" not in roles
