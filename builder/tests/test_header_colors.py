# //// Neoffice — added file (no upstream equivalent): the header colours of the site chrome.
import unittest
from types import SimpleNamespace

from builder.builder.doctype.website_header_footer_config.website_header_footer_config import (
	WebsiteHeaderFooterConfig,
	_contrast,
	_luminance,
	_readable_on,
)


class TestHeaderColors(unittest.TestCase):
	def test_luminance_and_contrast(self):
		self.assertAlmostEqual(_luminance("#ffffff"), 1.0, places=3)
		self.assertAlmostEqual(_luminance("#000"), 0.0, places=3)
		self.assertEqual(_luminance("not a colour"), 0.5)
		self.assertGreater(_contrast("#ffffff", "#000000"), 20)
		self.assertAlmostEqual(_contrast("#1b1f24", "#1b1f24"), 1.0, places=3)

	def test_a_cta_in_the_header_colour_falls_back_to_the_secondary(self):
		# a reseller site: a dark site whose primary IS the header background
		config = SimpleNamespace(header_bg_color="#1b1f24", header_text_color="#f5f5f5", primary_color="#1b1f24", secondary_color="#e578d1")
		colours = WebsiteHeaderFooterConfig.get_header_colors(config)
		self.assertEqual(colours["cta_bg"], "#e578d1")
		# a pale button takes a dark label, white would not read on pink
		self.assertEqual(colours["cta_text"], "#1f272e")

	def test_a_cta_that_stands_out_keeps_the_primary(self):
		config = SimpleNamespace(header_bg_color="#ffffff", header_text_color="#1a1a1a", primary_color="#6366f1", secondary_color="#e578d1")
		colours = WebsiteHeaderFooterConfig.get_header_colors(config)
		self.assertEqual(colours["cta_bg"], "#6366f1")
		self.assertEqual(colours["cta_text"], "#ffffff")

	def test_a_link_reads_on_the_page_background(self):
		from builder.hf_utils.header_footer import _link_colour

		# a dark site whose primary IS its background: the links took the secondary
		self.assertEqual(
			_link_colour({"background_color": "#1b1f24", "primary_color": "#1b1f24", "secondary_color": "#e578d1", "text_color": "#f5f5f5"}),
			"#e578d1",
		)
		# nothing else stands out: the page's own text colour
		self.assertEqual(
			_link_colour({"background_color": "#1b1f24", "primary_color": "#1b1f24", "secondary_color": "#1b1f24", "text_color": "#f5f5f5"}),
			"#f5f5f5",
		)
		# an ordinary palette keeps its primary
		self.assertEqual(
			_link_colour({"background_color": "#ffffff", "primary_color": "#6366f1", "secondary_color": "#e578d1", "text_color": "#1a1a1a"}),
			"#6366f1",
		)

	def test_the_generic_link_rules_never_outrank_a_component(self):
		"""The page's link colours must stay at the weight of a bare `a`.

		Written `a:not(.u-btn):hover`, the exclusion weighed more than a class and beat
		the menu, the footer links and the header CTA, repainting all three on hover
		(2026-09-10). Every narrowing of these rules goes inside :where().
		"""
		import pathlib
		import re

		css = pathlib.Path(__file__).parent.parent.joinpath("templates/includes/header_footer/theme_variables.html").read_text()
		offenders = [
			selector
			for selector in re.findall(r"^\s*(a[^\s{,][^{,\n]*)\s*[,{]", css, re.M)
			if (":not(" in selector or "[" in selector) and ":where(" not in selector
		]
		self.assertEqual(offenders, [])

	def test_without_a_usable_secondary_the_header_text_is_the_button(self):
		config = SimpleNamespace(header_bg_color="#1b1f24", header_text_color="#f5f5f5", primary_color="#1b1f24", secondary_color=None)
		colours = WebsiteHeaderFooterConfig.get_header_colors(config)
		self.assertEqual(colours["cta_bg"], "#f5f5f5")
		self.assertEqual(colours["cta_text"], "#1f272e")
		self.assertEqual(_readable_on("#ffffff", ["#ffffff", None, "#fefefe"]), "#fefefe")


class TestShopPagesKeepTheChromeInk(unittest.TestCase):
	"""The chrome never writes light-ground text over the shop's pages.

	The shop draws on the chrome's ground with the chrome's ink (its tokens read
	--background-color and --text-color), so a rule giving `body.product-page` the dark
	light-surface text made the product title, the filter heading and the icons vanish on
	a dark site (2026-09-12). The white-card rule stays for frappe's own cards, and names
	none of the shop's.
	"""

	def _css(self):
		"""The template's rules, its comments stripped: the history above the block names
		the very selector this test forbids."""
		import pathlib
		import re

		css = pathlib.Path(__file__).parent.parent.joinpath("templates/includes/header_footer/theme_variables.html").read_text()
		return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

	def test_no_rule_targets_the_shop_pages(self):
		self.assertNotIn("body.product-page", self._css())

	def test_the_white_card_rule_names_no_shop_card(self):
		import re

		rule = re.search(r":where\(([^)]*)\)\s*\{\s*--text-color: #1f272e", self._css())
		self.assertIsNotNone(rule, "the white-card rule is gone")
		for shop_class in (".product-card", ".item-card", ".cart-items"):
			self.assertNotIn(shop_class, rule.group(1))


class TestOverImageRule(unittest.TestCase):
	def test_a_block_that_places_itself_keeps_its_position(self):
		"""A tile's photograph laid across it (position: absolute) was turned back into a flex
		item by the design system's full-weight `.u-over-image > *` and shrank to a strip beside
		its title, on the published page only."""
		import os

		import builder

		path = os.path.join(os.path.dirname(builder.__file__), "templates", "includes", "header_footer", "theme_variables.html")
		with open(path) as f:
			css = f.read()
		self.assertIn(":where(.u-over-image > *)", css)
		self.assertNotRegex(css, r"(?m)^\.u-over-image > \*")
		# the scrim comes after the children, so a photograph laid in the section sits under it
		self.assertIn(".u-over-image::after", css)
		self.assertNotIn(".u-over-image::before", css)
