# //// Neoffice — added file (no upstream equivalent): the editor draws the site's header and footer with
# //// their own colours (2026-11-08).
"""The editor writes the css of its header and footer previews into a <style> element of its own. The
template's <style> tags came along, and the browser read them as the selector of the first rule: that rule,
the :root block holding the header's colours, was dropped, and every header in the editor lost its colours.
The footer preview also took the colours of the site the editor was opened on, not of the site being edited."""

import unittest
from unittest.mock import patch

import frappe

from builder.hf_utils import header_footer as hf


def header_css() -> str:
	"""The real header stylesheet, as the site renders it."""
	return frappe.render_template(
		"builder/templates/includes/header_footer/header_styles.html",
		{"colors": {"bg": "#241209", "text": "#faf6ee"}, "hf_config": None},
	)


class TestStyleText(unittest.TestCase):
	def test_the_template_is_wrapped_in_a_style_element(self):
		"""The defect needs the wrapper: if the template drops it, this test says the fix is moot."""
		self.assertTrue(header_css().lstrip().startswith("<style"))

	def test_the_bare_css_keeps_every_rule_and_no_tag(self):
		css = hf.style_text(header_css())
		self.assertNotIn("<style", css)
		self.assertNotIn("</style", css)
		self.assertIn("--header-bg: #241209", css)
		self.assertIn(".site-header--floating", css)

	def test_several_style_elements_are_joined(self):
		self.assertEqual(hf.style_text("<style>a{}</style>\n<style media='x'>b{}</style>"), "a{}\nb{}")

	def test_css_without_a_tag_is_left_as_it_is(self):
		self.assertEqual(hf.style_text(":root{--a:1}"), ":root{--a:1}")
		self.assertEqual(hf.style_text(None), "")


class TestEditorPreviews(unittest.TestCase):
	def setUp(self):
		self.config = frappe._dict(header_layout="Logo | Menu Center | Icons", footer_template="Simple")
		patcher = patch.object(hf, "_editor_chrome_config", return_value=self.config)
		patcher.start()
		self.addCleanup(patcher.stop)
		frappe.set_user("Administrator")

	def test_the_header_preview_gets_bare_css(self):
		with (
			patch.object(hf, "render_header", return_value="<header></header>"),
			patch.object(hf, "get_header_css", return_value=header_css()),
		):
			out = hf.get_editor_header_html(website_profile="Site")
		self.assertTrue(out["configured"])
		self.assertNotIn("<style", out["css"])
		self.assertIn("--header-bg: #241209", out["css"])

	def test_the_footer_preview_wears_the_colours_of_the_site_being_edited(self):
		with (
			patch.object(hf, "render_footer", return_value="<footer></footer>"),
			patch.object(
				hf, "get_footer_css", return_value="<style>:root{--footer-bg:#fff}</style>"
			) as footer_css,
		):
			out = hf.get_editor_footer_html(website_profile="Site")
		footer_css.assert_called_once_with(self.config)
		self.assertEqual(out["css"], ":root{--footer-bg:#fff}")
