# Chrome (header/footer/theme) API for the builder Settings > Theme tab.
#
# Ported from Unpress (unpress_core/hf_utils/chrome_api.py) — same public
# fieldnames, same curated field set, so a site's chrome stays interchangeable
# between the two editions.
#
# #//// Neoffice multi-site: unlike the Unpress single-site Studio, the chrome
# #//// here resolves per Website Profile. Reads mirror header_footer.py exactly
# #//// (variant only when it already exists — a GET must never create one and
# #//// silently divert a profile away from the Single); writes bootstrap the
# #//// variant from the Single, like api._get_site_chrome_config.
import json

import frappe

CHROME_ROLES = ("System Manager", "Website Manager")

SIMPLE_FIELDS = (
	# header
	"header_layout",
	"header_style",
	"sticky_header",
	"header_scroll",
	"header_height",
	"header_bg_color",
	"header_text_color",
	"logo_type",
	"logo_text",
	"logo_image",
	"show_cta",
	"cta_text",
	"cta_url",
	"cta_style",
	"search_type",
	"show_user",
	"show_wishlist",
	"show_cart",
	# footer
	"footer_template",
	"footer_bg_color",
	"footer_text_color",
	"show_footer_logo",
	"footer_description",
	"copyright_text",
	"show_social_links",
	"facebook_url",
	"twitter_url",
	"instagram_url",
	"linkedin_url",
	"youtube_url",
	"show_newsletter",
	"newsletter_title",
	# design system
	"radius_style",
	"shadow_style",
	"button_hover",
	"motion_style",
	# theme
	"primary_color",
	"secondary_color",
	"background_color",
	"text_color",
	"heading_font",
	"body_font",
)

# Select fields whose options the UI needs
OPTION_FIELDS = (
	"header_scroll",
	"radius_style",
	"shadow_style",
	"button_hover",
	"motion_style",
	"header_layout",
	"header_style",
	"header_height",
	"logo_type",
	"cta_style",
	"search_type",
	"footer_template",
	"heading_font",
	"body_font",
)


def _active_profile(profile: str | None = None) -> str | None:
	"""The Website Profile this request edits — explicit wins, else the one
	resolved from the Host by neoffice_theme's before_request hook."""
	return profile or getattr(frappe.local, "website_profile", None)


def _read_doc(profile: str | None = None):
	"""Resolve the chrome doc for reading. Never creates anything."""
	frappe.only_for(CHROME_ROLES)
	profile = _active_profile(profile)
	if profile and frappe.db.exists("DocType", "Website Header Footer Variant"):
		if frappe.db.exists("Website Header Footer Variant", profile):
			return frappe.get_doc("Website Header Footer Variant", profile)
	return frappe.get_single("Website Header Footer Config")


def _write_doc(profile: str | None = None):
	"""Resolve the chrome doc for writing, bootstrapping the profile's variant
	from the Single on first edit (same contract as api._get_site_chrome_config,
	inlined to keep hf_utils free of an import back into builder.api)."""
	frappe.only_for(CHROME_ROLES)
	profile = _active_profile(profile)
	if profile and frappe.db.exists("DocType", "Website Header Footer Variant"):
		if not frappe.db.exists("Website Header Footer Variant", profile):
			single = frappe.get_single("Website Header Footer Config")
			variant = frappe.new_doc("Website Header Footer Variant")
			for f in variant.meta.fields:
				if f.fieldtype in (
					"Section Break",
					"Column Break",
					"Tab Break",
					"HTML",
					"Table",
					"Table MultiSelect",
				):
					continue
				if f.fieldname == "website_profile":
					continue
				try:
					variant.set(f.fieldname, single.get(f.fieldname))
				except Exception:
					pass
			variant.website_profile = profile
			variant.insert(ignore_permissions=True)
			frappe.db.commit()
		return frappe.get_doc("Website Header Footer Variant", profile)
	return frappe.get_single("Website Header Footer Config")


@frappe.whitelist()
def get_chrome_settings(profile: str | None = None) -> dict:
	doc = _read_doc(profile)
	meta = frappe.get_meta(doc.doctype)

	settings = {field: doc.get(field) for field in SIMPLE_FIELDS}
	settings["menu_items"] = [
		{"label": row.label, "url": row.url, "open_in_new_tab": row.open_in_new_tab}
		for row in (doc.menu_items or [])
	]

	options = {}
	for field in OPTION_FIELDS:
		df = meta.get_field(field)
		options[field] = [opt for opt in (df.options or "").split("\n") if opt] if df else []
	settings["_options"] = options
	# echo the resolved profile back so the UI writes to the same doc it read
	settings["_profile"] = _active_profile(profile)
	return settings


@frappe.whitelist()
def update_chrome_settings(settings: str | dict, profile: str | None = None) -> dict:
	if isinstance(settings, str):
		settings = json.loads(settings)

	doc = _write_doc(profile)
	for field in SIMPLE_FIELDS:
		if field in settings:
			doc.set(field, settings[field])

	if "menu_items" in settings:
		doc.set("menu_items", [])
		for item in settings["menu_items"] or []:
			label = (item.get("label") or "").strip()
			url = (item.get("url") or "").strip()
			if label and url:
				doc.append(
					"menu_items",
					{
						"label": label,
						"url": url,
						"open_in_new_tab": 1 if item.get("open_in_new_tab") else 0,
					},
				)

	# on_update clears the website cache (and, on the Single only, syncs the
	# menu into Website Settings)
	doc.save()
	return {"ok": True}
