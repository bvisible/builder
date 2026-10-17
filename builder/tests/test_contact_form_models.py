# //// Neoffice — added file (no upstream equivalent): contact_model, which says WHICH form the
# //// include draws (2026-10-17, neoffice-maintenance#1593). One shortcode, three forms.
# ////
# //// The test that matters most is the first: the default must stay `steps`, because that is what
# //// every page written before this parameter already draws. A page in production must not change
# //// shape because we added a choice.
import re
import unittest

import frappe

FORM = "builder/templates/includes/contact_form.html"


def render(**params):
	"""The page's own way of giving a component its parameters: {%- set -%} before the include."""
	sets = []
	for name, value in params.items():
		if isinstance(value, bool):
			sets.append(f"{{%- set {name} = {'true' if value else 'false'} -%}}")
		else:
			sets.append(f'{{%- set {name} = "{value}" -%}}')
	return frappe.render_template("".join(sets) + f'{{% include "{FORM}" %}}', {})


def steps(html):
	return re.findall(r'data-step="(\d)"', html)


def named(html, name):
	return re.findall(rf'<(?:input|textarea)\b[^>]*\bname="{name}"[^>]*>', html)


class TestTheDefaultIsWhatPagesAlreadyHave(unittest.TestCase):
	def test_a_page_that_asks_for_nothing_gets_the_two_steps_it_had(self):
		html = render()
		self.assertEqual(steps(html), ["1", "2"])
		self.assertIn("data-progress", html)

	def test_an_unknown_model_falls_back_instead_of_drawing_nothing(self):
		"""A typo in a page must never cost the site its contact form."""
		html = render(contact_model="stpes")
		self.assertEqual(steps(html), ["1", "2"])
		self.assertEqual(len(named(html, "sender")), 1)


class TestTheThreeForms(unittest.TestCase):
	def test_simple_is_one_block_with_the_three_things_every_site_needs(self):
		html = render(contact_model="simple")
		self.assertEqual(steps(html), [])
		self.assertNotIn("data-progress", html)
		self.assertNotIn("data-step-next", html)
		for name in ("full_name", "sender", "message"):
			self.assertEqual(len(named(html, name)), 1, name)
		# no phone unless the business says it needs one
		self.assertEqual(named(html, "phone"), [])

	def test_simple_asks_for_the_phone_when_the_business_requires_it(self):
		html = render(contact_model="simple", phone_required=True)
		phone = named(html, "phone")
		self.assertEqual(len(phone), 1)
		self.assertIn("required", phone[0])

	def test_steps_walks_the_same_fields_in_two(self):
		html = render(contact_model="steps")
		self.assertEqual(steps(html), ["1", "2"])
		self.assertIn("data-step-next", html)
		self.assertIn("data-step-back", html)
		# the buttons wait for the script: without it both steps show and the form still posts
		self.assertRegex(html, r"data-step-next[^>]*hidden")

	def test_questions_asks_what_the_request_is_about_before_the_message(self):
		html = render(contact_model="questions")
		for name in ("request_type", "budget", "start_when"):
			self.assertTrue(named(html, name), f"{name} is missing")
		self.assertLess(html.index('name="request_type"'), html.index('name="message"'))
		self.assertEqual(steps(html), ["1", "2"])

	def test_every_option_names_the_question_it_answers(self):
		"""Without data-label the owner reads "A quote: A quote": the label beside a radio
		belongs to the option, not to the question (neo_contact_form.js labelOf)."""
		html = render(contact_model="questions")
		radios = re.findall(r'<input type="radio"[^>]*>', html)
		self.assertGreaterEqual(len(radios), 8)
		for radio in radios:
			with self.subTest(radio[:60]):
				self.assertIn("data-label=", radio)
				label = re.search(r'data-label="([^"]+)"', radio).group(1)
				value = re.search(r'value="([^"]+)"', radio).group(1)
				self.assertNotEqual(label, value)

	def test_the_other_models_ask_no_question_of_their_own(self):
		for model in ("simple", "steps"):
			with self.subTest(model):
				html = render(contact_model=model)
				for name in ("request_type", "budget", "start_when"):
					self.assertEqual(named(html, name), [], f"{name} should not be in {model}")


class TestWhatEveryModelMustCarry(unittest.TestCase):
	def test_the_defence_is_in_all_three(self):
		for model in ("simple", "steps", "questions"):
			with self.subTest(model):
				html = render(contact_model=model)
				self.assertIn('data-neo-contact="1"', html)
				self.assertIn("neoffice_theme.website_messages.submit", html)
				self.assertIn("issue_token", html)
				# the field only a script fills, and the line that tells the visitor what happened
				self.assertEqual(len(named(html, "website")), 1)
				self.assertIn("builder-contact-form__status", html)
				self.assertEqual(len(re.findall(r'<button type="submit"', html)), 1)

	def test_each_one_can_wait_in_a_window(self):
		for model in ("simple", "steps", "questions"):
			with self.subTest(model):
				html = render(contact_model=model, contact_dialog=True)
				self.assertIn('<dialog class="builder-contact-form__dialog"', html)
				self.assertIn('id="dialog_sender_name"', html)

	def test_each_one_can_carry_the_consent_sentence(self):
		sentence = "I agree that my details may be used to answer my enquiry."
		for model in ("simple", "steps", "questions"):
			with self.subTest(model):
				html = render(contact_model=model, consent_text=sentence)
				box = re.search(r'<input type="checkbox"[^>]*>', html).group(0)
				self.assertIn("required", box)
				self.assertIn(f'value="{sentence}"', box)
