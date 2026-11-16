# //// Neoffice — added file (no upstream equivalent): a page rendered for a preview image or a PDF links no
# //// rendered route (neoffice-maintenance#1890).
"""Chrome's PDF generator, which also draws the preview images of the pages, reads every request to the site as a
file. /builder_assets/tokens.css is a rendered route, not a file: the site chrome linked it on every site with tokens,
so each preview image was refused as "Attempted Unauthorized File Access in PDF Generator" and wrote an Error Log row
(five in one minute on 15.11, one per page of a site being published). A Builder page already inlines the stylesheet
in a preview (webpage.html); the chrome no longer links it there, and still links it on every page a visitor opens."""

import os
import unittest
from unittest.mock import patch

import frappe
import jinja2

from builder.hf_utils import header_footer as hf

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
THEME = {
	"token_prefix": "spa",
	"primary_color": "#7a4b3a",
	"secondary_color": "#d9c2a7",
	"background_color": "#fbf7f2",
	"text_color": "#2b211c",
	"heading_font": "Inter",
	"body_font": "Inter",
}
LINK = 'href="/builder_assets/tokens.css"'


def render(for_preview: bool, theme=THEME) -> str:
	"""theme_variables.html as the site renders it, read from the file."""
	env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES))
	template = env.get_template("includes/header_footer/theme_variables.html")
	return template.render(
		theme=theme, for_preview=for_preview, font_stylesheets=[], **hf.button_colours(theme)
	)


class Config:
	def get_theme_data(self):
		return dict(THEME)


class TestTheTokenStylesheet(unittest.TestCase):
	def test_a_visitor_gets_the_link(self):
		self.assertIn(LINK, render(for_preview=False))

	def test_a_preview_gets_no_link(self):
		self.assertNotIn(LINK, render(for_preview=True))

	def test_a_site_without_tokens_never_had_one(self):
		self.assertNotIn(LINK, render(for_preview=False, theme={**THEME, "token_prefix": ""}))


class TestTheChromeKnowsItRendersAPreview(unittest.TestCase):
	def theme_context(self, request):
		missing = object()
		before = getattr(frappe.local, "request", missing)
		frappe.local.request = request
		try:
			with (
				patch.object(hf.frappe, "render_template", return_value="") as rendered,
				patch("builder.hosted_fonts.chrome_stylesheets", return_value=[]),
			):
				hf.get_theme_css(Config())
		finally:
			if before is missing:
				del frappe.local.request
			else:
				frappe.local.request = before
		return rendered.call_args.args[1]

	def test_a_preview_request_is_said(self):
		self.assertTrue(self.theme_context(frappe._dict(for_preview=True))["for_preview"])

	def test_a_visit_is_not_a_preview(self):
		self.assertFalse(self.theme_context(frappe._dict())["for_preview"])
		self.assertFalse(self.theme_context(None)["for_preview"])


if __name__ == "__main__":
	unittest.main()
