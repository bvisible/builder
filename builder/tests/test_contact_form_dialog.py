# //// Neoffice — added file (no upstream equivalent): the contact form can wait in a window, carry
# //// the business's consent sentence and ask for the phone (2026-09-29). A shop asked for its form
# //// behind a "Contact us" button, with its own consent wording and none of its details on display.
import os
import re
import unittest

import frappe

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM = "builder/templates/includes/contact_form.html"
CONSENT = "By sending my enquiry, I agree that my details may be used to answer it."
OPEN_BUTTON = r"<button[^>]*data-contact-open"


def render(**params):
	"""The page's own way of giving a component its parameters: {%- set -%} before the include."""
	sets = []
	for name, value in params.items():
		if isinstance(value, bool):
			sets.append(f"{{%- set {name} = {'true' if value else 'false'} -%}}")
		else:
			sets.append(f'{{%- set {name} = "{value}" -%}}')
	return frappe.render_template("".join(sets) + f'{{% include "{FORM}" %}}', {})


class TestContactFormDialog(unittest.TestCase):
	def test_a_page_that_sets_nothing_keeps_the_form_it_had(self):
		html = render()
		self.assertNotIn("<dialog", html)
		self.assertNotIn('name="consent"', html)
		self.assertIn('id="sender_name"', html)
		phone = re.search(r'<input type="tel"[^>]*>', html).group(0)
		self.assertNotIn("required", phone)

	def test_the_window_opens_from_its_button(self):
		html = render(contact_dialog=True)
		self.assertIn('<dialog class="builder-contact-form__dialog"', html)
		self.assertRegex(html, OPEN_BUTTON)
		self.assertIn("u-btn u-btn--primary", html)
		# the window's fields keep ids of their own, so a page may also carry the inline form
		self.assertIn('id="dialog_sender_name"', html)
		self.assertIn('for="dialog_sender_name"', html)
		self.assertNotIn('id="sender_name"', html)

	def test_a_page_with_its_own_link_draws_no_second_button(self):
		html = render(contact_dialog=True, contact_button_text="")
		self.assertIn("<dialog", html)
		# the script names the attribute too: look for the button itself
		self.assertNotRegex(html, OPEN_BUTTON)
		# the window still has a title, the default one
		self.assertIn('id="dialog_contact_title"', html)

	def test_the_button_reads_what_the_page_says(self):
		html = render(contact_dialog=True, contact_button_text="Write to us")
		self.assertRegex(html, r"data-contact-open>Write to us</button>")

	def test_the_consent_box_must_be_ticked_and_travels_with_the_message(self):
		html = render(consent_text=CONSENT)
		box = re.search(r'<input type="checkbox"[^>]*>', html).group(0)
		self.assertIn("required", box)
		self.assertIn(f'value="{CONSENT}"', box)
		self.assertIn(f">{CONSENT}</label>", html)
		self.assertIn("data-consent-label=", html)
		self.assertIn("form.dataset.consentLabel", html)

	def test_the_phone_can_be_required(self):
		html = render(phone_required=True)
		phone = re.search(r'<input type="tel"[^>]*>', html).group(0)
		self.assertIn("required", phone)

	def test_the_catalogue_offers_the_four_parameters(self):
		from builder.site_ai.components import catalogue

		form = next(c for c in catalogue() if c.path == FORM)
		names = {p["name"] for p in form.params}
		self.assertEqual({"contact_dialog", "contact_button_text", "consent_text", "phone_required"}, names)
		with open(os.path.join(HERE, "templates", "includes", "contact_form.html"), encoding="utf-8") as f:
			template = f.read()
		for name in names:
			self.assertRegex(template, rf"\b{name} is defined\b", name)
		tag = form.tag({"contact_dialog": True, "contact_button_text": "", "not_declared": 1})
		self.assertIn("{%- set contact_dialog = true -%}", tag)
		self.assertIn('{%- set contact_button_text = "" -%}', tag)
		self.assertNotIn("not_declared", tag)


class TestFaqAccordion(unittest.TestCase):
	def test_the_sheet_folds_a_faq(self):
		with open(os.path.join(HERE, "templates", "includes", "header_footer", "theme_variables.html"), encoding="utf-8") as f:
			sheet = f.read()
		self.assertIn(":where(.u-faq) summary {", sheet)
		self.assertIn(".u-faq summary::-webkit-details-marker", sheet)
		self.assertIn(".u-faq details[open] > summary::after", sheet)

	def test_the_generator_is_told_how_to_fold_one(self):
		from builder.site_ai.nora.site_builder import CLASS_CONTRACT

		self.assertIn("['u-faq']", CLASS_CONTRACT)
		self.assertIn("`summary`", CLASS_CONTRACT)
