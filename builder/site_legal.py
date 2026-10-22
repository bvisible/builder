# //// Neoffice — added file (no upstream equivalent): what a template needs to know about the legal layer of the site it renders.
"""The legal layer of a generated site (legal.py) reaches the templates through one Jinja method, `site_legal()`:

  - `privacy_url`: the route of the site's privacy policy, "" when it has none (a site built before the policy existed): the
    sentence under a form and the link in the cookie notice appear only when there is a page to link to;
  - `notice`: whether the site shows the cookie and privacy notice (`show_data_notice` of its chrome, set by the generator). The map
    include waits for a click on such a site, because loading Google's map tells Google who is looking.

Read from the database without ever creating the profile's chrome variant (api._get_site_chrome_config bootstraps one on a plain
read, which a visitor's page must not do)."""

import frappe

PRIVACY_ROUTES = ("privacy", "privacy-policy", "politique-de-confidentialite", "confidentialite", "datenschutz")


def _notice_on(profile: str | None) -> bool:
	try:
		if profile and frappe.db.exists("DocType", "Website Header Footer Variant") and frappe.db.exists("Website Header Footer Variant", profile):
			return bool(frappe.db.get_value("Website Header Footer Variant", profile, "show_data_notice"))
		return bool(frappe.db.get_single_value("Website Header Footer Config", "show_data_notice"))
	except Exception:
		return False


def _privacy_url(profile: str | None) -> str:
	try:
		from builder.hf_utils.header_footer import _legal_pages_of_site

		for row in _legal_pages_of_site(profile):
			if row["url"].strip("/").lower() in PRIVACY_ROUTES:
				return row["url"]
	except Exception:
		pass
	return ""


def site_legal() -> dict:
	"""{"privacy_url": str, "notice": bool} for the site being rendered; computed once per request."""
	profile = getattr(frappe.local, "website_profile", None)
	cached = getattr(frappe.local, "neo_site_legal", None)
	if cached and cached[0] == profile:
		return cached[1]
	value = {"privacy_url": _privacy_url(profile), "notice": _notice_on(profile)}
	frappe.local.neo_site_legal = (profile, value)
	return value
