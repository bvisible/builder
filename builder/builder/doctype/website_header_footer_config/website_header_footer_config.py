# Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class WebsiteHeaderFooterConfig(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from builder.builder.doctype.website_menu_item.website_menu_item import WebsiteMenuItem
		from builder.builder.doctype.website_footer_link.website_footer_link import WebsiteFooterLink

		copyright_text: DF.Data | None
		cta_style: DF.Literal["Primary", "Secondary", "Outline"]
		cta_text: DF.Data | None
		cta_url: DF.Data | None
		facebook_url: DF.Data | None
		header_bg_color: DF.Color | None
		header_text_color: DF.Color | None
		footer_description: DF.SmallText | None
		footer_links: DF.Table[WebsiteFooterLink]
		footer_logo_image: DF.AttachImage | None
		footer_logo_text: DF.Data | None
		footer_logo_type: DF.Literal["Text", "Image", "Same as Header"]
		footer_template: DF.Literal["Minimal", "Standard", "Extended"]
		header_layout: DF.Literal["Logo | Menu Center | Icons", "Logo | Menu Right | Icons", "Menu Left | Logo Center | Icons"]
		instagram_url: DF.Data | None
		linkedin_url: DF.Data | None
		logo_image: DF.AttachImage | None
		logo_text: DF.Data | None
		logo_type: DF.Literal["Text", "Image"]
		menu_items: DF.Table[WebsiteMenuItem]
		newsletter_placeholder: DF.Data | None
		newsletter_title: DF.Data | None
		search_type: DF.Literal["None", "Icon (overlay)", "Search Bar (inline)", "Search Bar (full width bottom)"]
		show_cart: DF.Check
		show_cta: DF.Check
		show_footer_logo: DF.Check
		show_newsletter: DF.Check
		show_social_links: DF.Check
		show_user: DF.Check
		show_wishlist: DF.Check
		sticky_header: DF.Check
		twitter_url: DF.Data | None
		youtube_url: DF.Data | None
	# end: auto-generated types

	def validate(self):
		pass

	def on_update(self):
		"""Clear website cache when header/footer config changes."""
		if not getattr(self, "_syncing", False):
			self._sync_menu_to_website_settings()
		self.clear_website_cache()

	def _sync_menu_to_website_settings(self):
		"""Sync menu_items to Website Settings top_bar_items for client editing."""
		try:
			ws = frappe.get_doc("Website Settings")
			ws.flags._syncing = True
			ws.top_bar_items = []
			for item in (self.menu_items or []):
				ws.append("top_bar_items", {
					"label": item.label,
					"url": item.url,
					"open_in_new_tab": item.get("open_in_new_tab", 0),
				})
			ws.save(ignore_permissions=True)
		except Exception:
			# Non-critical: don't break config save if sync fails
			frappe.log_error("Menu sync to Website Settings failed", frappe.get_traceback())

	def clear_website_cache(self):
		"""Clear all website-related cache to reflect header/footer changes."""
		# Clear full website cache
		frappe.clear_cache()

		# Clear Redis cache for website pages
		frappe.cache().delete_keys("website_page")
		frappe.cache().delete_keys("page_context")
		frappe.cache().delete_keys("website_route_rules")
		frappe.cache().delete_keys("builder_page")

		# Clear Jinja template cache
		if hasattr(frappe.local, "jenv") and frappe.local.jenv:
			frappe.local.jenv.cache.clear()

		# Clear website generator cache
		frappe.cache().delete_value("website_generator_routes")
		frappe.cache().delete_value("website_pages")

		frappe.msgprint(_("Website cache cleared. Refresh your pages to see changes."), alert=True)

	def get_layout_type(self) -> str:
		"""Get the layout type (A or B) based on header_layout.

		- Layout A: Logo on left (center or right menu)
		- Layout B: Logo in center (menu on left)
		"""
		if self.header_layout == "Menu Left | Logo Center | Icons":
			return "B"
		return "A"

	def get_menu_position(self) -> str:
		"""Get menu position based on header_layout."""
		if self.header_layout == "Menu Left | Logo Center | Icons":
			return "left"
		if self.header_layout == "Logo | Menu Right | Icons":
			return "right"
		return "center"

	def get_search_config(self) -> dict:
		"""Get search configuration based on search_type."""
		search_type = self.search_type or "None"

		return {
			"enabled": search_type != "None",
			"icon": search_type == "Icon (overlay)",
			"bar": search_type == "Search Bar (inline)",
			"bar_full": search_type == "Search Bar (full width bottom)",
		}

	def get_visible_icons(self) -> dict:
		"""Get which icons should be visible based on checkboxes."""
		search_config = self.get_search_config()

		return {
			"search": search_config["icon"],
			"search_bar": search_config["bar"],
			"search_bar_full": search_config["bar_full"],
			"user": self.show_user,
			"wishlist": self.show_wishlist,
			"cart": self.show_cart,
		}

	def get_header_colors(self) -> dict:
		"""Get header color configuration."""
		return {
			"bg": self.header_bg_color or "#1a1a1a",
			"text": self.header_text_color or "#ffffff",
			"cta_bg": getattr(self, "primary_color", None) or "#6366f1",
			"cta_text": "#ffffff",
		}

	def get_footer_colors(self) -> dict:
		"""Get footer color configuration. Defaults to header colors."""
		return {
			"bg": getattr(self, "footer_bg_color", None) or self.header_bg_color or "#ffffff",
			"text": getattr(self, "footer_text_color", None) or self.header_text_color or "#1a1a1a",
		}

	def get_logo_data(self) -> dict:
		"""Get logo configuration. Uses default logo if none attached."""
		DEFAULT_LOGO = "/files/logo-default.png"
		return {
			"type": self.logo_type,
			"text": self.logo_text or "My Site",
			"image": self.logo_image or DEFAULT_LOGO,
		}

	def get_footer_logo_data(self) -> dict:
		"""Get footer logo configuration. Uses default logo if none attached."""
		DEFAULT_LOGO = "/files/logo-default.png"
		if self.footer_logo_type == "Same as Header":
			return self.get_logo_data()
		return {
			"type": self.footer_logo_type,
			"text": self.footer_logo_text or "My Site",
			"image": self.footer_logo_image or DEFAULT_LOGO,
		}

	def get_cta_data(self) -> dict | None:
		"""Get CTA button configuration."""
		if not self.show_cta:
			return None
		return {
			"text": self.cta_text,
			"url": self.cta_url,
			"style": self.cta_style,
		}

	def get_social_links(self) -> list[dict]:
		"""Get social media links."""
		if not self.show_social_links:
			return []

		links = []
		social_platforms = [
			("facebook", self.facebook_url, "Facebook"),
			("twitter", self.twitter_url, "Twitter"),
			("instagram", self.instagram_url, "Instagram"),
			("linkedin", self.linkedin_url, "LinkedIn"),
			("youtube", self.youtube_url, "YouTube"),
		]

		for platform, url, label in social_platforms:
			if url:
				links.append({
					"platform": platform,
					"url": url,
					"label": label,
				})

		return links

	def get_copyright_text(self) -> str:
		"""Get formatted copyright text."""
		import datetime
		text = self.copyright_text or "© {year} {site_name}. All rights reserved."
		return text.format(
			year=datetime.datetime.now().year,
			site_name=frappe.local.site or "Website"
		)

	def get_theme_data(self) -> dict:
		"""Get theme configuration for CSS variables injection.

		Returns a dict with all theme values compatible with WebShop CSS variables.
		"""
		return {
			"primary_color": getattr(self, "primary_color", None) or "#6c5ce7",
			"secondary_color": getattr(self, "secondary_color", None) or "#00b894",
			"background_color": getattr(self, "background_color", None) or "#ffffff",
			"text_color": getattr(self, "text_color", None) or "#1a1a1a",
			"heading_font": getattr(self, "heading_font", None) or "Inter",
			"body_font": getattr(self, "body_font", None) or "Inter",
		}


def get_header_footer_config() -> "WebsiteHeaderFooterConfig":
	"""Get the Website Header Footer Config singleton."""
	return frappe.get_single("Website Header Footer Config")
