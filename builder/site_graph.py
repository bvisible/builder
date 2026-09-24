# //// Neoffice — added file (no upstream equivalent): the site's identity for search engines,
# //// declared once, on its home page. neoffice-maintenance#691 (lot 1), 2026-09-24.
#
# Google prints a site's name above each of its results (WebSite), and reads the organisation
# behind it — logo, contact, social profiles, and the policies every offer of a shop follows
# (returns, shipping) — from one Organization node, on the home page. None of it existed:
# Google guessed the name from the page titles, and the shop's offers pointed at policies
# nobody declared.
#
# The chrome holds the identity: its logo, its business_* fields and social links, per site
# through the Variant. An app that knows more adds it through the `site_organization` hook, a
# function given the Organization node to complete, which may return nodes of its own: webshop
# types it an OnlineStore, declares its return window and its free delivery, and adds its
# physical store with its hours.
import frappe

SOCIAL_FIELDS = ("facebook_url", "instagram_url", "linkedin_url", "youtube_url", "twitter_url")


def site_base() -> str:
	"""The address of the site being served, without the trailing slash: the profile's domain
	on a multi-site instance, as the canonical URLs of its pages (set_canonical_url)."""
	profile = getattr(frappe.local, "website_profile_doc", None)
	if profile and profile.get("primary_domain"):
		return f"https://{profile['primary_domain']}"
	return frappe.utils.get_url().rstrip("/")


def site_graph(config=None) -> dict | None:
	"""The WebSite and the Organization of the site being served, or None when the site has no
	chrome (an offline site) or no name of its own."""
	if config is None:
		from builder.hf_utils.header_footer import get_header_footer_config

		config = get_header_footer_config()
	if not config:
		return None
	name = display_name(config)
	if not name:
		return None
	base = site_base()
	organization = {"@type": "Organization", "@id": f"{base}/#organization", "name": name, "url": f"{base}/"}
	legal_name = (config.get("business_name") or "").strip()
	if legal_name and legal_name != name:
		organization["legalName"] = legal_name
	logo = _logo(config, base)
	if logo:
		organization["logo"] = logo
	for field, key in (("business_phone", "telephone"), ("business_email", "email")):
		value = (config.get(field) or "").strip()
		if value:
			organization[key] = value
	profiles = [config.get(field).strip() for field in SOCIAL_FIELDS if (config.get(field) or "").strip()]
	if profiles:
		organization["sameAs"] = profiles
	# a contribution completes the Organization in place, and may return nodes of its own for
	# the graph (webshop: its physical store, tied to the Organization by @id)
	nodes = []
	for method in frappe.get_hooks("site_organization") or []:
		try:
			added = frappe.get_attr(method)(organization)
		except Exception:
			frappe.log_error(f"Site organization: {method} failed", frappe.get_traceback())
			continue
		if isinstance(added, list | tuple):
			nodes.extend(node for node in added if isinstance(node, dict))
	website = {
		"@type": "WebSite",
		"@id": f"{base}/#website",
		"url": f"{base}/",
		"name": name,
		"publisher": {"@id": organization["@id"]},
	}
	return {"@context": "https://schema.org", "@graph": [website, organization, *nodes]}


def display_name(config) -> str:
	"""The one name the site goes by: the WebSite name of its home page, and what the pages
	other apps render announce (webshop's og:site_name, title suffix and seller). Google
	reads them together to pick the name it prints above the site's results: the header's
	text, else Website Settings' name, else the business name."""
	from builder.site_icon import site_name

	return site_name(config) or (config.get("business_name") or "").strip()


def is_site_home(page) -> bool:
	"""Whether this Builder page is the one served at the root of the site."""
	request = getattr(frappe.local, "request", None)
	if (getattr(request, "path", None) or "").rstrip("/") == "":
		return request is not None
	profile = getattr(frappe.local, "website_profile_doc", None)
	if profile and profile.get("home_route"):
		return profile["home_route"] == page.route
	return page.is_home_page()


def _logo(config, base: str) -> str | None:
	"""The header's picture as an absolute address (Google wants a logo it can fetch)."""
	from urllib.parse import quote

	logo = config.get_logo_data() if hasattr(config, "get_logo_data") else {}
	image = logo.get("image") if (config.get("logo_type") or "Image") == "Image" else None
	if not image or not config.get("logo_image"):
		# the chrome's own default is Neoffice's logo: not this organisation's
		return None
	if image.startswith(("http://", "https://")):
		return image
	return base + quote(image, safe="/%?=&:+~")
