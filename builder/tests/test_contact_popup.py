# //// Neoffice — added file (no upstream equivalent): the contact window of the site chrome
# //// (neoffice-maintenance#3336). A shop asked for its contact form in a window opened by a link of the menu,
# //// with no Contact page and none of its own details on display. The window sits in the footer of the chrome
# //// (like the newsletter's), holds the contact form of the site and nothing else, and is off unless a site asks.
import json
import os
import re
import unittest
from unittest.mock import patch

import frappe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = "builder/templates/includes/contact_form.html"
WINDOW_FIELDS = {
	"contact_popup": "Check",
	"contact_popup_title": "Data",
	"contact_popup_text": "Small Text",
	"contact_popup_success": "Small Text",
}
# what the business publishes about itself: none of it may reach the window
DETAILS = {
	"business_email": "owner@example.com",
	"business_phone": "+41 21 555 00 11",
	"business_address": "12 Example Street, 1000 Nowhere",
}
WINDOW = re.compile(r'<dialog class="builder-contact-form__dialog.*?</dialog>', re.S)


def render_footer(without=(), **config):
	base = {"contact_popup": 1, **DETAILS}
	base.update(config)
	for name in without:
		base.pop(name, None)
	context = {
		"config": frappe._dict(base),
		"template": "Simple",
		"logo": None,
		"description": "",
		"copyright_text": "",
		"social_links": [],
		"show_newsletter": 0,
		"show_opening_hours": 0,
		"opening_hours_display": "Compact",
		"opening_hours": None,
		"newsletter_title": None,
		"newsletter_placeholder": None,
		"powered_by": None,
		"footer_columns": {},
		"legal_links": [],
		"logo_height": "Medium",
		"footer_html": None,
	}
	return frappe.render_template("builder/templates/includes/header_footer/footer.html", context)


def window(html):
	found = WINDOW.search(html)
	assert found, "the footer draws no contact window"
	return found.group(0)


def ids(html):
	return set(re.findall(r'\bid="([^"]+)"', html))


