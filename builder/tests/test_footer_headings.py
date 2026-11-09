# //// Neoffice — added file (no upstream equivalent): the footer titles of the site chrome are
# //// h2, so they never skip a level after the page's last heading (Lighthouse "heading-order").
import os
import re
import unittest

import frappe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(HERE, "templates", "includes", "header_footer")
TITLE_CLASSES = ("site-footer__column-title", "site-footer__newsletter-title")


def render_footer(template: str) -> str:
	link = frappe._dict(url="/contact", label="Contact", is_external=0, open_in_new_tab=0)
	config = frappe._dict(newsletter_email_group="Shop Newsletter", newsletter_popup=0, motion_style="None")
	context = {
		"config": config,
		"template": template,
		"logo": None,
		"description": "",
		"copyright_text": "",
		"social_links": [],
		"show_newsletter": 1,
		"show_opening_hours": 0,
		"opening_hours_display": "Compact",
		"opening_hours": None,
		"newsletter_title": "Our letter",
		"newsletter_placeholder": None,
		"powered_by": None,
		"footer_columns": {"Shop": [link], "Help": [link]},
		"legal_links": [],
		"logo_height": "Medium",
		"footer_html": None,
	}
	return frappe.render_template("builder/templates/includes/header_footer/footer.html", context)


def source(name: str) -> str:
	with open(os.path.join(TEMPLATES, name)) as f:
		return f.read()


def rule(css: str, selector: str) -> str:
	match = re.search(r"^" + re.escape(selector) + r"\s*\{(.*?)^\}", css, re.S | re.M)
	assert match, f"no rule for {selector}"
	return match.group(1)


class TestFooterTitlesAreH2(unittest.TestCase):
	"""The titles were h4. After a page ending on an h1 or an h2 the level jumps by two, and the
	accessibility audit lists every column title (a shop's catalogue scored 82 because of it)."""

	def test_no_footer_template_draws_an_h4(self):
		for template in ("Standard", "Extended"):
			with self.subTest(template=template):
				self.assertNotIn("<h4", render_footer(template))

	def test_each_column_and_the_newsletter_title_is_an_h2(self):
		for template in ("Standard", "Extended"):
			html = render_footer(template)
			for css_class in TITLE_CLASSES:
				with self.subTest(template=template, css_class=css_class):
					tags = re.findall(r'<(h\d) class="' + css_class + '"', html)
					self.assertTrue(tags, f"{css_class} is missing from the {template} footer")
					self.assertEqual(set(tags), {"h2"})

	def test_both_columns_of_the_footer_are_titled(self):
		html = render_footer("Standard")
		self.assertEqual(html.count('<h2 class="site-footer__column-title">'), 2)

	def test_the_source_keeps_no_h4_title_either(self):
		"""A branch the render above does not reach (a template added later) still reads h2."""
		self.assertNotIn("<h4", source("footer.html"))


class TestAnH2TitleLooksLikeTheH4Did(unittest.TestCase):
	"""The theme scale gives every h2 a line height; the h4 had none. The class already pins the
	size, the weight, the colour and the margin, so only the line height is left to inherit."""

	def test_the_titles_inherit_their_line_height(self):
		css = source("footer_styles.html")
		for css_class in TITLE_CLASSES:
			with self.subTest(css_class=css_class):
				self.assertIn("line-height: inherit;", rule(css, "." + css_class))

	def test_the_titles_still_pin_their_size_weight_and_margin(self):
		css = source("footer_styles.html")
		for css_class in TITLE_CLASSES:
			body = rule(css, "." + css_class)
			for prop in ("font-size:", "font-weight:", "margin:"):
				with self.subTest(css_class=css_class, prop=prop):
					self.assertIn(prop, body)
