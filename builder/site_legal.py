# //// Neoffice — added file (no upstream equivalent): what a template needs to know about the legal layer of the site it renders.
"""The legal layer of a generated site (legal.py) reaches the templates through one Jinja method, `site_legal()`:

  - `privacy_url`: the route of the site's privacy policy, "" when it has none (a site built before the policy existed): the
    sentence under a form and the link in the cookie notice appear only when there is a page to link to;
  - `notice`: whether the site shows the cookie and privacy notice (`show_data_notice` of its chrome, set by the generator). The map
    include waits for the visitor's agreement on such a site, because loading Google's map tells Google who is looking;
  - `maps`: whether a published page of the site holds that map. Then the notice asks for the agreement (Accept / Refuse) instead of
    only telling: a visitor who accepts sees the map without a click, on every page, and can take the agreement back under the map.

Read from the database without ever creating the profile's chrome variant (api._get_site_chrome_config bootstraps one on a plain
read, which a visitor's page must not do)."""

import frappe

PRIVACY_ROUTES = ("privacy", "privacy-policy", "politique-de-confidentialite", "confidentialite", "datenschutz")
MAP_MARKER = "google_map.html"
MAPS_CACHED_FOR = 600


def _notice_on(profile: str | None) -> bool:
	try:
		if profile and frappe.db.exists("DocType", "Website Header Footer Variant") and frappe.db.exists("Website Header Footer Variant", profile):
			return bool(frappe.db.get_value("Website Header Footer Variant", profile, "show_data_notice"))
		return bool(frappe.db.get_single_value("Website Header Footer Config", "show_data_notice"))
	except Exception:
		return False


def _site_has_map(profile: str | None) -> bool:
	"""Whether a published page of this site includes the map. Read from the pages' blocks, so cached: a page that gains a map is
	seen within ten minutes, a site that never had one pays nothing."""

	def read() -> bool:
		try:
			filters = {"published": 1}
			if profile and frappe.db.has_column("Builder Page", "neo_website_profile"):
				filters["neo_website_profile"] = profile
			return any(MAP_MARKER in str(row.get("blocks") or "") for row in frappe.get_all("Builder Page", filters=filters, fields=["blocks"], limit_page_length=0))
		except Exception:
			return False

	key = f"neo_site_has_map::{profile or ''}"
	try:
		known = frappe.cache.get_value(key)
		if known is None:
			known = read()
			frappe.cache.set_value(key, known, expires_in_sec=MAPS_CACHED_FOR)
		return bool(known)
	except Exception:
		return read()


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
	"""{"privacy_url": str, "notice": bool, "maps": bool} for the site being rendered; computed once per request."""
	profile = getattr(frappe.local, "website_profile", None)
	cached = getattr(frappe.local, "neo_site_legal", None)
	if cached and cached[0] == profile:
		return cached[1]
	notice = _notice_on(profile)
	value = {"privacy_url": _privacy_url(profile), "notice": notice, "maps": bool(notice and _site_has_map(profile))}
	frappe.local.neo_site_legal = (profile, value)
	return value