class TestContactPopup(unittest.TestCase):
	def test_the_window_is_drawn_when_a_site_asks_for_it(self):
		html = window(render_footer())
		self.assertIn('aria-labelledby="site_contact_contact_title"', html)
		self.assertIn('id="site_contact_contact_title"', html)
		self.assertIn("data-contact-close", html)

	def test_a_site_that_does_not_ask_keeps_its_footer_as_it_was(self):
		off = render_footer(contact_popup=0)
		# a site saved before the fields existed has no key at all: the same footer
		self.assertEqual(off, render_footer(without=WINDOW_FIELDS))
		for marker in (
			"<dialog",
			"builder-contact-form",
			"data-neo-contact",
			"data-contact-close",
			"site_contact_",
		):
			self.assertNotIn(marker, off)

	def test_the_window_holds_the_contact_form_and_nothing_else(self):
		html = window(render_footer())
		# the same endpoint, token and fallback as the form of a page: the message arrives the same way
		self.assertIn('action="/api/method/neoffice_theme.website_messages.submit"', html)
		self.assertIn('data-token-url="/api/method/neoffice_theme.website_messages.issue_token"', html)
		self.assertIn('data-legacy-action="/api/method/frappe.www.contact.send_message"', html)
		self.assertIn("data-neo-contact", html)
		for name in ("full_name", "sender", "message", "website"):
			self.assertRegex(html, rf'<(?:input|textarea)\b[^>]*\bname="{name}"')
		# a window asks the three things every site needs: no steps, no phone
		self.assertNotIn("data-step", html)
		self.assertNotIn('type="tel"', html)

	def test_the_window_shows_no_detail_of_the_business(self):
		html = window(render_footer())
		self.assertNotIn("mailto:", html)
		self.assertNotIn("tel:", html)
		for value in DETAILS.values():
			self.assertNotIn(value, html)
		# the only link it may carry is the privacy policy, under the form
		for href in re.findall(r'href="([^"]*)"', html):
			self.assertIn("privacy", href)

	def test_the_window_has_no_button_of_its_own(self):
		"""A link of the menu opens it: a second button would draw a floating one at the foot of every page."""
		self.assertNotRegex(render_footer(), r"<button[^>]*data-contact-open")

	def test_the_window_waits_for_its_first_opening_to_ask_the_server_for_anything(self):
		"""The chrome is on every page: a form bound at load would take a token and look for a captcha on each one."""
		self.assertIn("data-neo-lazy", window(render_footer()))
		page = frappe.render_template('{%- set contact_dialog = true -%}{% include "' + FORM + '" %}', {})
		self.assertNotIn("data-neo-lazy", page)

	def test_the_runtime_comes_with_the_window(self):
		"""builder_page.py loads the script only on a page that carries a form: the chrome's window is on pages that carry none."""
		html = render_footer()
		self.assertRegex(html, r'<script src="/assets/builder/js/neo_contact_form\.js" defer></script>')
		self.assertNotIn("neo_contact_form", render_footer(contact_popup=0))

	def test_the_footer_of_the_chrome_gives_the_runtime_its_version(self):
		from builder.hf_utils.header_footer import render_footer as render

		doc = frappe.new_doc("Website Header Footer Variant")
		doc.update(
			{"website_profile": "E2E-contact-window-unsaved", "footer_template": "Simple", "contact_popup": 1}
		)
		self.assertRegex(
			render(doc),
			r'<script src="/assets/builder/js/neo_contact_form\.js\?v=[0-9a-f]{8}" defer></script>',
		)
		doc.contact_popup = 0
		self.assertNotIn("neo_contact_form", render(doc))

	def test_the_window_speaks_in_the_words_of_the_site(self):
		html = window(
			render_footer(
				contact_popup_title="Write to us",
				contact_popup_text="We answer within a day.",
				contact_popup_success="Thanks, we will reply soon.",
			)
		)
		self.assertIn(">Write to us</h2>", html)
		self.assertIn(
			'<p class="builder-contact-form__intro" id="site_contact_contact_intro">We answer within a day.</p>',
			html,
		)
		self.assertIn('aria-describedby="site_contact_contact_intro"', html)
		self.assertIn('data-sent="Thanks, we will reply soon."', html)

	def test_what_the_owner_wrote_is_escaped(self):
		html = window(
			render_footer(
				contact_popup_title='<script>alert("t")</script>',
				contact_popup_text="<img src=x onerror=alert(1)>",
				contact_popup_success='"><b>',
			)
		)
		self.assertNotIn("<script>alert", html)
		self.assertNotIn("<img src=x", html)
		self.assertIn("&lt;script&gt;", html)
		self.assertNotIn('data-sent=""><b>', html)

	def test_the_words_left_empty_are_the_forms_own(self):
		html = window(render_footer())
		self.assertIn(">Contact us</h2>", html)
		self.assertNotIn("builder-contact-form__intro", html)
		self.assertNotIn("aria-describedby", html)
		self.assertIn('data-sent="Thank you, your message has been sent."', html)

	def test_the_windows_fields_cannot_collide_with_a_window_of_a_page(self):
		"""A page may carry its own window (contact_dialog): same page, two windows, one id each."""
		chrome = window(render_footer())
		page = frappe.render_template('{%- set contact_dialog = true -%}{% include "' + FORM + '" %}', {})
		self.assertTrue(ids(chrome))
		self.assertEqual(set(), ids(chrome) & ids(page))
		# every label of the window still points at one of its own fields
		for target in re.findall(r'\bfor="([^"]+)"', chrome):
			self.assertIn(target, ids(chrome))

	def test_a_page_window_draws_what_it_drew_before(self):
		"""The form's new words are optional: a page that sets none gets the same markup as ever."""
		html = frappe.render_template('{%- set contact_dialog = true -%}{% include "' + FORM + '" %}', {})
		self.assertIn('id="dialog_sender_name"', html)
		self.assertIn('aria-labelledby="dialog_contact_title"', html)
		self.assertIn('data-sent="Thank you, your message has been sent."', html)
		# the sheet of the form names the class; the page draws no such paragraph
		self.assertNotIn('class="builder-contact-form__intro"', html)
		self.assertNotIn("aria-describedby", html)

	def test_the_two_chrome_doctypes_carry_the_same_fields_off_by_default(self):
		for folder in ("website_header_footer_config", "website_header_footer_variant"):
			path = os.path.join(HERE, "builder", "doctype", folder, f"{folder}.json")
			with open(path, encoding="utf-8") as f:
				doc = json.load(f)
			fields = {x["fieldname"]: x for x in doc["fields"]}
			for name, fieldtype in WINDOW_FIELDS.items():
				self.assertIn(name, fields, folder)
				self.assertEqual(fieldtype, fields[name]["fieldtype"], f"{folder}.{name}")
				self.assertIn(name, doc["field_order"], folder)
			self.assertEqual("0", fields["contact_popup"]["default"], folder)
			for name in ("contact_popup_title", "contact_popup_text", "contact_popup_success"):
				self.assertEqual("contact_popup", fields[name]["depends_on"], f"{folder}.{name}")

	def test_the_chrome_editor_can_set_them(self):
		from builder.hf_utils.chrome_api import SIMPLE_FIELDS

		for name in WINDOW_FIELDS:
			self.assertIn(name, SIMPLE_FIELDS)

	def test_the_privacy_policy_knows_a_site_whose_only_form_is_the_window(self):
		"""The pages hold no form, the chrome does: the policy must still say what the site does with a message."""
		from builder.site_ai.nora import legal

		rows = [{"blocks": '{"innerHTML": "<p>No form here</p>"}'}]
		for popup, expected in ((1, True), (0, False)):
			with (
				patch("builder.site_ai.nora.legal.frappe") as mock_frappe,
				patch("builder.api._get_site_chrome_config", return_value={"contact_popup": popup}),
			):
				mock_frappe.get_all.return_value = rows
				mock_frappe.db.has_column.return_value = True
				self.assertEqual(expected, legal.uses_of("A Profile", "vitrine")["form"], popup)


if __name__ == "__main__":
	unittest.main()
