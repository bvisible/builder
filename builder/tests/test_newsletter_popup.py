# //// Neoffice — added file (no upstream equivalent): the newsletter window of the site chrome
# //// (2026-09-29). A shop asked for a welcome code offered to first-time visitors who subscribe.
import json
import os
import re
import unittest
from unittest.mock import MagicMock, patch

import frappe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POPUP_FIELDS = {
	"newsletter_popup": "Check",
	"newsletter_popup_title": "Data",
	"newsletter_popup_text": "Small Text",
	"newsletter_popup_consent": "Small Text",
	"newsletter_popup_success": "Small Text",
	"newsletter_popup_delay": "Int",
}


def render_footer(**config):
	base = {"newsletter_email_group": "Shop Newsletter", "newsletter_popup": 1}
	base.update(config)
	context = {
		"config": frappe._dict(base), "template": "Simple", "logo": None, "description": "", "copyright_text": "",
		"social_links": [], "show_newsletter": 0, "show_opening_hours": 0, "opening_hours_display": "Compact",
		"opening_hours": None, "newsletter_title": base.get("newsletter_title"), "newsletter_placeholder": None,
		"powered_by": None, "footer_columns": {}, "legal_links": [], "logo_height": "Medium", "footer_html": None,
	}
	return frappe.render_template("builder/templates/includes/header_footer/footer.html", context)


class TestNewsletterPopup(unittest.TestCase):
	def test_the_window_is_offered_with_the_site_words(self):
		html = render_footer(
			newsletter_popup_title="Welcome aboard",
			newsletter_popup_text="Subscribe and receive a code.",
			newsletter_popup_consent="By subscribing, you agree to receive our newsletter.",
			newsletter_popup_success="Check your inbox.",
			newsletter_popup_delay=5,
		)
		self.assertIn('<dialog class="site-newsletter-popup"', html)
		self.assertIn('data-delay="5"', html)
		self.assertIn('data-key="builder-newsletter-popup:Shop Newsletter"', html)
		self.assertIn('data-success="Check your inbox."', html)
		self.assertIn(">Welcome aboard</h2>", html)
		self.assertIn("Subscribe and receive a code.", html)
		self.assertIn("By subscribing, you agree to receive our newsletter.", html)
		self.assertIn("/api/method/builder.api.subscribe_to_newsletter", html)
		# the group is the site's: the window never names one in its request
		script = html[html.index('<dialog class="site-newsletter-popup"'):]
		self.assertNotIn("email_group:", script)

	def test_the_title_falls_back_to_the_newsletter_title(self):
		html = render_footer(newsletter_title="Our letter")
		self.assertIn(">Our letter</h2>", html)

	def test_no_window_unless_asked_and_given_a_group(self):
		self.assertNotIn("site-newsletter-popup", render_footer(newsletter_popup=0))
		self.assertNotIn("<dialog", render_footer(newsletter_email_group=None))

	def test_the_window_stays_away_from_a_purchase(self):
		html = render_footer()
		guard = re.search(r"if \(/\^\\/\((.+?)\)", html)
		self.assertIsNotNone(guard)
		for route in ("cart", "checkout", "login", "me", "orders?"):
			self.assertIn(route, guard.group(1).split("|"))

	def test_the_two_chrome_doctypes_carry_the_same_fields(self):
		for folder in ("website_header_footer_config", "website_header_footer_variant"):
			path = os.path.join(HERE, "builder", "doctype", folder, f"{folder}.json")
			with open(path, encoding="utf-8") as f:
				doc = json.load(f)
			fields = {x["fieldname"]: x for x in doc["fields"]}
			for name, fieldtype in POPUP_FIELDS.items():
				self.assertIn(name, fields, folder)
				self.assertEqual(fieldtype, fields[name]["fieldtype"], f"{folder}.{name}")
				self.assertIn(name, doc["field_order"], folder)
			self.assertEqual("8", fields["newsletter_popup_delay"]["default"], folder)
			self.assertIn("newsletter_popup", fields["newsletter_email_group"]["depends_on"], folder)

	def test_the_chrome_editor_can_set_them(self):
		from builder.hf_utils.chrome_api import SIMPLE_FIELDS

		for name in POPUP_FIELDS:
			self.assertIn(name, SIMPLE_FIELDS)

	def test_a_button_wearing_the_design_system_class_keeps_its_padding(self):
		"""The page reset zeroes a <button>'s padding at one element's weight: .u-btn must reach
		a <button> at that weight too, or the window's Subscribe loses its padding."""
		with open(os.path.join(HERE, "templates", "includes", "header_footer", "theme_variables.html"), encoding="utf-8") as f:
			sheet = f.read()
		rule = re.search(r":where\(\.u-btn\),\s*button:where\(\.u-btn\) \{(.*?)\}", sheet, re.S)
		self.assertIsNotNone(rule)
		self.assertIn("padding:", rule.group(1))

	def test_a_welcome_email_that_fails_is_logged_not_swallowed(self):
		"""The visitor reads "check your inbox" whatever happens: a welcome email (a code, in a shop)
		that never left must reach the Error Log, with the group and the address."""
		import builder.api as api

		raw = api.subscribe_to_newsletter.__wrapped__  # past the rate limit
		template = frappe._dict(response_="Your welcome code", subject="Welcome")

		def get_doc(*args, **kwargs):
			if isinstance(args[0], dict):
				return MagicMock()  # the Email Group Member
			return {"Email Group": MagicMock(), "Email Template": template}[args[0]]

		with (
			patch("builder.hf_utils.header_footer.get_header_footer_config", return_value={"newsletter_email_group": "Shop Newsletter"}),
			patch.object(frappe.db, "exists", side_effect=lambda doctype, filters=None: doctype == "Email Group"),
			patch.object(frappe.db, "get_value", return_value="Welcome Template"),
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(frappe, "sendmail", side_effect=RuntimeError("outgoing account down")),
			patch.object(frappe, "log_error") as log_error,
		):
			result = raw("visitor@example.com")
		self.assertTrue(result["success"])
		log_error.assert_called_once()
		title, message = log_error.call_args.args
		self.assertEqual("Newsletter welcome email not sent", title)
		self.assertIn("Shop Newsletter", message)
		self.assertIn("visitor@example.com", message)
		self.assertIn("outgoing account down", message)

