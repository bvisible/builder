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
