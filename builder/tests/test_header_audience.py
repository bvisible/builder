# //// Neoffice — added file (no upstream equivalent): who sees the header's button and its cart, and the
# //// menu measured again when the blocks beside it change (2026-09-14). A signed-in reseller still had
# //// "request an account" in the bar, no cart, and the last menu link under "Hello <name>".
import os
import unittest
from unittest.mock import patch

import frappe

from builder.builder.doctype.website_header_footer_config.website_header_footer_config import (
	WebsiteHeaderFooterConfig,
)

MACROS = '{% from "builder/templates/includes/header_footer/macros.html" import render_cta, render_icons %}'


def chrome(**values):
	doc = frappe.new_doc("Website Header Footer Config")
	doc.update(values)
	return doc


def template(name):
	path = os.path.join(frappe.get_app_path("builder", "templates", "includes", "header_footer"), name)
	with open(path, encoding="utf-8") as f:
		return f.read()


class TestButtonAudience(unittest.TestCase):
	def test_automatic_keeps_an_account_button_for_visitors(self):
		for url in ("/login", "/login?redirect-to=/cart", "/signup/", "/compte-professionnel", "/#signup"):
			self.assertEqual(chrome(cta_url=url).get_cta_audience(), "visitors", url)

	def test_automatic_shows_any_other_button_to_everyone(self):
		for url in ("/contact", "/all-products", "https://example.com/login", "", None):
			self.assertEqual(chrome(cta_url=url).get_cta_audience(), "everyone", url)

	def test_an_explicit_choice_wins(self):
		self.assertEqual(chrome(cta_url="/login", cta_audience="Everyone").get_cta_audience(), "everyone")
		self.assertEqual(chrome(cta_url="/contact", cta_audience="Visitors only").get_cta_audience(), "visitors")
		self.assertEqual(chrome(cta_url="/contact", cta_audience="Signed-in users only").get_cta_audience(), "signed-in")

	def test_the_button_data_carries_its_audience(self):
		self.assertEqual(chrome(show_cta=1, cta_url="/login").get_cta_data()["audience"], "visitors")


class TestCartAudience(unittest.TestCase):
	def test_automatic_keeps_a_b2b_cart_for_signed_in_visitors(self):
		with patch.object(WebsiteHeaderFooterConfig, "is_b2b_site", return_value=True):
			self.assertEqual(chrome().get_cart_audience(), "signed-in")
		with patch.object(WebsiteHeaderFooterConfig, "is_b2b_site", return_value=False):
			self.assertEqual(chrome().get_cart_audience(), "everyone")

	def test_an_explicit_choice_wins(self):
		with patch.object(WebsiteHeaderFooterConfig, "is_b2b_site", return_value=True):
			self.assertEqual(chrome(cart_audience="Everyone").get_cart_audience(), "everyone")
		with patch.object(WebsiteHeaderFooterConfig, "is_b2b_site", return_value=False):
			self.assertEqual(chrome(cart_audience="Signed-in users only").get_cart_audience(), "signed-in")

	def test_the_icons_carry_the_cart_audience(self):
		with patch.object(WebsiteHeaderFooterConfig, "is_b2b_site", return_value=True):
			self.assertEqual(chrome(show_cart=1).get_visible_icons()["cart_audience"], "signed-in")

	def test_a_site_is_b2b_by_its_kind_or_its_sign_in_gate(self):
		doc = chrome()
		for row, expected in (((None, 1), True), (("B2B", 0), True), (("B2C", 0), False), (None, False)):
			with patch.object(frappe.local, "website_profile", "A site", create=True), patch.object(
				frappe.db, "get_value", return_value=row
			):
				self.assertEqual(doc.is_b2b_site(), expected, row)
		with patch.object(frappe.local, "website_profile", None, create=True):
			self.assertFalse(doc.is_b2b_site())


class TestHeaderMarkup(unittest.TestCase):
	def test_the_button_says_who_sees_it(self):
		cta = {"text": "Request an account", "url": "/login", "style": "Primary", "audience": "visitors"}
		self.assertIn('data-audience="visitors"', frappe.render_template(MACROS + "{{ render_cta(cta) }}", {"cta": cta}))
		cta = {"text": "Contact", "url": "/contact", "style": "Primary", "audience": "everyone"}
		self.assertNotIn("data-audience", frappe.render_template(MACROS + "{{ render_cta(cta) }}", {"cta": cta}))

	def test_a_b2b_cart_waits_for_the_sign_in(self):
		icons = {"search": 0, "search_bar": 0, "user": 0, "wishlist": 0, "cart": 1, "cart_audience": "signed-in"}
		html = frappe.render_template(MACROS + "{{ render_icons(icons) }}", {"icons": icons})
		self.assertIn('data-audience="signed-in"', html)

	def test_the_state_and_the_rule_ship_with_the_header(self):
		self.assertIn("user_id=", template("header.html"))
		styles = template("header_styles.html")
		self.assertIn('html.is-signed-in .site-header [data-audience="visitors"]', styles)
		self.assertIn('html:not(.is-signed-in) .site-header [data-audience="signed-in"]', styles)
		self.assertIn("is-signed-in", template("components/user_header.html"))

	def test_the_menu_is_measured_again_when_the_blocks_beside_it_change(self):
		"""The account block fills in after the first measure: "Hello Administrator" covered the last link."""
		styles = template("header_styles.html")
		self.assertIn("'.site-header__left', '.site-header__right'", styles)
		self.assertIn("observer.observe(side)", styles)
