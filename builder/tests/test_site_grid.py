# //// Neoffice — added file (no upstream equivalent): the site grid the chrome shares with the pages
# //// (2026-09-14). Header, footer and top page band sat on 1280 px / 24 px, the pages of an editorial
# //// grid on 1440 px / 48 px: a 36 px staircase at 1400 px, and 16 px against 24 px on a phone.
import os
import unittest

import frappe

from builder.page_header import _CSS, default_band_block
from builder.site_ai.nora.site_builder import site_grid, site_grid_line


def template(name):
	path = os.path.join(frappe.get_app_path("builder", "templates", "includes", "header_footer"), name)
	with open(path, encoding="utf-8") as f:
		return f.read()


class TestSiteGrid(unittest.TestCase):
	def test_each_layout_system_has_its_grid(self):
		self.assertEqual(site_grid("editorial-grid"), {"container": "1440px", "gutter": "48px", "gutter-phone": "24px"})
		self.assertEqual(site_grid("classic-centered")["gutter"], "64px")
		self.assertEqual(site_grid("poster-brutalist"), {"container": "1280px", "gutter": "24px", "gutter-phone": "24px"})

	def test_the_grids_follow_the_recipes(self):
		"""SITE_GRIDS copies the containers the layout recipes write: a merge that changes them must change it."""
		with open(frappe.get_app_path("builder", "ai", "prompts.py"), encoding="utf-8") as f:
			recipes = f.read()
		self.assertIn("maxWidth '1440px', margin '0 auto', padding '0 48px'", recipes)
		self.assertIn("maxWidth '1200px', margin '0 auto', padding '0 64px'", recipes)
		self.assertIn("section padding '64px 24px'", recipes)

	def test_the_page_brief_names_the_grid_handles(self):
		handles = {"container": "var(--xx-container)", "gutter": "var(--xx-gutter)", "gutter-phone": "var(--xx-gutter-phone)"}
		line = site_grid_line(handles)
		for handle in handles.values():
			self.assertIn(handle, line)
		self.assertEqual(site_grid_line({"primary": "var(--xx-primary)"}), "")


class TestChromeOnTheGrid(unittest.TestCase):
	def test_the_chrome_reads_the_grid_tokens(self):
		from builder.hf_utils.header_footer import get_theme_css

		config = frappe.new_doc("Website Header Footer Config")
		config.token_prefix = "xx"
		css = get_theme_css(config)
		self.assertIn("--container-width: var(--xx-container, 1280px)", css)
		self.assertIn("--container-padding: var(--xx-gutter, 24px)", css)
		self.assertIn("--container-padding-phone: var(--xx-gutter-phone, 16px)", css)

	def test_without_tokens_the_chrome_keeps_its_fallbacks(self):
		from builder.hf_utils.header_footer import get_theme_css

		config = frappe.new_doc("Website Header Footer Config")
		config.token_prefix = ""
		self.assertNotIn("--container-width:", get_theme_css(config))

	def test_header_footer_and_band_change_gutter_at_the_same_thresholds(self):
		header, footer = template("header_styles.html"), template("footer_styles.html")
		self.assertIn("padding: 0 var(--container-padding-tablet, 16px);", header)
		self.assertIn("padding: 0 var(--container-padding-phone, 16px);", header)
		self.assertIn(".site-footer .site-footer__container", footer)
		self.assertIn("var(--container-padding-phone, 16px)", footer)
		self.assertIn("padding:44px var(--container-padding,24px) 36px", _CSS)
		self.assertIn("var(--container-padding-phone,16px)", _CSS)

	def test_on_a_phone_the_logo_gives_way_to_the_buttons(self):
		"""A wordmark kept its 280px on a 390px screen: the burger ended at 420px and the page zoomed out."""
		header = template("header_styles.html")
		phone = header[header.index("on a phone the logo gives way") :]
		self.assertIn(".site-header:not([data-layout=\"B\"]) .site-header__left {\n\t\tflex: 0 1 auto;\n\t\tmin-width: 0;", phone)
		self.assertIn("max-width: 100%;\n\t\tmax-height: 36px;", phone)

	def test_the_designed_band_starts_on_the_grid(self):
		"""The gutter sits on the column that carries the width, like the header's container: on the
		outer section it put the band's text 24px left of the logo."""
		band = default_band_block("xx")
		inner = band["children"][0]["baseStyles"]
		self.assertEqual(inner["maxWidth"], "var(--container-width, 1280px)")
		self.assertEqual(inner["paddingLeft"], "var(--container-padding, 24px)")
		self.assertEqual(inner["boxSizing"], "border-box")
		self.assertEqual(band["children"][0]["mobileStyles"]["paddingLeft"], "var(--container-padding-phone, 16px)")
		self.assertNotIn("paddingLeft", band["baseStyles"])
