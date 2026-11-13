# //// Neoffice — added file (no upstream equivalent): the first card of the site playbook (neoffice-maintenance#2614).
"""The first card of the site playbook asks the site type FIRST and is written in the person's language.

A person who started the wizard from the Website space saw the card open with « One page, or several pages with a menu? » and
its first question was « Name »: the opening sentence belonged to the fourth question. And the model took the language of the
playbook's English examples and wrote a French person's card in English.
"""

import unittest
from unittest import mock

import frappe

from builder.site_ai.nora import prompts


class TestTheFirstCard(unittest.TestCase):
	def first_card(self):
		text = prompts.site_playbook(None)
		return text.split("1. The business.")[1].split("2. The pages.")[0]

	def test_the_site_type_is_the_first_group_so_the_opening_sentence_is_the_first_question(self):
		card = self.first_card()
		for later in ("label:'Name'", "label:'Activity'", "label:'What makes you different'"):
			self.assertLess(card.index("label:'Site type'"), card.index(later), later)

	def test_the_card_still_names_the_six_site_types_the_pipeline_knows(self):
		card = self.first_card()
		for label in ("Showcase", "Showcase with customer accounts", "Online shop", "Blog", "Portfolio", "One page"):
			self.assertIn("label:'" + label + "'", card)
		for site_type in ("vitrine", "vitrine_user", "ecommerce", "blog", "portfolio", "one_page"):
			self.assertIn(site_type, card)

	def test_the_options_say_whether_the_site_has_several_pages_and_a_menu_or_one_page(self):
		card = self.first_card()
		self.assertIn("several pages with a menu", card)
		self.assertIn("a single long page, no menu", card)

	def test_the_card_is_asked_in_the_persons_language(self):
		self.assertIn("in the user's language", self.first_card())


class TestPicturesSentInAMessage(unittest.TestCase):
	"""« My images » hands the assistant the addresses of the pictures the person chose. Without a rule, the model took them for
	a request to put the picture on the page and applied thirty-seven changes to a blank draft (13.11, on osiris)."""

	def test_they_are_kept_for_the_site_and_never_put_on_the_page(self):
		text = prompts.site_playbook(None)
		self.assertIn("are THEIR OWN pictures", text)
		self.assertIn("do NOT edit or read any block", text)
		self.assertIn("keep their addresses for generate_site", text)
		self.assertIn("logo_image for a logo, photos for the others", text)


class TestThePersonsLanguage(unittest.TestCase):
	def say(self, user_language, system_language=None, builder_language=None, language_name="français"):
		def get_value(doctype, name, field=None, *args, **kwargs):
			return user_language if doctype == "User" else language_name

		def get_single_value(doctype, field):
			return system_language if doctype == "System Settings" else builder_language

		# frappe.session is a proxy of the request's session: the local object holds it, and it is put back as it was (a
		# patch that deletes it leaves every later test of the process without a session)
		previous = getattr(frappe.local, "session", None)
		frappe.local.session = frappe._dict(user="someone@example.test")
		try:
			with (
				mock.patch.object(frappe.db, "get_value", side_effect=get_value),
				mock.patch.object(frappe.db, "get_single_value", side_effect=get_single_value),
			):
				return prompts.person_language_line()
		finally:
			frappe.local.session = previous

	def test_the_language_of_the_account_is_said_by_name_and_code(self):
		line = self.say("fr")
		self.assertIn("français (fr)", line)
		self.assertIn("every question, option, description and button", line)

	def test_the_system_language_stands_in_when_the_account_has_none(self):
		self.assertIn("(de)", self.say(None, system_language="de", language_name="Deutsch"))

	def test_the_builders_default_language_is_the_last_resort(self):
		self.assertIn("(it)", self.say(None, builder_language="it", language_name="italiano"))

	def test_no_language_at_all_says_nothing(self):
		self.assertEqual(self.say(None), "")

	def test_the_playbook_carries_it(self):
		with mock.patch.object(prompts, "person_language_line", return_value="The person you talk to uses français (fr)."):
			self.assertIn("The person you talk to uses français (fr).", prompts.site_playbook(None))
